from __future__ import annotations

import itertools
import re
import urllib.parse
from types import SimpleNamespace

import lxml.etree
import lxml.html
import requests
import trafilatura
import trafilatura.spider
from lxml import etree

from src.processing.web.domain import *
from src.processing.web.domain import ResponseInfo
from src.utils.monad import Result

_RE_FIND_YOUTUBE_ID = re.compile( r"v=([a-zA-Z0-9]+(?=\b|&))" )
_RE_REMOVE_UTM = re.compile( r"&?utm_(source|medium|campaign|term|content)=[^&]*&?" )
_RE_REMOVE_TIMESTAMP = re.compile( r"&?t=\d+[^&]*&?" )
remove_utm = lambda x: _RE_REMOVE_UTM.sub( "", x )
remove_timestamp = lambda x: _RE_REMOVE_TIMESTAMP.sub( "", x )
find_youtube_id = lambda url: _RE_FIND_YOUTUBE_ID.search( url ).group()


class EventParsing( SimpleNamespace ):
	def _remove_params( url: UrlEvent[ URaw ] ) -> UrlEvent[ UNorm ]:
		replacers = [ remove_utm ]
		query = url.query

		if url.kind == UrlKinds.YOUTUBE:
			replacers.append( remove_timestamp )

		for transform in replacers:
			query = transform( query )

		# noinspection PyTypeChecker
		return url.update( { "query": query } )

	def parse_url( line: TabSeparated ) -> Result[ UrlEvent[ UNorm ] ]:
		date, quality, url = line.strip().split( "\t" )
		parsed = urllib.parse.urlparse( url )
		# TODO  08/06/2022 Still a lot to do here. It seems to be tripping with very basic input , specially when scheme is not specifiec.
		good = UrlEvent(
				raw = url,
				quality = quality,
				hostname = parsed.hostname or "",
				scheme = parsed.scheme or "http",
				netloc = parsed.netloc,
				path = parsed.path or "",
				query = parsed.query or ""
		)

		if not good.hostname:
			print( f"{good.raw} hostname bug" )
			return Result.failure( Exception( "No hostname found" ) )

		return Result.ok( good ).map( EventParsing._remove_params )


class Htmls( SimpleNamespace ):

	@staticmethod
	def as_element( response: Response ) -> lxml.html.HtmlElement:
		encoding = Htmls.encoding( response )
		return etree.HTML( response.content.decode( encoding ) )

	@staticmethod
	def mime( response: Response ) -> MimeType:
		headers: WebHeader = response.headers
		content_type = headers.get( "Content-Type", "" )
		match content_type.split( ";" ):
			case [ mime, _ ]:
				mime_type = mime
			case [ mime ]:
				mime_type = mime
			case _:
				mime_type = "text/html"
		return mime_type

	@staticmethod
	def encoding( response: Response ) -> TextEncoding:
		headers = response.headers
		content_type = headers.get( "Content-Type", "" )
		match content_type.split( ";" ):
			case [ _, charset ]:
				encoding = charset.split( "=" )[ 1 ]
			case [ _ ]:
				encoding = "utf-8"
			case _:
				encoding = "utf-8"
		return encoding

	@staticmethod
	def toText( e ):
		return map( lambda x: x.text, e )

	@staticmethod
	def toAttrib( attr, e ):
		return map( lambda x: x.get( attr ), e )

	@staticmethod
	def first( *args ):
		for i in itertools.chain.from_iterable( args ):
			if i:
				return i
		return ""

	@staticmethod
	def getDuration( html: etree.HTML ):
		duration = Htmls.toAttrib( "content", html.xpath( "//meta[@name='duration']" ) )
		return Htmls.first( duration )

	@staticmethod
	def getTitle( html: etree.HTML ) -> String:

		articleTitle = Htmls.toText( html.xpath( "//article/h1" ) )
		itemProp = Htmls.toAttrib( "content", html.xpath( "//meta[@itemprop='name']" ) )
		ogTitle = Htmls.toAttrib( "content", html.xpath( "//meta[@name='og:title']" ) )
		titleFromAnywhere = Htmls.toText( html.xpath( "//title" ) )
		titleFromHead = Htmls.toText( html.xpath( "//head/title" ) )
		twitterTitle = Htmls.toAttrib( "content", html.xpath( "//meta[@name='twitter:title']" ) )

		return Htmls.first(
				ogTitle, twitterTitle, itemProp,
				articleTitle, titleFromHead, titleFromAnywhere )

	@staticmethod
	def getDescription( html: etree.HTML ) -> String:

		anyParagraph = Htmls.toText( html.xpath( "//p" ) )
		articleParagraph = Htmls.toText( html.xpath( "//article//p" ) )
		itemProp = Htmls.toAttrib( "content", html.xpath( "//meta[@itemprop='description']" ) )
		metaDescr = Htmls.toAttrib( "content", html.xpath( "//meta[@name='description']" ) )
		ogDescr = Htmls.toAttrib( "content", html.xpath( "//meta[@name='og:description']" ) )
		twitterDescr = Htmls.toAttrib( "content", html.xpath( "//meta[@name='twitter:description']" ) )

		return Htmls.first( ogDescr, twitterDescr, itemProp, metaDescr,
		                    articleParagraph, anyParagraph )

	@staticmethod
	def getImage( html: etree.HTML ) -> String:

		anyImage = Htmls.toAttrib( "src", html.xpath( "//img" ) )
		headIcon = Htmls.toAttrib( "href", html.xpath( "//head/link[@rel='icon']" ) )
		itemProp = Htmls.toAttrib( "content", html.xpath( "//meta[@itemprop='image']" ) )
		ogImage = Htmls.toAttrib( "content", html.xpath( "//meta[@property='og:image']" ) )
		twitterImage = Htmls.toAttrib( "content", html.xpath( "//meta[@name='twitter:image']" ) )

		return Htmls.first( ogImage, twitterImage, itemProp, headIcon, anyImage )

	@staticmethod
	def getHtmlStructure( response: Response ) -> ResponseEnrichment:
		html_element = Htmls.as_element( response )
		result = trafilatura.bare_extraction( filecontent = html_element,
		                                      include_comments = False,
		                                      include_images = True,
		                                      include_formatting = True,
		                                      include_links = True,
		                                      )

		text = result.get( "text", None )
		title = result.get( "title", None )
		author = result.get( "author", None )
		date = result.get( "date", None )
		categories = result.get( "categories", None )
		tags = result.get( "tags", None )
		neighbors = [ ]

		# TODO  08/06/2022

		return ResponseEnrichment(
				text = text,
				title = title,
				author = author,
				date = date,
				categories = categories,
				tags = tags,
				comments = [ ],
				neighbors = neighbors )

	@staticmethod
	def parse_structure( info: Response ) -> Result[ ResponseEnrichment ]:
		match Htmls.mime( info ):
			case "text/html":
				return Result.ok( info ).flatMap( Htmls.getHtmlStructure )


class Youtube( SimpleNamespace ):
	@staticmethod
	def _youtube_transcript( info: ResponseInfo ) -> Result[ String ]:

		try:
			id = find_youtube_id( info.url.query )
			response = requests.get( "https://youtubetranscript.com/", params = { "server_vid": id } )
			root = lxml.etree.fromstring( response.text )
			text = " ".join( root.itertext() )
			if text == 'Error: transcripts disabled for that video':
				return Result.failure( Exception( "No transcript for this video" ) )
			return Result.ok( text )
		except Exception as e:
			return Result.failure( e )

	...


_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'


class Enrichment( SimpleNamespace ):
	...

	@staticmethod
	def _fetch_url( url: UrlEvent[ ... ], headers: Mapping[ String, String ] = None ) -> Result[ ResponseInfo ]:
		headers = headers or { 'User-Agent': _USER_AGENT }
		try:
			response = requests.get( url.raw, headers = headers )
			if response.ok:
				rich = Htmls.parse_structure( response ).orElse( None )
				info = ResponseInfo( url = url, content = response, structure = rich )
				return Result.ok( info )
			return Result.failure( Exception( "Response was not ok" ) )
		except Exception as e:
			return Result.failure( e )

	@staticmethod
	def _parse_response( info: ResponseInfo ) -> Result[ ResponseInfo ]:
		match info.mime:
			case "text/html":
				return Htmls.parse_structure( info )
			case "application/pdf":
				return Result.failure( Exception( "PDF not supported for now" ) )
			case other:
				return Result.failure( Exception( f"Unsupported mime type {other}" ) )


#
def default_url_parser() -> EventParser:
	return EventParsing.parse_url


def default_response_fetcher() -> WebFetcher:
	return _fetch_url


def default_response_processer() -> ResponseProcesser:
	return _parse_response


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
			parsed = parse( "https://akti.canelhas.io/resource/1.html?param=1#fragment" ).expect()
			self.assertEqual( parsed.scheme, "https" )
			self.assertEqual( parsed.hostname, "akti.canelhas.io" )
			self.assertEqual( parsed.path, "/resource/1.html" )
			self.assertEqual( parsed.query, "param=1" )

		def testCleanUrl( self ):
			parse = default_url_parser()
			cleaned = parse( "https://akti.canelhas.io/resource/1.html?utm_campaign=alguma&param=1&utm_source=medium#fragment" ).expect()
			self.assertEqual( cleaned.query, "param=1" )


	unittest.main()
