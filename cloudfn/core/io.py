"""cloudfn-core io"""

import io
import bz2
import zlib

class MemStream():
	"""In-Memory compressed stream container"""
	def __init__(self, compression='bz2'):
		assert compression in [None, 'gz', 'bz2'], "Unsupported compression value!"

		self.byte_stream = io.BytesIO()
		self.compression = compression
		if compression == 'gz':
			self.compressor = zlib.compressobj(zlib.Z_BEST_COMPRESSION, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
		elif compression == 'bz2':
			self.compressor = bz2.BZ2Compressor(9)
		else:
			self.compressor = None

		self.writable = True
		self.raw_size = 0
		self.compressed_size = 0

	def __del__(self):
		self.byte_stream.close()

	def status(self):
		"""Prints current status"""
		print(f"{'Writable' if self.writable else 'Read-Only'} {self.compression} {self.raw_size} {self.compressed_size}")

	def write(self, b: bytes):
		"""Writes bytes to stream"""
		assert self.writable, "No longer writeable!"

		if self.compressor:
			self.byte_stream.write(self.compressor.compress(b))
		else:
			self.byte_stream.write(b)

		self.raw_size += len(b)
		self.compressed_size = self.byte_stream.tell()

	def writes(self, s: str, encoding='utf-8'):
		"""Writes string to stream"""
		self.write(s.encode(encoding))

	def writesn(self, s: str, encoding='utf-8'):
		"""Writes string, followed by newline to stream"""
		self.write(s.encode(encoding))
		self.write('\n'.encode(encoding))

	def done(self):
		"""Completes writing operations and returns the underlyng in-memory stream object"""
		self.writable = False
		if self.compressor:
			self.byte_stream.write(self.compressor.flush())
		self.byte_stream.flush()
		self.compressed_size = self.byte_stream.tell()
		self.byte_stream.seek(0)
		return self.byte_stream

if __name__ == "__main__":
	print('::Testing::')
	f = MemStream(compression='gz')
	f.status()
	f.writes("123456")
	f.status()
	f.done()
	#f.writes("7890")
	f.status()
	#boto3.client('s3').put_object(Bucket='bdc-bi-test', Key='testing123', Body=f.done())
	#f.status()
	print('::Done Testing::')

# import unittest

# class TestMemStream(unittest.TestCase):
# 	"""Unit Test for MemStream"""


# 	def test_uncompressed(self):
# 		"""bla"""
# 		ms = MemStream(compression=None)
# 		ms.writes('12345')
# 		self.assertEqual(ms.done().getvalue(), b'12345')
# 		del ms

# if __name__ == '__main__':
# 	unittest.main()
