import re

from domain import *
from src.utils.monad import Result
from urllib.parse import urlparse as parse_url, ParseResult


# noinspection PyMethodMayBeStatic
class UrlParser:
	remove_utm = re.compile( r"&?utm_(source|medium|campaign|term|content)=[^&]*&?" )

	def transform(self, url: String) -> Result[ Url[ UClean ] ]:
		return self.parse( url ).map( self.clean )

	def parse(self, url: String) -> Result[ Url[ URaw ] ]:
		return (Result.ok( url )
		        .map( parse_url )
		        .map( lambda parsed: Url( hostname = parsed.hostname,
		                                  scheme = parsed.scheme,
		                                  netloc = parsed.netloc,
		                                  path = parsed.path,
		                                  query = parsed.query,
		                                  raw = url ) ))

	def clean(self, url: Url[ URaw ]) -> Url[ UClean ]:
		# noinspection PyTypeChecker
		return url.update( {
				"query": self.remove_utm.sub( "", url.query ),
		} )


class UrlFetcher:

	def __init__(self, url: Url[ UClean ]):
		...

	def fetch(self, url: Url[ ... ]) -> Result[ PageInfo ]:
		...


def _to_info(self, value: String) -> Result[ PageInfo ]:
	return (self._to_url( value )
	        .map( _clean_url )
	        .flatMap( _fetch_info ))


def to_content(value: String) -> Result[ PageContent[ CRich ] ]:
	return (
			to_info( value )
			.map( _parse_content )
			.map( _enrich_content ))


def _fetch_info(url: Url[ UClean ]) -> Result[ PageInfo ]:
	...


def _parse_content(info: PageInfo) -> PageContent[ CRaw ]:
	...


def _enrich_content(content: PageContent[ CRaw ]) -> PageContent[ CRich ]:
	...


if __name__ == '__main__':

	import unittest


	# noinspection PyBroadException
	class TestUrlParsing( unittest.TestCase ):

		def testUrlDoesNotThrow(self):
			try:
				parser = UrlParser()
				parser.parse( "a hundred percent not a url" )
				self.assertTrue( True )
			except:
				self.assertTrue( False )

		def testBasicParsing(self):
			parser = UrlParser()
			parser.parse( "" )
			parsed = parser.parse( "https://akti.canelhas.io/resource/1.html?param=1#fragment" ).unwrap()
			self.assertEqual( parsed.scheme, "https" )
			self.assertEqual( parsed.hostname, "akti.canelhas.io" )
			self.assertEqual( parsed.path, "/resource/1.html" )
			self.assertEqual( parsed.query, "param=1" )

		def testCleanUrl(self):
			parser = UrlParser()
			cleaned = parser.transform( "https://akti.canelhas.io/resource/1.html?utm_campaign=alguma&param=1&utm_source=medium#fragment" ).unwrap()
			self.assertEqual( cleaned.query, "param=1" )


	unittest.main()
