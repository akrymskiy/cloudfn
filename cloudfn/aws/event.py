"""cloudfn-aws event"""

from collections.abc import Mapping
from datetime import datetime
from urllib.parse import unquote_plus

class Payload():
	"""Generic Event"""
	class S3Event():
		"""S3 Event"""
		def __init__(self, payload):
			self._payload = payload

		@property
		def records(self):
			"""S3 Records"""
			return map(Payload.S3Event.S3Record, self._payload.records)

		@property
		def first(self):
			"""First S3 Record"""
			return Payload.S3Event.S3Record(self._payload.first_record)

		class S3Record():
			"""S3 Record"""
			def __init__(self, raw_record):
				self._raw_record = raw_record

			@property
			def bucket_name(self):
				"""Bucket name"""
				return unquote_plus(self._raw_record.get('s3', '').get('bucket', {}).get('name'))

			@property
			def object_key(self):
				"""Object Key"""
				return unquote_plus(self._raw_record.get('s3', '').get('object', {}).get('key'))

			@property
			def event_name(self):
				"""Event Name"""
				return self._raw_record.get('eventName')

			@property
			def event_time(self):
				"""Event Time"""
				return datetime.fromisoformat(self._raw_record.get('eventTime').rstrip('Z'))

			@property
			def aws_region(self):
				"""Region"""
				return self._raw_record.get('awsRegion')



	class SQSEvent():
		"""SQS Event"""
		def __init__(self, payload):
			self._payload = payload

		@property
		def first(self):
			return self._payload.records[0]

		@staticmethod
		def mock_single():
			return Payload.SQSEvent({})

		@staticmethod
		def mock_batch():
			return Payload.SQSEvent({})

	def __init__(self, event):
		self.is_none = event is None
		self.is_mapping = isinstance(event, Mapping)
		self.raw_event = event

		records = event.get('Records')
		self.records = records if isinstance(records, list) and len(records) > 0 else None
		event_source = self.first_record.get('eventSource') if isinstance(self.first_record, Mapping) else None
		self.is_s3 = event_source == 'aws:s3'
		self.is_sqs = event_source == 'aws:sqs'
		self.is_sns = event_source == 'aws:sns'

	@property
	def sqs_event(self):
		return Payload.SQSEvent(self) if self.is_sqs else None

	@property
	def s3_event(self):
		return Payload.S3Event(self) if self.is_s3 else None

	@property
	def first_sqs(self):
		if self.records:
			return None # first_record of known subclasses or default first_record

		return self.raw_event

	@property
	def first_record(self):
		"""First record if present"""
		return self.records[0] if self.records else None

	@property
	def aws_event(self):
		"""Specific event conversion"""
		if self.is_s3:
			return Payload.S3Event(self)

	@staticmethod
	def mock_s3_single(bucket_name, object_key,
		event_name='ObjectCreated:Put', aws_region='us-east-1', event_time=datetime.utcnow(),
		size=0, principal_id='', metadata={}):
		"""Mock single S3 event"""
		return {"Records": [{
			"eventVersion": "2.1",
			"eventSource": "aws:s3",
			"awsRegion": aws_region,
			"eventTime": event_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
			"eventName": event_name,
			"s3": {
				"s3SchemaVersion": "1.0",
				"configurationId": "Mock_Configuration",
				"bucket": {
					"name": bucket_name,
					"ownerIdentity": {
						"principalId": principal_id
					},
					"arn": f"arn:aws:s3:::{bucket_name}"
				},
				"object": {
					"key": object_key,
					"size": size,
					# "eTag": "f2c82ce53131855f07edf6dca7a0157b",
					# "versionId": "jNoYRR1AdiKAtaiBeDvvhyrVYs31V.5z",
					# "sequencer": "00602EBEAF9C397C40"
				}
			}
		}]}

if __name__ == '__main__':
	e_in = {}
	e_in = {'Records': [{
		# messageId: 'eccfe821-0a8e-4ab8-aa8c-cb818c0dcc1a',
		# receiptHandle: 'N1254aOMj35YWpAVbUzzx25rvGL39CC3NbL9+ZDaSK43Rgafo3+LDJPjydxF0LkAQ1+e1giDiL0=',
		# body: JSON.stringify(body),
		# attributes: {},
		# messageAttributes: {},
		# md5OfBody: 'be61a9f98ddd5dd9ef53e5e0f62b67fe',
		'eventSource': 'aws:sqs'
		# eventSourceArn: sourceArn,
		# awsRegion: 'us-east-1'
	}]}
	e_in = {
		"Records": [{
				"eventVersion": "2.1",
				"eventSource": "aws:s3",
				"awsRegion": "us-west-2",
				"eventTime": "2021-02-18T19:23:27.498Z",
				"eventName": "ObjectCreated:Put",
				"userIdentity": {
					"principalId": "AWS:AROAJNDVBL7WPMMDWOTYY:DW_Cartesian_ReportCollector"
				},
				"requestParameters": {
					"sourceIPAddress": "44.242.149.164"
				},
				"responseElements": {
					"x-amz-request-id": "1D651D17B1B4842B",
					"x-amz-id-2": "w+GZ+DBLhVla4f4Qh8WO7X/ypb3hISG0igTrKxBkZ0v7Yl1WLwmUUwaqVh3lL6IggYrFEMaSgJ89tI/lzb52H1jwBgdeqNI+"
				},
				"s3": {
					"s3SchemaVersion": "1.0",
					"configurationId": "DW_Cartesian_Raw",
					"bucket": {
						"name": "cf-datawarehouse",
						"ownerIdentity": {
							"principalId": "AEZILKLDOTNQJ"
						},
						"arn": "arn:aws:s3:::cf-datawarehouse"
					},
					"object": {
						"key": "data/raw/Cartesian/CenterfieldDetailedReports/month%3D2020-01/Cartesian_CenterfieldDetailedReports_2020-01.xlsx",
						"size": 18601503,
						"eTag": "f2c82ce53131855f07edf6dca7a0157b",
						"versionId": "jNoYRR1AdiKAtaiBeDvvhyrVYs31V.5z",
						"sequencer": "00602EBEAF9C397C40"
					}
				}
			}
		]
	}

	e_out = Payload(e_in)

	print(type(e_in), type(e_out))
	print(e_out.is_s3)


	# # Plain JSON or SQS (if we have Records with eventSource = SQS)
	# sqs_recs = Payload.get('Records')
	# if sqs_recs and sqs_recs[0].get('eventSource') == 'aws:sqs':
	# 	if len(sqs_recs) > 1:
	# 		raise RuntimeError('SQS: Only 1 message per batch is accepted')

	# 	# Convert SQS message body
	# 	report_req = json.loads(sqs_recs[0]['body'])
	# else:
	# 	# Plain invoke
	# 	report_req = event