"""cloudfn-aws event"""

from collections.abc import Mapping
from datetime import datetime
from hashlib import md5
import json
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

		# @property
		# def first(self):
		# 	"""First SQS Record"""
		# 	return self._payload.records[0]

		@property
		def first(self):
			"""First SQS Record"""
			return Payload.SQSEvent.SQSRecord(self._payload.first_record)

		class SQSRecord():
			"""SQS Record"""
			def __init__(self, raw_record):
				self._raw_record = raw_record

			def __getitem__(self, item):
				return self._raw_record.get(item)

			@property
			def body(self):
				"""Return parsed message body"""
				if body := self._raw_record.get('body'):
					return json.loads(body)

	class SNSEvent():
		"""SNS Event"""
		def __init__(self, payload):
			self._payload = payload

		@property
		def first(self):
			"""First SNS Record"""
			return Payload.SNSEvent.SNSRecord(self._payload.first_record)

		class SNSRecord():
			"""SNS Record"""
			def __init__(self, raw_record):
				self._raw_record = raw_record

			def __getitem__(self, item):
				return self._raw_record.get(item)

	class CWSEvent():
		"""CloudWatch Scheduled Event"""
		def __init__(self, payload):
			self._payload = payload

		def __getitem__(self, item):
			return self._payload[item]

		@property
		def event_id(self):
			"""Id"""
			return self._payload['id']

		@property
		def region(self):
			"""Region"""
			return self._payload['region']

		@property
		def account(self):
			"""Account"""
			return self._payload['account']

		@property
		def event_time_utc(self) -> datetime:
			"""Event Time in UTC"""
			return datetime.strptime(self._payload['time'], '%Y-%m-%dT%H:%M:%SZ')

		@property
		def event_time_utc_m(self) -> datetime:
			"""Event Time in UTC truncated to minute"""
			return self.event_time_utc.replace(second=0, microsecond=0)

		@property
		def resources(self):
			"""Resources"""
			return self._payload['resources']

		@property
		def detail(self):
			"""Detail"""
			return self._payload['detail']

	def __init__(self, event):
		"""Payload class init"""
		self.is_none = event is None
		self.is_mapping = isinstance(event, Mapping)
		self.raw_event = event

		self.records = event.get('Records')
		if not (isinstance(self.records, list) and len(self.records) > 0):
			self.records = None


		# Events that have records
		event_source = self.first_record.get('eventSource') if isinstance(self.first_record, Mapping) else event.get('source')
		self.is_s3 = event_source == 'aws:s3'
		self.is_sqs = event_source == 'aws:sqs'
		self.is_sns = event_source == 'aws:sns'

		# Events that do not have records
		self.is_cws = event_source == 'aws.events' and event.get('detail-type') == 'Scheduled Event'

	def __getitem__(self, item):
		if self.is_mapping:
			return self.raw_event.get(item)

		raise RuntimeError(f'Cannot `.get` on object of type {type(self.raw_event)}')

	@property
	def sqs_event(self):
		"""SQSEvent instance if this event is SQS event"""
		return Payload.SQSEvent(self) if self.is_sqs else None

	@property
	def s3_event(self):
		"""S3Event instance if this event is S3 event"""
		return Payload.S3Event(self) if self.is_s3 else None

	@property
	def sns_event(self):
		"""SNSEvent instance if this event is SNS event"""
		return Payload.SNSEvent(self) if self.is_sns else None

	@property
	def cws_event(self):
		"""CWSEvent instance if this event is CWS event"""
		return Payload.CWSEvent(self) if self.is_cws else None

	@property
	def first_record(self):
		"""First record if present"""
		return self.records[0] if self.records else None

	@property
	def aws_event(self):
		"""Specific event conversion"""
		if self.is_s3:
			return Payload.S3Event(self)
		elif self.is_sns:
			return Payload.SNSEvent(self)
		elif self.is_sqs:
			return Payload.SQSEvent(self)
		elif self.is_cws:
			return Payload.CWSEvent(self)

	@staticmethod
	def mock_s3_single(bucket_name, object_key,
		event_name='ObjectCreated:Put', aws_region='us-east-1', event_time: datetime=datetime.utcnow(),
		size=0, principal_id='', metadata=None):
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

	@staticmethod
	def mock_sqs_single(body, sent_time: datetime=datetime.utcnow(),
		aws_region='us-east-1', account_id='000000000000',queue_name='Mock_Queue',
		approximate_receive_count=1,message_id='00000000-0000-0000-0000-000000000000'):
		"""Mock single SQS event"""
		unix_ts = int(sent_time.timestamp() * 1000)
		_body = json.dumps(body) if isinstance(body, Mapping) else body
		return {
			"Records": [
				{
					"messageId": message_id,
					"receiptHandle": "MessageReceiptHandle",
					"body": _body,
					"attributes": {
						"ApproximateReceiveCount": str(approximate_receive_count),
						"SentTimestamp": str(unix_ts),
						"SenderId": account_id,
						"ApproximateFirstReceiveTimestamp": str(unix_ts + 1)
					},
					"messageAttributes": {}, #ToDo
					"md5OfBody": md5(_body.encode()).hexdigest() if _body else None,
					"eventSource": "aws:sqs",
					"eventSourceARN": f"arn:aws:sqs:{aws_region}:{account_id}:{queue_name}",
					"awsRegion": "us-east-1"
				}
			]
		}


	@staticmethod
	def mock_sns_single(message, subject=None, sent_time: datetime=datetime.utcnow(),
		aws_region='us-east-1', account_id='000000000000',topic_name='Mock_Topic',
		approximate_receive_count=1,message_id='00000000-0000-0000-0000-000000000000'):
		"""Mock single SNS event"""
		return {
			"Records": [
				{
					"EventSource": "aws:sns",
					"EventVersion": "1.0",
					"EventSubscriptionArn":f"arn:aws:sns:{aws_region}:{account_id}:{topic_name}",
					"Sns": {
						"Type": "Notification",
						"MessageId": message_id,
						"TopicArn": "arn:aws:sns:us-east-1:123456789012:ExampleTopic",
						"Subject": subject,
						"Message": message,
						"Timestamp": sent_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
						"SignatureVersion": "1",
						"Signature": "EXAMPLE",
						"SigningCertUrl": "EXAMPLE",
						"UnsubscribeUrl": "EXAMPLE",
						"MessageAttributes": {
							# ToDo
							# "Test": {
							# 	"Type": "String",
							# 	"Value": "TestString"
							# },
							# "TestBinary": {
							# 	"Type": "Binary",
							# 	"Value": "TestBinary"
							# }
						}
				}
				}
			]
			}

	@staticmethod
	def mock_cws_single(event_time: datetime=datetime.utcnow(),
		aws_region='us-east-1', account_id='000000000000',
		rule_name='Mock_Rule',event_id='00000000-0000-0000-0000-000000000000'):
		"""Mock single CloudWatch Scheduled event"""
		return {
			"id": event_id,
			"detail-type": "Scheduled Event",
			"source": "aws.events",
			"account": account_id,
			"time": event_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
			"region": aws_region,
			"resources": [f"arn:aws:events:{aws_region}:{account_id}:rule/{rule_name}"],
			"detail": {}
		}

if __name__ == '__main__':
	print('> Testing S3')
	e_in = Payload.mock_s3_single('random_bucket', 'random_key')
	e_out = Payload(e_in)
	print(f"Type In: {type(e_in)}, Type Parsed: {type(e_out)}")
	print(f"Detected event: {type(e_out.aws_event)}\n")

	print('> Testing SQS - String')
	e_in = Payload.mock_sqs_single('buddy')
	e_out = Payload(e_in)
	print(f"Type In: {type(e_in)}, Type Parsed: {type(e_out)}")
	print(f"Detected event: {type(e_out.aws_event)}\n")

	print('> Testing SQS - Dict')
	e_in = Payload.mock_sqs_single({'buddy': True})
	e_out = Payload(e_in)
	print(f"Type In: {type(e_in)}, Type Parsed: {type(e_out)}")
	print(f"Detected event: {type(e_out.aws_event)}\n")

	print('> Testing SNS - String')
	e_in = Payload.mock_sns_single('buddy')
	e_out = Payload(e_in)
	print(f"Type In: {type(e_in)}, Type Parsed: {type(e_out)}")
	print(f"Detected event: {type(e_out.aws_event)}\n")

	print('> Testing SNS - Dict')
	e_in = Payload.mock_sns_single({'buddy': True})
	e_out = Payload(e_in)
	print(f"Type In: {type(e_in)}, Type Parsed: {type(e_out)}")
	print(f"Detected event: {type(e_out.aws_event)}\n")

	print('> Testing CWS')
	e_in = Payload.mock_cws_single()
	e_out = Payload(e_in)
	print(f"Type In: {type(e_in)}, Type Parsed: {type(e_out)}")
	print(f"Detected event: {type(e_out.aws_event)}\n")

	print('> Testing non-AWS')
	e_in = Payload.mock_cws_single()
	e_out = Payload({'some_key': 'some_value'})
	print(f"Type In: {type(e_in)}, Type Parsed: {type(e_out)}")
	print(f"Detected event: {type(e_out.aws_event)}\n")

	exit()

	print('Testing CWS')
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

	e_in = {
		"id": "53dc4d37-cffa-4f76-80c9-8b7d4a4d2eaa",
		"detail-type": "Scheduled Event",
		"source": "aws.events",
		"account": "123456789012",
		"time": "2019-10-08T16:53:06Z",
		"region": "us-east-1",
		"resources": [ "arn:aws:events:us-east-1:123456789012:rule/MyScheduledRule" ],
		"detail": {}
	}
	e_out = Payload(e_in)

	print(type(e_in), type(e_out))
	print(type(e_out.aws_event))
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