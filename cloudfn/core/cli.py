"""cloudfn command-line module"""

from argparse import ArgumentParser
import ast
from importlib import import_module
from importlib.util import spec_from_file_location, module_from_spec
from inspect import getmembers
from pathlib import Path
from sys import argv
from traceback import extract_tb

def deploy_fn(args):
	"""Deploy function"""

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

def deploy_layer(args):
	"""Deploy layer"""
	function_path = Path(args.function_path)
	if function_path.is_file():
		print(f'Attempting to load: {args.function_path}')
	else:
		print(f'{function_path.absolute()} is not a file')
		return 1

	return 0

def main():
	"""CLI Entry-Point"""
	# Process arguments
	arg_parser = ArgumentParser(description='cloudfn cli')
	subparsers = arg_parser.add_subparsers(help='sub-command help', dest='cmd', required=True)
	#subparsers.add_argument('action', choices=['deploy'])

	deploy_fn_parser = subparsers.add_parser('deploy-fn', aliases=['df'], help='deploys function')
	deploy_fn_parser.add_argument('--fn-path', '-fp', required=True, help='path help')
	deploy_fn_parser.set_defaults(function=deploy_fn)

	deploy_layer_parser = subparsers.add_parser('deploy-layer', aliases=['dl'], help='deploys layer')
	deploy_layer_parser.add_argument('--fn-path', '-fp', help='path help')
	deploy_layer_parser.set_defaults(function=deploy_layer)

	args = arg_parser.parse_args(argv[1:])
	# print(args)
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
		'__main__.argv',
		# r'cfn df -fp C:\Users\avk\Repos\CF\cf-dw-lambda\Cartesian\APICollector.py'.split()):
		r'cfn deploy-fn --fn-path C:\Users\avk\Repos\Personal\cloudfn\example\Example.py'.split()):
		print('Ret Val = ', main())
# endregion