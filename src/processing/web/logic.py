from __future__ import annotations

import itertools
import pathlib
import re
from types import SimpleNamespace
from typing import Tuple, Optional
from urllib.parse import urlparse as parse_url

import lxml.etree
import lxml.html
import requests
import trafilatura
import trafilatura.spider
from lxml import etree
from requests import Response

from src.processing.web.domain import *
from src.processing.web.domain import ResponseInfo
from src.utils.monad import Result

_RE_FIND_YOUTUBE_ID = re.compile( r"v=([a-zA-Z0-9]+(?=\b|&))" )
_RE_REMOVE_UTM = re.compile( r"&?utm_(source|medium|campaign|term|content)=[^&]*&?" )
_RE_REMOVE_TIMESTAMP = re.compile( r"&?t=\d+[^&]*&?" )
_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'

remove_utm = lambda x: _RE_REMOVE_UTM.sub( "", x )
remove_timestamp = lambda x: _RE_REMOVE_TIMESTAMP.sub( "", x )
find_youtube_id = lambda url: _RE_FIND_YOUTUBE_ID.search( url ).group()


# noinspection PyTypeChecker

def _remove_params( url: Url[ URaw ] ) -> Url[ UClean ]:
	replacers = [ remove_utm ]
	query = url.query

	if url.kind == UrlKinds.YOUTUBE:
		replacers.append( remove_timestamp )

	for transform in replacers:
		query = transform( query )

	return url.update( { "query": query } )


def _parse_url( line: TabSeparated ) -> Result[ Url[ UClean ] ]:
	date, quality, url = line.strip().split( "\t" )
	parsed = parse_url( url )

	good = Url(
			raw = url,
			quality = quality,
			hostname = parsed.hostname,
			scheme = parsed.scheme or "http",
			netloc = parsed.netloc,
			path = parsed.path or "",
			query = parsed.query or ""
	)

	if not good.hostname:
		return Result.failure( Exception( "No hostname found" ) )

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
			encoding = "utf-8"
		case _:
			mime_type = "text/html"
			encoding = "utf-8"

	return mime_type, encoding


def _fetch_url( url: Url[ ... ], headers: Mapping[ String, String ] = None ) -> Result[ ResponseInfo ]:
	headers = headers or { 'User-Agent': _USER_AGENT }
	# TODO  07/06/2022 conditionally change fetchers
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


class Htmls( SimpleNamespace ):

	@staticmethod
	def markdown_references( text: String ) -> PageInfo:
		return [ ]

	@staticmethod
	def generic_info( response: ResponseInfo, page: lxml.html.HtmlElement ) -> PageInfo:

		result = trafilatura.bare_extraction(
				filecontent = page,
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

		neighbors = Htmls.markdown_references( text )
		return PageInfo(
				url = response.url,
				text = text,
				title = title,
				author = author,
				date = date,
				categories = categories,
				tags = tags,
				comments = [ ],
				neighbors = neighbors )

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

	@staticmethod
	def page_info( info: ResponseInfo ) -> Result[ PageInfo ]:
		encoding = info.encoding or "utf8"
		html_element = etree.HTML( info.content.decode( encoding ) )
		base_result = Htmls.generic_info( info, html_element )
		text = base_result.text
		match info.url.kind:
			case UrlKinds.YOUTUBE:
				text = Htmls._youtube_transcript( info ).orElse( text )
			case UrlKinds.ARXIV:
				return Result.failure( Exception( "Arxiv, but html." ) )
			case UrlKinds.DATASKEPTIC:
				return Result.failure( Exception( "Probably audio" ) )
			case UrlKinds.GITHUBIO:
				return Result.failure( Exception( "Github.io " ) )
			case _:
				...

		Result.ok( base_result.with_text( text ) )


def _switch_parsers( info: ResponseInfo ) -> Result[ PageInfo[ CRich ] ]:
	match info.mime:
		case "text/html":
			return Htmls.page_info( info )
		case "application/pdf":
			return Result.failure( Exception( "PDF not supported for now" ) )
		case other:
			return Result.failure( Exception( f"Unsupported mime type {other}" ) )


#
def default_url_parser() -> UrlParser:
	return _parse_url


def default_fetcher() -> WebFetcher:
	return _fetch_url


def default_content_parser() -> PageParser:
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
