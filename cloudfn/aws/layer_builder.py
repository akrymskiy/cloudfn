"""Layer Builder"""

import io
from datetime import datetime
import os
import shutil
import subprocess
from subprocess import CalledProcessError
import sys
import zipfile

import boto3

# from bdc_bi_common.aws_helper import LambdaHandler
#from bdc_bi_common.io_helper import MemStream

def print_bstr(bstr):
	"""Print binary string"""
	for l in bstr.decode('utf8').split('\n'):
		print(l)

FILTER_FILES = ['__pycache__', 'pip', 'pkg_resources', 'setuptools', 'wheel', 'easy_install.py']

def filter_files(file_path):
	"""Ignore helper function"""
	# Ignore setup packages
	filtered = not any(f'site-packages/{x}' in file_path for x in FILTER_FILES)
	# Ignore pre-compiled
	filtered = filtered and not file_path.endswith('pyc') and not file_path.endswith('pyo')
	# Ignore tests
	filtered = filtered and not '/tests/' in file_path

	return filtered

# pylint: disable=unused-argument,missing-kwoa
# @LambdaHandler
def lambda_handler(event, context, *, log, config):
	"""Lambda entry-point"""
	# Checking for mandatory input
	if not {'layerName', 'packages'} <= event.keys():
		raise ValueError('Expecting "layerName" and "packages" params in function input')

	layer_name = event['layerName']
	packages = event['packages']
	deploy_layer = event.get('deployLayer', True)
	compatible_runtimes = event.get('deployLayer', ['python3.6', 'python3.7', 'python3.8', 'python3.9'])
	no_upgrade = event.get('noUpgrade', False)

	# Clear out /tmp
	shutil.rmtree('/tmp/', ignore_errors=True)

	# Set up virtual env
	result = subprocess.run(
		["python3", "-m", "venv", "/tmp/layer"],
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		check=True)

	## --compile ????
	try:
		result = subprocess.run(
			[
				"source /tmp/layer/bin/activate && pip install --no-cache-dir --prefer-binary wheel"
				" && pip install --no-cache-dir --upgrade pip"
				f" && pip install {'' if no_upgrade else '-U'} --no-cache-dir --prefer-binary {' '.join(packages)}"
			],
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			shell=True,
			check=True
		)
	except CalledProcessError as ex:
		print_bstr(ex.stdout)
		raise ex

	print_bstr(result.stdout)

	zip_buffer = io.BytesIO()
	with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False, compresslevel=9) as zip_file:
		for root, _, files in os.walk('/tmp/layer/lib'):
			for file in files:
				file_to_add = os.path.join(root, file)
				if filter_files(file_to_add):
					zip_file.write(
						file_to_add,
						file_to_add.replace(
							f'/tmp/layer/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/',
							'python/'
						)
					)

		bucket = 'bdc-bi-temp'
		key = f"lambda/Lambda/LambdaLayer/{layer_name}.zip"
		zip_file.close()
		s3_obj = boto3.resource("s3").Object(
			bucket,
			key)
		zip_buffer.flush()
		zip_buffer.seek(0)
		s3_obj.put(Body=zip_buffer)

		if deploy_layer:
			print('Deploying layer to AWS Lambda...')
			lambda_client = boto3.client('lambda')
			publish_result = lambda_client.publish_layer_version(
				LayerName=layer_name,
				Description=f"{layer_name} built by Lambda_LayerBuilder on {datetime.now()}",
				Content={
					'S3Bucket': s3_obj.bucket_name,
					'S3Key': s3_obj.key
				},
				CompatibleRuntimes=compatible_runtimes
			)

			print(f"Published version: {publish_result['LayerVersionArn']}")
