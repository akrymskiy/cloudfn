"""cloudfn-aws"""

from collections.abc import Mapping
from contextlib import suppress
from datetime import datetime
import functools
import inspect
import json
import os
from pathlib import Path
import re
from string import Template
import sys
import time
from traceback import extract_tb
from urllib.parse import urlsplit

import boto3
from botocore.exceptions import ClientError

from cloudfn.core.data import coalesce
from cloudfn.core.util import TestHelper

SSM_SUB_PATTERN = re.compile(r'\"\${ssm:(.+?)}\"')

class LambdaHandler:
	"""Lambda handler decorator"""
	_f = None
	_config = {}
	_invoke_counter = 0
	_project_name = None
	_local_mode = None
	_config_path_template = None

	def _load_project_config(self):
		"""Attempts to load project config from cfn.json (if present)"""
		with suppress(Exception):
			func_path = Path(self._f.__code__.co_filename)
			# Check for existence of cfn.json
			cfn_path = func_path.parent.joinpath('cfn.json')
			if cfn_path.exists():
				with open(cfn_path, 'rt', encoding='utf_8') as f_cfn:
					cfn = json.load(f_cfn)
					LambdaHandler._project_name = cfn.get('project_name', func_path.parent.stem)
					LambdaHandler._config_path_template = cfn.get('config_path_template')

	def __init__(self, f=None, trap_exceptions=False, hello_bye=False, payload_is_mapping=True):
		# Fix for timezone bug on Windows - it should be UTC on AWS Linux by default
		if os.name == 'nt':
			os.environ["TZ"] = "UTC"
			time.timezone = 0
			time.altzone = 0
			time.daylight = 0
			time.tzname = ('UTC', 'UTC')

		if f and not self._f:
			self._f = f
			self._f_sig = inspect.signature(self._f)
			self._load_project_config()

		LambdaHandler._invoke_counter = 0

		self._hello_bye = hello_bye
		self._trap_exceptions = trap_exceptions
		self._payload_is_mapping = payload_is_mapping

	def __get__(self, obj, owner=None):
		return functools.partial(self, obj)

	def __call__(self, *args, **kwargs):
		if args and hasattr(args[0], '__call__'):
			if not self._f:
				self._f = args[0]
				self._f_sig = inspect.signature(self._f)
				self._load_project_config()
			return self

		LambdaHandler._invoke_counter += 1

		context = None
		event = None
		alias = None
		refresh_config = None
		log = None

		# First param (expecting event)
		if args:
			event = args[0]

			# Check whether event is Mapping
			if isinstance(event, Mapping):
				# Check whether event has refresh_config key
				if 'refresh_config' in event:
					refresh_config = True
			else:
				# Raise exception if mapping is expected
				if self._payload_is_mapping:
					raise TypeError('Bad Input Type: Mapping expected')

		# Second param (expecting LambdaContext)
		if len(args) > 1 and type(args[1]).__name__ == 'LambdaContext':
			context = args[1]

			# Parse ARN from context
			arn_split = context.invoked_function_arn.split(':')
			if not LambdaHandler._project_name:
				# If this was not set from cfn.json assume default {project_name}_{function_name}
				LambdaHandler._project_name = arn_split[6].split('_', 1)[0]

			alias_arn = arn_split[7] if len(arn_split) == 8 else None
			alias = coalesce(alias_arn, 'Default')

			# Detect local mode (if needed)
			if LambdaHandler._local_mode is None:
				LambdaHandler._local_mode = getattr(context, '_LOCAL_CONTEXT', False)

			# Init log
			log = LambdaHandler.LambdaLog(
				LambdaHandler._invoke_counter,
				datetime.now(),
				alias,
				context.aws_request_id,
				LambdaHandler._local_mode)

			# Allow env var override
			if str.lower(os.environ.get('CFN_HELLO_BYE', '')) == 'true':
				self._hello_bye = True

			if 'CFN_CONFIG_PATH_TEMPLATE' in os.environ:
				LambdaHandler._config_path_template = os.environ['CFN_CONFIG_PATH_TEMPLATE']

			# Load config (if needed)
			if (LambdaHandler._config_path_template) and (alias not in LambdaHandler._config or refresh_config):
				config_path_split = urlsplit(
					Template(LambdaHandler._config_path_template)
						.safe_substitute(project_name=LambdaHandler._project_name, alias=alias)
				)

				s3_config_bucket = config_path_split.netloc
				s3_config_key = config_path_split.path.lstrip('/')

				log.log('CNFG', 'Attempting to read config from S3', {
					'bucket': s3_config_bucket,
					'key': s3_config_key
				})

				s3_config_obj = boto3.resource('s3').Object(
					s3_config_bucket,
					s3_config_key
				)

				try:
					# read config
					config_text = s3_config_obj.get()['Body']
					log.log('CNFG', 'Read config from S3', {
						'bucket': s3_config_obj.bucket_name,
						'key': s3_config_obj.key
					})

					# check for ssm vars
					if ssm_names := set(SSM_SUB_PATTERN.findall(config_text)):
						log.log('CNFG', 'Attempting to inject secrets', {
							'secrets': ssm_names
						})

						# init SSM client
						sec_client = boto3.client('secretsmanager')

						# try to load secrets and inject
						for ssm_name in ssm_names:
							secret_response = sec_client.get_secret_value(SecretId=ssm_name)
							try:
								# if secret is JSON, inject replacing the string val/quotes
								json.loads(secret_response['SecretString'])
								config_text = config_text.replace(f'"${{sm:{ssm_name}}}"', secret_response['SecretString'])
							except:
								# not a JSON, inject as string (leave quotes)
								config_text = config_text.replace(f'${{sm:{ssm_name}}}', secret_response['SecretString'])

					LambdaHandler._config[alias] = json.load(config_text)

					
				except ClientError as ex:
					log.log('CNFG', 'Unable to read config from S3', {
						'bucket': s3_config_obj.bucket_name,
						'key': s3_config_obj.key,
						'error_code': ex.response['Error']['Code'],
						'error_message': ex.response['Error']['Message']
					})
					raise

		# Barebone log in case context object is missing
		if not context:
			log = LambdaHandler.LambdaLog(LambdaHandler._invoke_counter, datetime.now())

		if self._hello_bye:
			log.hello(event)

		# Wrap actual call
		try:
			# Inject log if needed as kwarg
			_kwargs = dict(kwargs)
			if 'log' in self._f_sig.parameters:
				_kwargs['log'] = log
			if 'config' in self._f_sig.parameters:
				_kwargs['config'] = LambdaHandler._config.get(alias, {})
			if 'alias' in self._f_sig.parameters:
				_kwargs['alias'] = alias
			if 'alias_arn' in self._f_sig.parameters:
				_kwargs['alias_arn'] = alias_arn
				

			# Make the call
			ret_val = self._f(*args, **_kwargs)

			if self._hello_bye:
				log.goodbye(ret_val)

			return ret_val

		# pylint: disable=broad-except
		except Exception:
			# Exception processing/logging
			exc_tuple = sys.exc_info()

			if not self._trap_exceptions:
				raise
			if self._hello_bye:
				log.badbye({
					'errorType': exc_tuple[0].__name__,
					'errorMessage': str(exc_tuple[1]),
					'stackTrace': [
						{'filename': x.filename, 'name': x.name, 'line_num': x.lineno, 'line': x.line}
						for x in reversed(extract_tb(exc_tuple[2]))
					]
				})

	class LambdaLog:
		"""Lambda Log"""
		def __init__(self, invoke_counter, start_time, alias=None, aws_request_id=None, local_mode=None):
			self._invoke_counter = invoke_counter
			self._start_time = start_time
			self._alias = alias
			self._aws_request_id = aws_request_id
			self._local_mode = local_mode

		def run_time_sec(self):
			"""Computes run-time in seconds since log init"""
			return (datetime.now() - self._start_time).total_seconds()

		def log(self, severity: str, msg: str, extra: dict = None):
			"""Log method"""
			log_dict = {
				'severity': severity,
				'invokeNumber': self._invoke_counter,
				'message': msg
			}

			if self._alias:
				log_dict['alias'] = self._alias

			if self._aws_request_id:
				log_dict['requestId'] = self._aws_request_id

			if extra:
				log_dict['extra'] = extra

			if self._local_mode:
				TestHelper.print_log_entry(log_dict)
			else:
				try:
					log_str = json.dumps(log_dict, separators=(',', ':'), ensure_ascii=False, default=str)
				except TypeError:
					log_dict['extra'] = "...Unable to deserialize 'extra'..."
					log_str = json.dumps(log_dict, separators=(',', ':'), ensure_ascii=False)

				print(log_str, flush=True)

		def trace(self, msg: str, extra: dict = None):
			"""Log (TRACE) method"""
			self.log('TRACE', msg, extra)

		def info(self, msg: str, extra: dict = None):
			"""Log (INFO) method"""
			self.log('INFO', msg, extra)

		def warn(self, msg: str, extra: dict = None):
			"""Log (WARN) method"""
			self.log('WARN', msg, extra)

		def error(self, msg: str, extra: dict = None):
			"""Log (ERROR) method"""
			self.log('ERROR', msg, extra)

		def hello(self, extra: dict = None):
			"""Log begin execution"""
			self.info('Hello', extra)

		def goodbye(self, ret_val=None):
			"""Log successful completion"""
			log_ret_val = {'ret_val': ret_val} #ret_val if ret_val and isinstance(ret_val, Mapping) else {'scalar': ret_val}
			self.info('Completed', {**log_ret_val, **{'runTimeSec': self.run_time_sec()}})

		def badbye(self, ret_val=None):
			"""Log unsuccessful completion"""
			log_ret_val = {'ret_val': ret_val} #ret_val if ret_val and isinstance(ret_val, Mapping) else {'scalar': ret_val}
			self.error('Completed', {**log_ret_val, **{'runTimeSec': self.run_time_sec()}})
