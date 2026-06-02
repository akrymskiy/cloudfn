"""cloudfn command-line module"""

from argparse import ArgumentParser
import ast
from importlib import import_module
from importlib.util import spec_from_file_location, module_from_spec
from inspect import getmembers
from pathlib import Path
import sys
from traceback import extract_tb

from cloudfn.core.common import FNPaths, get_fn_paths, print_e

def import_cfn_module(module_name: str):
	"""Import cfn module dynamically"""
	try:
		return import_module(module_name)

	except ModuleNotFoundError as mnfe:
		if mnfe.name.startswith('cloudfn.aws'):
			print_e('Required `cloudfn-aws` package is not installed.')
		elif mnfe.name.startswith('cloudfn.azure'):
			print_e('Required `cloudfn-azure` package is not installed.')
		elif mnfe.name.startswith('cloudfn.gcp'):
			print_e('Required `cloudfn-gcp` package is not installed.')
		else:
			print_e(f'Please install package containing module `{mnfe.name}`')

		sys.exit(1)

def deploy_fn(args):
	"""Deploy function"""

	fn_paths = get_fn_paths(args.path)
	fn_path = Path(args.fn_path)

	# Check file
	if not fn_path.is_file():
		print(f'{fn_path.absolute()} is not a file')
		return 1


	fn_file_name = fn_path.name
	fn_module_name = fn_path.stem

	print(fn_file_name, fn_module_name)

	# AST Test
	code = ast.parse(open(fn_path).read())

	for x in code.body:
		print(x)
		if isinstance(x, ast.FunctionDef):
			print('Decorators:')
			xx: ast.FunctionDef = x
			for d in xx.decorator_list:
				print(d)
				# dd: ast.Name = d
				# print(dd.id, dd.ctx)
		elif isinstance(x, ast.ImportFrom):
			print('Import From: ')
			xx: ast.ImportFrom = x
			print(xx.module)
			print(xx.names)

	return
	#

	print(f'Attempting to load: {fn_path}')
	fn_spec = spec_from_file_location(fn_module_name, fn_path)
	fn_module = module_from_spec(fn_spec)
	# print(fn_spec, fn_module)
	try:
		fn_spec.loader.exec_module(fn_module)
	except ModuleNotFoundError as mnfe:
		print(mnfe.msg)
		print(mnfe.name)
		# print(type(mnfe.__traceback__))
		# print(mnfe.__traceback__.tb_lasti)

		frame = extract_tb(mnfe.__traceback__)[-1]

		print(frame.filename, frame.line, frame.lineno, frame.name)
		# print(next(traceback.walk_stack(mnfe.__traceback__.tb_frame)))
		# traceback.print_tb(mnfe.__traceback__, 10)
		return 1

	handler_candidates = [
		x for x in getmembers(fn_module)
		if x[1].__class__.__qualname__ == 'LambdaHandler'
	]

	if len(handler_candidates) > 1:
		raise RuntimeError('Multiple functions decorated with LambdaHandler found!')
	if not handler_candidates:
		raise RuntimeError('Function decorated with LambdaHandler not found!')

	handler_fn = handler_candidates[0]
	print(handler_fn)
	print('EntryPoint FN', handler_fn[0])
	# Check handler decorator module
	hdm = handler_fn[1].__class__.__module__.split('.')
	if hdm[0] == 'cloudfn' and hdm[2] == 'model':
		print(hdm[1])

		dfn = import_module(f'cloudfn.{hdm[1]}.deploy').deploy_fn
		print(dfn)
		dfn()

		# cloudfn.aws.model.LambdaHandler
	# func_file_path = file_arg
	# project_dir = func_file_path.parent
	# project_name = project_dir.name
	# func_file_name = func_file_path.name
	# func_name = func_file_path.stem
	# func_name_full_name = f'{project_name}_{func_name}'

	# spec = importlib.util.spec_from_file_location(func_name, func_file_path)
	# func_module = importlib.util.module_from_spec(spec)
	# spec.loader.exec_module(func_module)

	# handler_candidates = [x[0] for x in inspect.getmembers(func_module) if isinstance(x[1], LambdaHandler)]

	# if len(handler_candidates) > 1:
	# 	raise RuntimeError('Multiple functions decorated with LambdaHandler found!')
	# elif not handler_candidates:
	# 	raise RuntimeError('Function decorated with LambdaHandler not found!')

	return 0

def deploy_aws_layer(args):
	"""Deploy AWS function layer"""
	print('CFN AWS Layer Deploy')
	print('--------------------')
	fn_paths = get_fn_paths(args.path)

	if not fn_paths:
		print_e(f'Path `{args.path}` does not exists')
		sys.exit(1)

	if not fn_paths.requirements_path:
		print_e(f'`requirements.txt` not found in the project folder')
		sys.exit(1)

	deploy_module = import_cfn_module('cloudfn.aws.deploy')
	deploy_module.deploy_fn_layer(fn_paths, args.aws_profile, args.aws_region, args.layer_builder_function)

	return 0

def deploy_aws_fn(args):
	"""Deploy AWS function"""
	print('CFN AWS Function Deploy')
	print('-----------------------')

	fn_paths = get_fn_paths(args.path)

	if not fn_paths:
		print_e(f'Path `{args.path}` does not exists')
		sys.exit(1)

	deploy_module = import_cfn_module('cloudfn.aws.deploy')
	deploy_module.deploy_fn(fn_paths, args.aws_profile, args.aws_region)

	return 0

def deploy_aws_layer_builder_fn(args):
	"""Create AWS LayerBuilder function"""

	print('CFN AWS Lambda Builder Function Deploy')
	print('-----------------------')

	deploy_module = import_cfn_module('cloudfn.aws.deploy')
	deploy_module.deploy_layer_builder_fn(args.layer_builder_function, args.aws_profile, args.aws_region)

	return 0

def main():
	"""CLI Entry-Point"""
	# Process arguments
	arg_parser = ArgumentParser(description='cloudfn CLI')
	subparsers = arg_parser.add_subparsers(help='sub-command help', dest='cmd', required=True)

	deploy_aws_fn_parser = subparsers.add_parser('deploy-aws-fn', help='deploys function to AWS Lambda')
	deploy_aws_fn_parser.add_argument('--path', required=True, help='path to function')
	# deploy_aws_fn_parser.add_argument('--aws-profile', required=False, help='AWS CLI profile name')
	# deploy_aws_fn_parser.add_argument('--aws-region', required=False, help='AWS region')
	deploy_aws_fn_parser.set_defaults(function=deploy_aws_fn)

	deploy_aws_layer_parser = subparsers.add_parser('deploy-aws-layer', help='deploys layer to AWS Lambda')
	deploy_aws_layer_parser.add_argument('--path', required=True, help='path to function or to project folder')
	# deploy_aws_layer_parser.add_argument('--aws-profile', required=False, help='AWS CLI profile name')
	# deploy_aws_layer_parser.add_argument('--aws-region', required=False, help='AWS region')
	deploy_aws_layer_parser.add_argument('--layer-builder-function', required=False, default='CFN_LambdaLayerBuilder', help='name or ARN of the deploy function')
	deploy_aws_layer_parser.set_defaults(function=deploy_aws_layer)

	deploy_aws_layer_builder_fn_parser = subparsers.add_parser('create-aws-layer-builder-fn', help='deploys LayerBuilder helper function')
	deploy_aws_layer_builder_fn_parser.add_argument('--layer-builder-function', required=False, default='CFN_LambdaLayerBuilder', help='name for the deploy function')
	# deploy_aws_layer_builder_fn_parser.add_argument('--aws-profile', required=False, help='AWS CLI profile name')
	# deploy_aws_layer_builder_fn_parser.add_argument('--aws-region', required=False, help='AWS region')
	deploy_aws_layer_builder_fn_parser.set_defaults(function=deploy_aws_layer_builder_fn)

	# Common AWS parser args
	for aws_sub_parser in (deploy_aws_fn_parser, deploy_aws_layer_parser, deploy_aws_layer_builder_fn_parser):
		aws_sub_parser.add_argument('--aws-profile', required=False, help='AWS CLI profile name')
		aws_sub_parser.add_argument('--aws-region', required=False, help='AWS region')


	args = arg_parser.parse_args(sys.argv[1:])

	return args.function(args)

	# print(args)
	# if args.deploy:
	# 	print('OK')


	# if args.deploy_lambda:
	# 	lambda_path = Path(args.deploy_lambda)
	# 	if lambda_path.is_file():
	# 		print(f'Deploying {lambda_path}')
	# 	else:
	# 		print(f'{lambda_path.absolute()} is not a file')

# region Test Area
if __name__ == '__main__':
	import unittest.mock
	with unittest.mock.patch(
		'__main__.sys.argv',
		# r'cfn df -fp C:\Users\avk\Repos\CF\cf-dw-lambda\Cartesian\APICollector.py'.split()):
		# r'cfn deploy-aws-fn --fn-path C:\Users\avk\Repos\Personal\cloudfn\example\Example.py'.split()):
		# r'cfn deploy-aws-layer --fn-path C:\Users\avk\Repos\Personal\cloudfn\example\Example.py'.split()):
		r'cfn create-aws-layer-builder-fn --aws-profile ba-prod'.split()):
		print('Ret Val = ', main())


	# cfn deploy-layer --fn-path C:\Users\avk\Repos\DM\dm-lambda\Athena\QueryAcceptor.py
# endregion