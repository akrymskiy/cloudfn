"""cloudfn-aws local"""

from contextlib import suppress
from json import load as json_load
from pathlib import Path
from uuid import uuid4
from string import Template


from cloudfn.aws.util import AWSInfo

class LambdaContext:
	"""LambdaContext for local testing"""
	_LOCAL_CONTEXT = True

	def __init__(self, function_name: str, function_alias: str = ''):
		# Check if a path was passed in for function_name
		with suppress(Exception):
			func_path = Path(function_name)
			if func_path.exists():
				# Default function name from path: {project_name}_{file_name}
				self._function_name = f'{func_path.parent.stem}_{func_path.stem}'

				# Check for existence of cfn.json
				cfn_path = func_path.parent.joinpath('cfn.json')
				if cfn_path.exists():
					with open(cfn_path) as f_cfn:
						cfn = json_load(f_cfn)

					# Compute function name as deployed
					if 'function_name_template' in cfn:
						self._function_name = Template(cfn['function_name_template']).safe_substitute({
							'project_name': cfn.get('project_name', func_path.parent.stem),
							'file_name': func_path.stem
						})
			else:
				# Not a valid path - use function_name as-is
				self._function_name = function_name
		self._function_alias = function_alias
		self._aws_request_id = str(uuid4())

	@property
	def function_name(self) -> str:
		"""Function name property"""
		return self._function_name

	@property
	def function_version(self) -> str:
		"""Function version property"""
		return '$LATEST'

	@property
	def invoked_function_arn(self) -> str:
		"""Function ARN property"""
		return (
			f'arn:aws:lambda:{AWSInfo.get_region()}:{AWSInfo.get_account()}'
			f':function:{self.function_name}:{self._function_alias}'.rstrip(':')
		)

	@property
	def memory_limit_in_mb(self) -> int:
		"""Function memory limit property"""
		return 128

	@property
	def aws_request_id(self) -> str:
		"""Function request_id property"""
		return self._aws_request_id

	@property
	def log_group_name(self) -> str:
		"""Function CloudWatch log group name property"""
		return f'/aws/lambda/{self.function_name}'

	@property
	def log_stream_name(self) -> str:
		"""Function CloudWatch log stream name property"""
		return f'1970/01/01/[{self.function_version}]{self.aws_request_id}'

	identity: None
	client_context: None

	@staticmethod
	def get_remaining_time_in_millis() -> int:
		"""Returns remaining time"""
		return 10000
