from domain import *
from src.utils.monad import Result
from urllib.parse import urlparse as parse_url


def to_url(url: String) -> Result[ Url[ URaw ] ]:
	return (
		Result.ok( url )
		.map( lambda raw: parse_url( raw ) )
		.map( lambda parsed: Url( hostname=parsed.hostname,
		                          scheme=parsed.scheme,
		                          netloc=parsed.netloc,
		                          path=parsed.path,
		                          query=parsed.query,
		                          raw=url ) ))


def to_info(value: String) -> Result[ PageInfo ]:
	return (
		to_url( value )
		.map( _clean_url )
		.flatMap( _fetch_info ))


def to_content(value: String) -> Result[ PageContent[ CRich ] ]:
	return (
		to_info( value )
		.map( _parse_content )
		.map( _enrich_content ))


def _clean_url(url: Url[ URaw ]) -> Url[ UClean ]:
	...


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
		CANELHASIO = "https://akti.canelhas.io/resource/1.html?param=1#fragment"

		def testUrlDoesNotThrow(self):
			try:
				to_url( "" )
				self.assertTrue( True )
			except:
				self.assertTrue( False )

		def testBasicParsing(self):
			parsed = to_url( self.CANELHASIO ).unwrap()
			self.assertEqual( parsed.scheme, "https" )
			self.assertEqual( parsed.hostname, "akti.canelhas.io" )
			self.assertEqual( parsed.path, "/resource/1.html" )
			self.assertEqual( parsed.query, "param=1" )


	unittest.main()
