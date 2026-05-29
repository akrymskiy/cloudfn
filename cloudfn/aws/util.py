"""cloudfn-aws util"""

import os

import boto3

class AWSInfo():
	"""AWS Informational"""
	_aws_info = None

	@classmethod
	def _populate(cls):
		if cls._aws_info is None:
			cls._aws_info = {
				'region': (
					os.environ.get('AWS_REGION')
					or os.environ.get('AWS_DEFAULT_REGION')
					or (boto3.DEFAULT_SESSION.region_name if boto3.DEFAULT_SESSION else None)
					or boto3.Session().region_name),
				'account': boto3.client("sts").get_caller_identity()['Account']
			}

	@classmethod
	def get_account(cls):
		"""Returns AWS account # for currently executing code"""
		cls._populate()
		return cls._aws_info.get('account')

	@classmethod
	def get_region(cls):
		"""Returns AWS region for currently executing code"""
		cls._populate()
		return cls._aws_info.get('region')
