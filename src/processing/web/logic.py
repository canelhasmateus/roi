from __future__ import annotations

import mimetypes
import re
from typing import Callable
from urllib.parse import urlparse as parse_url

import requests
import trafilatura
from requests import Response

from src.processing.web.domain import *
from src.utils.monad import Result

# noinspection PyMethodMayBeStatic
_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'


class PageException( Exception ):
	def __init__( self, url, status, message ):
		self.url = url
		self.status = status
		self.message = message


class UrlParser:
	remove_utm = re.compile( r"&?utm_(source|medium|campaign|term|content)=[^&]*&?" )

	def __call__( self, url: String ) -> Result[ Url[ UClean ] ]:
		return self.transform( url )

	def transform( self, url: String ) -> Result[ Url[ UClean ] ]:
		return self.parse( url ).map( self.clean )

	def parse( self, url: String ) -> Result[ Url[ URaw ] ]:
		return (Result.ok( url )
		        .map( parse_url )
		        .map( lambda parsed: Url( hostname = parsed.hostname,
		                                  scheme = parsed.scheme,
		                                  netloc = parsed.netloc,
		                                  path = parsed.path,
		                                  query = parsed.query,
		                                  raw = url ) ))

	def clean( self, url: Url[ URaw ] ) -> Url[ UClean ]:
		# noinspection PyTypeChecker
		return url.update( {
				"query": self.remove_utm.sub( "", url.query ),
		} )


class UrlFetcher:
	def __init__( self, fn: Callable[ [ Url, WebHeader ], Response ] = None ):
		self.fn = fn
		if not self.fn:
			self.fn = lambda u, h: requests.get( u, headers = h )

	def __call__( self, url: Url ) -> Result[ PageInfo ]:
		return self.fetch( url )

	def fetch( self, url: Url[ ... ] ) -> Result[ PageInfo ]:
		return (Result.ok( url.raw )
		        .map( self._get )
		        .flatMap( lambda response: self._parse( url, response ) ))

	def _get( self, url: String ) -> Response:
		return self.fn( url, {
				'User-Agent': _USER_AGENT
		} )

	def _parse( self, url: Url[ ... ], response: Response ) -> Result[ PageInfo ]:
		if not response.ok:
			exception = PageException( url = url,
			                           status = response.status_code,
			                           message = response.reason )

			return Result.failure( exception )

		headers: WebHeader = response.headers
		content_type = headers.get( "Content-Type", "" )
		match content_type.split( ";" ):
			case [ mime, charset ]:
				mime_type = mime
				encoding = charset.split( "=" )[ 1 ]
			case [ mime ]:
				mime_type = mime
				encoding = None

		info = PageInfo( url = url,
		                 headers = headers,
		                 content = response.content,
		                 mime = mime_type,
		                 encoding = encoding )

		return Result.ok( info )


class ContentParser:

	def __call__( self, info: PageInfo ):
		return self.parser( info )

	def parser( self, info: PageInfo ) -> Result[ PageContent[ CRich ] ]:
		match info.mime:
			case "text/html":
				text = info.content.decode( info.encoding )
				extract = trafilatura.bare_extraction( filecontent = text,
				                                       include_comments = False,
				                                       include_images = True,
				                                       include_formatting = True,
				                                       include_links = True,
				                                       )

				result = PageContent(
						text = extract.get( "text", None ),
						title = extract.get( "title", None ),
						author = extract.get( "author", None ),
						date = extract.get( "date", None ),
						categories = extract.get( "categories", None ),
						tags = extract.get( "tags", None ),
						comments = [],
						neighbors = [ ])
				match result.text:
					case None:
						return Result.failure( Exception( "No text found" ) )
					case _:
						return Result.ok( result )
			case "application/pdf":
				# todo implement
				ex = Exception( "PDF not supported for now" )
				return Result.failure( ex )
			case other:
				ex = Exception( f"Unsupported mime type {other}" )
				return Result.failure( ex )


if __name__ == '__main__':

	import unittest


	# noinspection PyBroadException
	class TestUrlParsing( unittest.TestCase ):

		def testParseDoesNotThrow( self ):
			try:
				parser = UrlParser()
				parser.parse( "a hundred percent not a url" )
				self.assertTrue( True )
			except:
				self.assertTrue( False )

		def testBasicParsing( self ):
			parser = UrlParser()
			parser.parse( "" )
			parsed = parser.parse( "https://akti.canelhas.io/resource/1.html?param=1#fragment" ).unwrap()
			self.assertEqual( parsed.scheme, "https" )
			self.assertEqual( parsed.hostname, "akti.canelhas.io" )
			self.assertEqual( parsed.path, "/resource/1.html" )
			self.assertEqual( parsed.query, "param=1" )

		def testCleanUrl( self ):
			parser = UrlParser()
			cleaned = parser.transform( "https://akti.canelhas.io/resource/1.html?utm_campaign=alguma&param=1&utm_source=medium#fragment" ).unwrap()
			self.assertEqual( cleaned.query, "param=1" )


	# noinspection PyBroadException
	class TestUrlFetching( unittest.TestCase ):

		fake_url = Url( raw = "def not a url my friendo",
		                scheme = "",
		                netloc = "",
		                path = "",
		                query = "",
		                hostname = "",
		                )

		fake_response_bad = Response()
		fake_response_bad.status_code = 404
		fake_response_bad.reason = "Not Found"
		fake_response_bad.headers = { }
		fake_response_bad._content = None

		fake_response_good = Response()
		fake_response_good.status_code = 200
		fake_response_good.reason = "OK"
		fake_response_good.headers = { "Content-Type": "text/html; charset=utf-8" }
		fake_response_good._content = b"some content"

		def testFetchDoesNotThrow( self ):
			try:
				fn = lambda x, y: exec( """
				 raise( Exception() )
				""" )
				fetcher = UrlFetcher( fn )
				fetcher.fetch( self.fake_url )
				self.assertTrue( True )
			except:
				self.assertTrue( False )

		def testBadFetching( self ):
			fetcher = UrlFetcher( lambda x, y: self.fake_response_bad )
			response = fetcher.fetch( self.fake_url )
			self.assertRaises( PageException, lambda: response.unwrap() )

		def testGoodFetching( self ):
			fetcher = UrlFetcher( lambda x, y: self.fake_response_good )
			response = fetcher.fetch( self.fake_url ).unwrap()
			self.assertEquals( response.content, self.fake_response_good.content )


	unittest.main()
