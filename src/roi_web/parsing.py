from __future__ import annotations

import math

from fitz import fitz

_a = None

import itertools
import re
import urllib.parse
from types import SimpleNamespace

import lxml.etree
import lxml.html
import trafilatura
import trafilatura.spider
from lxml import etree

from .domain import *


class EventParsing( SimpleNamespace ):
	_RE_REMOVE_UTM = re.compile( r"&?utm_(source|medium|campaign|term|content)=[^&]*&?" )
	_RE_REMOVE_TIMESTAMP = re.compile( r"&?t=\d+[^&]*&?" )
	remove_utm = lambda x: EventParsing._RE_REMOVE_UTM.sub( "", x )
	remove_timestamp = lambda x: EventParsing._RE_REMOVE_TIMESTAMP.sub( "", x )

	@staticmethod
	def _remove_params( url: UrlEvent[ URaw ] ) -> UrlEvent[ UNorm ]:
		replacers = [ EventParsing.remove_utm ]
		query = url.query

		if url.kind == UrlKinds.YOUTUBE:
			replacers.append( EventParsing.remove_timestamp )

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
			return Result.failure( Exception( "No hostname found" ) )

		return Result.ok( good ).map( EventParsing._remove_params )


class Youtube( SimpleNamespace ):
	_RE_FIND_DURATION = re.compile( r"PT(\d+)M(\d+)S" )

	@staticmethod
	def title( html: etree.HTML ) -> String | None:
		title = HTML.toAttrib( "content", html.xpath( "//meta[@itemprop='name']" ) )
		title = HTML.first( title )
		return title

	@staticmethod
	def duration( html: etree.HTML ) -> Second | None:
		from_itemprop = HTML.toAttrib( "content", html.xpath( "//meta[@itemprop='duration']" ) )
		duration = HTML.first( from_itemprop )
		match = Youtube._RE_FIND_DURATION.match( duration )
		if not match:
			return None
		minutes = int( match.group( 1 ) )
		seconds = int( match.group( 2 ) )
		return minutes * 60 + seconds

	@staticmethod
	def date( element: lxml.html.HtmlElement ) -> IsoTime:
		date = HTML.toAttrib( "content", element.xpath( "//meta[@itemprop='datePublished']" ) )
		date = HTML.first( date )
		if date:
			...
		return date

	@staticmethod
	def image( element: lxml.html.HtmlElement ) -> String | None:
		url = HTML.toAttrib( "href", element.xpath( "//link[@itemprop='thumbnailUrl']" ) )
		url = HTML.first( url )
		if url:
			...
		return url

	@staticmethod
	def tags( element: lxml.html.HtmlElement ) -> Iterable[ String ] | None:
		from_itemprop = HTML.toAttrib( "content", element.xpath( "//meta[@name='keywords']" ) )
		tags = HTML.first( from_itemprop )
		if tags:
			tags = tags.split( "," )
			tags = [ content.strip() for content in tags ]
		return tags

	@staticmethod
	def neighbors( element: lxml.html.HtmlElement ) -> Iterable[ String ]:
		# TODO  10/06/2022 parse the video description
		return [ ]

	@staticmethod
	def categories( element: lxml.html.HtmlElement ) -> Iterable[ String ]:
		genres = HTML.toAttrib( "content", element.xpath( "//meta[@itemprop='genre']" ) )
		genres = HTML.first( genres )
		if genres:
			genres = genres.split( "," )

		return genres

	@staticmethod
	def comments( element: lxml.html.HtmlElement ) -> Iterable[ String ]:
		return [ ]

	@staticmethod
	def author( element: lxml.html.HtmlElement ) -> String:
		author = HTML.toAttrib( "href", element.xpath( "//span[@itemprop='author']/link[@itemprop='url']" ) )
		author = HTML.first( author )
		return author

	@staticmethod
	def text( element: lxml.html.HtmlElement ) -> String:
		return ""

	@staticmethod
	def structure( response: WebArchive ) -> PageContent:
		element = HTML.htmlElement( response )
		duration = Youtube.duration( element )

		return PageContent( url = response.url.raw,
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


class HTML( SimpleNamespace ):

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
		return None

	@staticmethod
	def getTitle( html: etree.HTML ) -> String:

		articleTitle = HTML.toText( html.xpath( "//article/h1" ) )
		itemProp = HTML.toAttrib( "content", html.xpath( "//meta[@itemprop='name']" ) )
		ogTitle = HTML.toAttrib( "content", html.xpath( "//meta[@name='og:title']" ) )
		titleFromAnywhere = HTML.toText( html.xpath( "//title" ) )
		titleFromHead = HTML.toText( html.xpath( "//head/title" ) )
		twitterTitle = HTML.toAttrib( "content", html.xpath( "//meta[@name='twitter:title']" ) )

		return HTML.first(
				ogTitle, twitterTitle, itemProp,
				articleTitle, titleFromHead, titleFromAnywhere )

	@staticmethod
	def getDescription( html: etree.HTML ) -> String:

		anyParagraph = HTML.toText( html.xpath( "//p" ) )
		articleParagraph = HTML.toText( html.xpath( "//article//p" ) )
		itemProp = HTML.toAttrib( "content", html.xpath( "//meta[@itemprop='description']" ) )
		metaDescr = HTML.toAttrib( "content", html.xpath( "//meta[@name='description']" ) )
		ogDescr = HTML.toAttrib( "content", html.xpath( "//meta[@name='og:description']" ) )
		twitterDescr = HTML.toAttrib( "content", html.xpath( "//meta[@name='twitter:description']" ) )

		return HTML.first( ogDescr, twitterDescr, itemProp, metaDescr,
		                   articleParagraph, anyParagraph )

	@staticmethod
	def getAudio( html: etree.HTML ) -> Iterable[ etree.HTML ]:
		...

	@staticmethod
	def getImage( html: etree.HTML ) -> String:

		anyImage = HTML.toAttrib( "src", html.xpath( "//img" ) )
		headIcon = HTML.toAttrib( "href", html.xpath( "//head/link[@rel='icon']" ) )
		itemProp = HTML.toAttrib( "content", html.xpath( "//meta[@itemprop='image']" ) )
		ogImage = HTML.toAttrib( "content", html.xpath( "//meta[@property='og:image']" ) )
		twitterImage = HTML.toAttrib( "content", html.xpath( "//meta[@name='twitter:image']" ) )

		return HTML.first( ogImage, twitterImage, itemProp, headIcon, anyImage )

	@staticmethod
	def structure( response: WebArchive ) -> PageContent:
		html_element = HTML.htmlElement( response.content )
		result = trafilatura.bare_extraction( filecontent = html_element,
		                                      include_formatting = True,
		                                      include_links = True,

		                                      include_comments = False,
		                                      include_images = False,
		                                      include_tables = False
		                                      )

		text = result.get( "text", None )
		title = result.get( "title", None )
		author = result.get( "author", None )
		date = result.get( "date", None )
		categories = [ i for i in result.get( "categories", [ ] ) ]
		tags = [ i for i in result.get( "tags", [ ] ) ]
		image = HTML.getImage( html_element )

		# TODO  24/06/2022 neighbors
		neighbors = re.findall( "(?<=]\()(.+?)(?=\))", text )

		return PageContent( url = response.url.raw,
		                    text = text,
		                    title = title,
		                    author = author,
		                    date = date,
		                    categories = categories,
		                    tags = tags,
		                    image = image if len( image or "" ) <= 1000 else None,
		                    comments = [ ],
		                    neighbors = neighbors,
		                    duration = math.ceil( len( text ) / 5 / 250 ) * 60
		                    )

	@staticmethod
	def htmlElement( response: WebArchive | NetworkArchive | String ) -> lxml.html.HtmlElement:
		if isinstance( response, WebArchive ):
			charset = response.content.response_charset or "utf-8"
			content = response.content.response_content.decode( charset )
		elif isinstance( response, NetworkArchive ):
			charset = response.response_charset or "utf-8"
			content = response.response_content.decode( charset )
		elif isinstance( response, String ):
			content = response
		else:
			content = ""

		return lxml.html.fromstring( content )

	@staticmethod
	def xmlElement( response: WebArchive | NetworkArchive | String ) -> lxml.etree.Element:
		if isinstance( response, WebArchive ):
			charset = response.content.response_charset or "utf-8"
			content = response.content.response_content.decode( charset )
		elif isinstance( response, NetworkArchive ):
			charset = response.response_charset or "utf-8"
			content = response.response_content.decode( charset )
		elif isinstance( response, String ):
			content = response

		else:
			content = ""

		return lxml.etree.fromstring( content )

	@staticmethod
	def youtubeTranscript( response: NetworkArchive ) -> String:

		return " ".join( i.text for i in lxml.etree.XML( response.response_content ) )


class PDF( SimpleNamespace ):

	@classmethod
	def text( cls, doc: fitz.Document ) -> String:
		page = itertools.chain.from_iterable(
				map( lambda page: page.get_text( "blocks" ),
				     doc.pages() )
		)

		return "\n\n".join( map( lambda x: x[ 4 ], page ) )

	@classmethod
	def structure( cls, archive: WebArchive ) -> PageContent:
		doc = fitz.Document( stream = archive.content.response_content )

		text = PDF.text( doc )
		author = doc.metadata.get( "author", None )
		title = doc.metadata.get( "title", None )
		keywords = [ i for i in doc.metadata.get( "keywords", [ ] ) ]
		subject = doc.metadata.get( "subject" )
		modDate = doc.metadata.get( "modDate" )

		return PageContent(
				url = archive.url.raw,
				text = text,
				title = title,
				duration = math.ceil( len( text ) / 5 / 250 ) * 60,
				author = author,
				date = modDate,
				tags = keywords,
				categories = [ subject ]
		)
