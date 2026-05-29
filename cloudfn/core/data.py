
"""cloudfn-core data"""

from datetime import date
from decimal import Decimal
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
	if isinstance(val, (int, float, Decimal)):
		return int(val)

	if not (val := missing_to_none(re.sub('[^.0-9-]', '', str(val)))):
		return None

	return int(float(val))

def safe_cast_float(val):
	"""Cast value as float"""
	if isinstance(val, (int, float, Decimal)):
		return float(val)

	if not (val := missing_to_none(re.sub('[^.0-9-]', '', str(val)))):
		return None

	return float(val)

def safe_cast_decimal(val):
	"""Cast value as Decimal"""
	if isinstance(val, (int, float, Decimal)):
		return Decimal(val)

	if not (val := missing_to_none(re.sub('[^.0-9-]', '', str(val)))):
		return None

	return Decimal(val)
