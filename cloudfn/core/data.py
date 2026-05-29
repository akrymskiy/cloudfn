
"""cloudfn-core data"""

from datetime import date
import re

def parse_iso_date(val, default=None) -> (date):
	"""Parse string as date"""
	return date.fromisoformat(val) if val else default

def coalesce(*vals):
	"""Return first val that is not None"""
	for val in vals:
		if val is not None:
			return val
	return None

def missing_to_none(val):
	"""Replace missing value to None"""
	if val is None or len(str(val)) == 0:
		return None

	return val


def safe_cast_int(val):
	"""Cast value as int"""
	if not (val := missing_to_none(val)):
		return None

	if isinstance(val, (int, float)):
		return int(val)

	return int(re.sub('[^.0-9-]', '', str(val)))


def safe_cast_float(val):
	"""Cast value as float"""
	if not (val := missing_to_none(val)):
		return None

	if isinstance(val, (int, float)):
		return float(val)

	return float(re.sub('[^.0-9-]', '', str(val)))
