
"""cloudfn-core data"""

from datetime import date

def parse_iso_date(val, default=None) -> (date):
	"""parse string as date"""
	return date.fromisoformat(val) if val else default
