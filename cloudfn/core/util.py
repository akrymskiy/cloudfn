"""cloudfn-core util"""

import json
import os
import time

class Colors:
	"""Colors"""

	RESET = '\033[0m'
	BOLD = '\033[01m'
	DISABLE = '\033[02m'
	UNDERLINE = '\033[04m'
	REVERSE = '\033[07m'
	STRIKETHROUGH = '\033[09m'
	INVISIBLE = '\033[08m'

	class FG:
		"""Foreground Colors"""
		BLACK = '\033[30m'
		RED = '\033[31m'
		GREEN = '\033[32m'
		ORANGE = '\033[33m'
		BLUE = '\033[34m'
		PURPLE = '\033[35m'
		CYAN = '\033[36m'
		LIGHTGREY = '\033[37m'
		DARKGREY = '\033[90m'
		LIGHTRED = '\033[91m'
		LIGHTGREEN = '\033[92m'
		YELLOW = '\033[93m'
		LIGHTBLUE = '\033[94m'
		PINK = '\033[95m'
		LIGHTCYAN = '\033[96m'

	class BG:
		"""Background Colors"""
		BLACK = '\033[40m'
		RED = '\033[41m'
		GREEN = '\033[42m'
		ORANGE = '\033[43m'
		BLUE = '\033[44m'
		PURPLE = '\033[45m'
		CYAN = '\033[46m'
		LIGHTGREY = '\033[47m'

	@staticmethod
	def print_colored(colors, text):
		"""Prints text in supplied colors"""
		for color in colors:
			print(color, end='')
		print(text)
		print(Colors.RESET, end='')

class TestHelper:
	"""Test Helper"""
	_flipper = False
	_t0 = None

	@classmethod
	def print_begin_testing(cls):
		"""Prints begin testing message on console"""
		cls.mark_time()
		print(f":: {'Begin Testing '::<80}")

	@classmethod
	def print_end_testing(cls):
		"""Prints end testing message on console"""
		print(f":: {'End Testing '::<50}{(cls.get_time_from_mark())::>23.2f} sec ::")

	@staticmethod
	def print_return_value(ret_val):
		"""Prints return value on console"""
		# print(Colors.FG.LIGHTGREEN, end='')
		# for l in json.dumps(ret_val, indent='\t', ensure_ascii=False, default=str).split('\n'):
		# 	print(l)
		# print(Colors.RESET, end='')
		Colors.print_colored(Colors.FG.LIGHTGREEN, json.dumps(ret_val, indent='\t', ensure_ascii=False, default=str))

	@staticmethod
	def set_env_vars(env_vars):
		"""Set environment variables"""
		os.environ.update(env_vars)

	@classmethod
	def mark_time(cls):
		"""Marks current time"""
		cls._t0 = time.time()

	@classmethod
	def get_time_from_mark(cls):
		"""Computes delta from mark to current"""
		return time.time() - cls._t0

	@classmethod
	def print_time_from_mark(cls):
		"""Prints delta from mark to current"""
		print(f'Time elapsed: {(cls.get_time_from_mark()):.2f} sec')

	@classmethod
	def print_log_entry(cls, log_entry):
		"""Prints log entry on console"""
		try:
			log_str = json.dumps(log_entry, indent='\t', ensure_ascii=False, default=str)
		except TypeError:
			log_entry['extra'] = "...Unable to deserialize 'extra'..."
			log_str = json.dumps(log_entry, indent='\t', ensure_ascii=False)
		print(Colors.FG.LIGHTCYAN if cls._flipper else Colors.FG.CYAN, end='')
		cls._flipper = not cls._flipper

		for l in log_str.splitlines():
			print(l)
		print(Colors.RESET, end='')