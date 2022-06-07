from __future__ import annotations

import re
from typing import Tuple
from urllib.parse import urlparse as parse_url

import requests
import trafilatura
from requests import Response

from src.processing.web.domain import *
from src.processing.web.domain import ResponseInfo
from src.utils.monad import Result

REMOVE_UTM = re.compile( r"&?utm_(source|medium|campaign|term|content)=[^&]*&?" )

_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'


# noinspection PyTypeChecker
def _remove_params( url: Url[ URaw ] ) -> Url[ UClean ]:
	return url.update( {
			"query": REMOVE_UTM.sub( "", url.query ),
	} )


def _parse_url( url: String ) -> Result[ Url[ UClean ] ]:

	url = url.strip()
	parsed = parse_url( url )
	good = Url( hostname = parsed.hostname, scheme = parsed.scheme,
	            netloc = parsed.netloc, path = parsed.path,
	            query = parsed.query, raw = url )

	return Result.ok( good ).map( _remove_params )
#

def _mime_and_encoding( response: Response ) -> Tuple[ MimeType | None, String | None ]:
	headers: WebHeader = response.headers
	content_type = headers.get( "Content-Type", "" )
	match content_type.split( ";" ):
		case [ mime, charset ]:
			mime_type = mime
			encoding = charset.split( "=" )[ 1 ]
		case [ mime ]:
			mime_type = mime
			encoding = None
		case _:
			mime_type = None
			encoding = None

	return mime_type, encoding


def _fetch_url( url: Url[ ... ], headers: Mapping[ String, String ] = None ) -> Result[ ResponseInfo ]:
	headers = headers or { 'User-Agent': _USER_AGENT }
	try:
		response = requests.get( url.raw, headers = headers )
		if response.ok:
			headers = response.headers
			mime_type, encoding = _mime_and_encoding( response )
			info = ResponseInfo( url = url,
			                     headers = headers,
			                     content = response.content,
			                     mime = mime_type,
			                     encoding = encoding )
			return Result.ok( info )

		exception = PageException( url = url,
		                           status = response.status_code,
		                           message = response.reason )
		return Result.failure( exception )
	except Exception as e:
		return Result.failure( e )


#

#

def _parse_trafilatura( info: ResponseInfo ) -> PageInfo:
	encoding = info.encoding or "utf8"
	text = info.content.decode(  encoding )
	extract = trafilatura.bare_extraction( filecontent = text,
	                                       include_comments = False,
	                                       include_images = True,
	                                       include_formatting = True,
	                                       include_links = True,
	                                       )

	if not text:
		raise Exception( "No text found" )

	return PageInfo(
			url = info.url,
			text = extract.get( "text", None ),
			title = extract.get( "title", None ),
			author = extract.get( "author", None ),
			date = extract.get( "date", None ),
			categories = extract.get( "categories", None ),
			tags = extract.get( "tags", None ),
			comments = [ ],
			neighbors = [ ] )


def _switch_parsers( info: ResponseInfo ) -> Result[ PageInfo[ CRich ] ]:
	match info.mime:
		case "text/html":
			return Result.ok( info ).map( _parse_trafilatura )
		case "application/pdf":
			ex = Exception( "PDF not supported for now" )
			return Result.failure( ex )
		case other:
			ex = Exception( f"Unsupported mime type {other}" )
			return Result.failure( ex )


#
def default_url_parser() -> UrlParser:
	return _parse_url


def default_fetcher() -> WebFetcher:
	return _fetch_url


def default_content_parser() -> ContentParser:
	return _switch_parsers


if __name__ == '__main__':

	import unittest


	# noinspection PyBroadException
	class TestUrlParsing( unittest.TestCase ):

		def testParseDoesNotThrow( self ):
			try:
				parse = default_url_parser()
				parse( "a hundred percent not a url" )
				self.assertTrue( True )
			except:
				self.assertTrue( False )

		def testBasicParsing( self ):
			parse = default_url_parser()
			parsed = parse( "https://akti.canelhas.io/resource/1.html?param=1#fragment" ).unwrap()
			self.assertEqual( parsed.scheme, "https" )
			self.assertEqual( parsed.hostname, "akti.canelhas.io" )
			self.assertEqual( parsed.path, "/resource/1.html" )
			self.assertEqual( parsed.query, "param=1" )

		def testCleanUrl( self ):
			parse = default_url_parser()
			cleaned = parse( "https://akti.canelhas.io/resource/1.html?utm_campaign=alguma&param=1&utm_source=medium#fragment" ).unwrap()
			self.assertEqual( cleaned.query, "param=1" )


	unittest.main()
