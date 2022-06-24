from __future__ import annotations

import io

from aiohttp import ClientSession
from warcio import ArchiveIterator, StatusAndHeaders
from warcio.capture_http import capture_http
from warcio.warcwriter import BufferWARCWriter

_a = None

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

from .domain import *


class Events( SimpleNamespace ):
	_RE_REMOVE_UTM = re.compile( r"&?utm_(source|medium|campaign|term|content)=[^&]*&?" )
	_RE_REMOVE_TIMESTAMP = re.compile( r"&?t=\d+[^&]*&?" )
	remove_utm = lambda x: Events._RE_REMOVE_UTM.sub( "", x )
	remove_timestamp = lambda x: Events._RE_REMOVE_TIMESTAMP.sub( "", x )

	@staticmethod
	def _remove_params( url: UrlEvent[ URaw ] ) -> UrlEvent[ UNorm ]:
		replacers = [ Events.remove_utm ]
		query = url.query

		if url.kind == UrlKinds.YOUTUBE:
			replacers.append( Events.remove_timestamp )

		for transform in replacers:
			query = transform( query )

		# noinspection PyTypeChecker
		return url.update( { "query": query } )

	@staticmethod
	def parse_url( line: TabSeparated ) -> Result[ UrlEvent[ UNorm ] ]:
		date, quality, url = line.strip().split( "\t" )
		parsed = urllib.parse.urlparse( url )
		# TODO  08/06/2022 Still a lot to do here. It seems to be tripping with very basic input , specially when scheme is not specific.
		good = UrlEvent( raw = url,
		                 quality = quality,
		                 hostname = parsed.hostname or "",
		                 scheme = parsed.scheme or "http",
		                 netloc = parsed.netloc,
		                 path = parsed.path or "",
		                 query = parsed.query or "" )

		if not good.hostname:
			print( f"{good.raw} hostname bug" )
			return Result.failure( Exception( "No hostname found" ) )

		return Result.ok( good ).map( Events._remove_params )


class Fetching( SimpleNamespace ):
	_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'

	@staticmethod
	async def async_fetch_url( session: ClientSession, url: UrlEvent ):
		async with session.get( url.raw, headers = { "User-Agent": Fetching._USER_AGENT } ) as resp:
			# TODO  23/06/2022 checar serialibilidade dos headers.
			response = NetworkArchive( response_status = resp.status,
			                           response_charset = resp.charset,
			                           response_content = await resp.read(),
			                           response_content_type = resp.content_type,
			                           response_headers = resp.headers,
			                           response_url = str( resp.url ),
			                           response_real_url = str( resp.real_url ),
			                           host = resp.host,
			                           request_headers = resp.request_info.headers,
			                           request_method = resp.request_info.method,
			                           request_url = str( resp.request_info.url ),
			                           request_real_url = str( resp.request_info.real_url ),
			                           )

			return WebArchive( url = url, content = response )


class Youtube( SimpleNamespace ):
	_RE_FIND_DURATION = re.compile( r"PT(\d+)M(\d+)S" )

	@staticmethod
	def title( html: etree.HTML ) -> String | None:
		title = Htmls.toAttrib( "content", html.xpath( "//meta[@itemprop='name']" ) )
		title = Htmls.first( title )
		return title

	@staticmethod
	def duration( html: etree.HTML ) -> Second | None:
		from_itemprop = Htmls.toAttrib( "content", html.xpath( "//meta[@itemprop='duration']" ) )
		duration = Htmls.first( from_itemprop )
		match = Youtube._RE_FIND_DURATION.match( duration )
		if not match:
			return None
		minutes = int( match.group( 1 ) )
		seconds = int( match.group( 2 ) )
		return minutes * 60 + seconds

	@staticmethod
	def date( element: lxml.html.HtmlElement ) -> IsoTime:
		date = Htmls.toAttrib( "content", element.xpath( "//meta[@itemprop='datePublished']" ) )
		date = Htmls.first( date )
		if date:
			...
		return date

	@staticmethod
	def image( element: lxml.html.HtmlElement ) -> String | None:
		url = Htmls.toAttrib( "href", element.xpath( "//link[@itemprop='thumbnailUrl']" ) )
		url = Htmls.first( url )
		if url:
			...
		return url

	@staticmethod
	def tags( element: lxml.html.HtmlElement ) -> Iterable[ String ] | None:
		from_itemprop = Htmls.toAttrib( "content", element.xpath( "//meta[@name='keywords']" ) )
		tags = Htmls.first( from_itemprop )
		if tags:
			tags = tags.split( "," )
			tags = { content.strip() for content in tags }
		return tags

	@staticmethod
	def neighbors( element: lxml.html.HtmlElement ) -> Iterable[ String ]:
		# TODO  10/06/2022 parse the video description
		return [ ]

	@staticmethod
	def categories( element: lxml.html.HtmlElement ) -> Iterable[ String ]:
		genres = Htmls.toAttrib( "content", element.xpath( "//meta[@itemprop='genre']" ) )
		genres = Htmls.first( genres )
		if genres:
			genres = genres.split( "," )

		return genres

	@staticmethod
	def comments( element: lxml.html.HtmlElement ) -> Iterable[ String ]:
		return [ ]

	@staticmethod
	def author( element: lxml.html.HtmlElement ) -> String:
		author = Htmls.toAttrib( "href", element.xpath( "//span[@itemprop='author']/link[@itemprop='url']" ) )
		author = Htmls.first( author )
		return author

	@staticmethod
	def text( element: lxml.html.HtmlElement ) -> String:
		if True:
			return ""

		video_id = Htmls.toAttrib( "content", element.xpath( "//meta[@itemprop='videoId']" ) )
		response = requests.get( "https://youtubetranscript.com/", params = { "server_vid": video_id } )
		root = lxml.etree.fromstring( response.text )
		text = " ".join( root.itertext() )
		if not response.ok or text == 'Error: transcripts disabled for that video':
			print( f"Transcripts disabled for that video with id {video_id}" )
		return text

	@staticmethod
	def structure( response: WebArchive ) -> PageContent:
		element = Htmls.element( response )

		duration = Youtube.duration( element )
		if not duration:
			print( "No Duration" )
		return PageContent( url = response.url,
		                    text = Youtube.text( element ),
		                    title = Youtube.title( element ),
		                    duration = duration,
		                    tags = Youtube.tags( element ),
		                    author = Youtube.author( element ),
		                    categories = Youtube.categories( element ),
		                    date = Youtube.date( element ),
		                    neighbors = Youtube.neighbors( element ),
		                    comments = Youtube.comments( element ),
		                    image = Youtube.image( element ) )


class Htmls( SimpleNamespace ):

	@staticmethod
	def mime( response: WebArchive ) -> MimeType:
		readers: WebHeader = response.content.headers
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
	def structure( response: WebArchive ) -> PageContent:
		html_element = Htmls.element( response.content )
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
		image = Htmls.getImage( html_element )
		neighbors = [ ]

		if author or date or categories or tags or neighbors:
			print( "Lucro" )
		# TODO  08/06/2022 - preview
		if image:
			print( "Imagem" )
		return PageContent( url = response.url,
		                    text = text,
		                    title = title,
		                    author = author,
		                    date = date,
		                    categories = categories,
		                    tags = tags,
		                    image = image,
		                    comments = [ ],
		                    neighbors = neighbors
		                    )

	@staticmethod
	def element( response: WebArchive | Response | String ) -> lxml.html.HtmlElement:

		if isinstance( response, WebArchive ):
			content = response.content.content.decode( "utf-8" )
		elif isinstance( response, (Response, NetworkArchive) ):
			content = response.content.decode( "utf-8" )
		elif isinstance( response, String ):
			content = response
		else:
			content = ""

		return lxml.html.fromstring( content )

	@staticmethod
	def getHtmlStructure( response: WebArchive ) -> Result[ PageContent ]:

		match response.url.kind:
			case UrlKinds.YOUTUBE:
				return Result.ok( response ).map( Youtube.structure )
			case _:
				return Result.ok( response ).map( Htmls.structure )


class Processing( SimpleNamespace ):

	@staticmethod
	def parse_response( info: WebArchive ) -> Result[ PageContent ]:

		match Htmls.mime( info ):
			case "text/html":
				return Result.ok( info ).flatMap( Htmls.getHtmlStructure )
			case "application/pdf":
				return Result.failure( Exception( "PDF not supported for now" ) )
			case other:
				return Result.failure( Exception( f"Unsupported mime type {other}" ) )

	@staticmethod
	async def parse_response_async( session: ClientSession, info: WebArchive ) -> Result[ PageContent ]:
		match Htmls.mime( info ):
			case "text/html":
				return Result.ok( info ).flatMap( Htmls.getHtmlStructure )
			case "application/pdf":
				return Result.failure( Exception( "PDF not supported for now" ) )
			case other:
				return Result.failure( Exception( f"Unsupported mime type {other}" ) )


#


def default_url_parser() -> EventParser:
	return Events.parse_url


def default_response_fetcher() -> WebFetcher:
	return Fetching.fetch_url


def async_response_fetcher() -> AsyncWebFetcher:
	return Fetching.async_fetch_url


def async_response_processer():
	return Processing.parse_response_async


def default_response_processer() -> ResponseProcesser:
	return Processing.parse_response
