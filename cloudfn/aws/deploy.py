"""cloudfn-aws deploy"""

import os
import sys
import json

import botocore
import boto3

from cloudfn.core.common import FNPaths, fqcn, get_fn_props, print_e

def deploy_fn(fn_paths: FNPaths, aws_profile: str, aws_region: str):
	"""AWS Function Deployer"""
	fn_props = get_fn_props(fn_paths)

	print(f'Deploying function `{fn_paths.fn_path}` to AWS Lambda')
	print(fn_props)
	
	aws_handlers = fn_props.fn_handlers.get('aws')

	if len(aws_handlers) == 0:
		print_e('Did not find decorated entry-point function in the function code')
		sys.exit(1)
	
	if len(aws_handlers) > 1:
		print_e('More than one decorated entry-point function in the function code')
		sys.exit(1)

	handler_name = aws_handlers[0]

	# Files to deploy
	files = {fn_paths.fn_path: fn_paths.fn_path.name}
	print(files)
	return

	files = {str(func_file_path): func_file_name}

	# Aditional files
	common_path = project_dir.joinpath('common.py')
	if common_path.exists() and common_path.is_file():
		files[str(common_path)] = common_path.name

	resources_path = project_dir.joinpath('resources')
	if resources_path.exists() and resources_path.is_dir():
		files.update(dict((x, x.relative_to(project_dir)) for x in resources_path.glob('**/*') if x.is_file()))

	deployer = LambdaDeployer(
		project_name=project_name, func_name=func_name,
		files=files, #{str(func_file_path): func_file_name},
		handler=f'{func_name}.{handler_name}',
		layers=['bdc-bi-common'],
		make_config=True)

	deploy_result = deployer.deploy()
	print(
		f"{Colors.FG.PINK}Published {Colors.BOLD}{func_name_full_name}{Colors.RESET}"
		f"{Colors.FG.PURPLE} @ {datetime.now().isoformat(' ')}"
	)
	print(f"{Colors.FG.PINK}RevisionId: {Colors.FG.PURPLE}{deploy_result['RevisionId']}")
	print(Colors.RESET)

if __name__ == '__main__':
	deploy()


def deploy_fn_layer(fn_paths: FNPaths, aws_profile: str, aws_region: str, layer_builder_function: str):
	"""AWS Layer Deployer"""
	fn_props = get_fn_props(fn_paths)

	print(f'Deploying AWS Lambda layer for project `{fn_props.project_name}` using `{str(fn_paths.requirements_path)}`')

	with open(fn_paths.requirements_path, 'rt', encoding='utf-8') as f_requirements:
		requirements = f_requirements.read().splitlines()

	try:
		# Set up session
		aws_session_settings = {}
		if aws_profile:
			aws_session_settings['profile_name'] = aws_profile
		if aws_region:
			aws_session_settings['aws_region'] = aws_region

		aws_session = boto3.session.Session(**aws_session_settings)
		lambda_client_config = botocore.config.Config(read_timeout=920, connect_timeout=920, retries={'max_attempts': 0})
		lambda_client = aws_session.client("lambda", config=lambda_client_config)
		lambda_response = lambda_client.invoke(
			FunctionName=layer_builder_function,
			InvocationType='RequestResponse',
			LogType='Tail',
			Payload=bytes(json.dumps({
				'layer_name': fn_props.project_name,
				'packages': requirements
			}), 'utf-8')
		)
	except Exception as ex:
		print_e(f'Unable to execute `{layer_builder_function}` due to {fqcn(ex)}\n\t{str(ex)}')
		sys.exit(1)
	print('-----------------------------')
	print(f"{layer_builder_function}: {lambda_response.get('StatusCode')}")
	res_payload = lambda_response.get('Payload')
	try:
		print(json.dumps(json.load(res_payload), indent=4))
	except json.JSONDecodeError:
		print(str(res_payload.read(), 'utf-8'))


def deploy_layer_builder_fn(args, sd,df):
	# fn_paths: FNPaths, aws_profile: str, aws_region: str, layer_builder_function: str
	print('ok', sd, df)
	pass