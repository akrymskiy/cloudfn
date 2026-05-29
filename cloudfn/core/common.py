"""CFN Commmons"""

import ast
from collections import defaultdict, namedtuple
import importlib
import inspect
import json
from pathlib import Path
import sys

FNPaths = namedtuple('FNPaths', ['fn_path', 'project_path', 'cfn_config_path', 'requirements_path'])
FNProps = namedtuple('FNProps', ['project_name', 'cfn_config', 'fn_handlers'])

def get_fn_paths(path: str):
	"""Compute FNPaths"""
	fn_path = Path(path)

	if not fn_path.exists():
		return None

	if fn_path.is_dir():
		project_path = fn_path
		fn_path = None
	else:
		project_path = fn_path.parent

	if not (requirements_path := project_path.joinpath('requirements.txt')).exists():
		requirements_path = None
	if not (cfn_config_path := project_path.joinpath('cfn.json')).exists():
		cfn_config_path = None

	return FNPaths(fn_path, project_path, cfn_config_path, requirements_path)

def get_fn_props(fn_paths: FNPaths):
	"""Compute FNProps"""
	cfn_config = None

	# Try to load config from cfn.json (if exists)
	if fn_paths.cfn_config_path:
		with open(fn_paths.cfn_config_path, 'r') as f_cfn_config:
			try:
				cfn_config = json.load(f_cfn_config)
			except Exception as ex:
				print_e(f'Unable to load `{fn_paths.cfn_config_path}` due to `{fqcn(ex)}`\n\t{str(ex)}')
				sys.exit(1)

	# Try to get project_name from cfn.json, fall-back to folder name
	project_name = cfn_config.get('project_name', fn_paths.project_path.name) if cfn_config else fn_paths.project_path.name

	# Try to find entry-point
	try:
		code = ast.parse(open(fn_paths.fn_path).read())

		# Loop through all the function definitions
		fn_handlers = defaultdict(list)
		for fn_def in (x for x in code.body if isinstance(x, ast.FunctionDef)):
			# Loop through decorators on the function
			for dec in fn_def.decorator_list:
				# Parse through decorator name nodes
				dec_name_list = []
				current_node = dec.func if isinstance(dec, ast.Call) else dec
				while current_node:
					if isinstance(current_node, ast.Attribute):
						dec_name_list.append(current_node.attr)
						current_node = current_node.value
					else:
						dec_name_list.append(current_node.id)
						current_node = None

				# Compute decorator full name
				dec_name = '.'.join(reversed(dec_name_list))

				# Check for CloudFN decorator
				if dec_name.endswith('LambdaHandler'):
					fn_handlers['aws'].append((
						fn_def.name,
						dec_name,
						{kw.arg: kw.value.value for kw in dec.keywords} if isinstance(dec, ast.Call) else {}
					))

			return FNProps(project_name, cfn_config, fn_handlers)
	except:
		raise

	return FNProps(project_name, cfn_config, None)

def print_e(*args, **kwargs):
	"""Error message print"""
	print(*args, file=sys.stderr, **kwargs)

def fqcn(obj):
	"""Fully Qualitified Class Name"""
	clazz = obj.__class__
	if clazz.__module__ == 'builtins':
		return clazz.__qualname__
	else:
		return f'{clazz.__module__}.{clazz.__qualname__}'
