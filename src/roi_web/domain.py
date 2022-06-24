from __future__ import annotations

import enum
import hashlib
from dataclasses import dataclass, replace, field
from typing import NewType, TypeAlias, Iterable, Generic, TypeVar, Mapping, List, Protocol

from requests import Response
from warcio.recordloader import ArcWarcRecord

from roi_utils import Result

String: TypeAlias = str
Second: TypeAlias = int
TabSeparated: TypeAlias = str
Binary: TypeAlias = bytes

MimeType = NewType( "MimeType", str )
TextEncoding = NewType( "TextEncoding", str )
WebHeader = NewType( "WebHeader", Mapping[ String, String | List[ String ] ] )
IsoTime = NewType( "IsoTime", str )

#
UrlStatus = NewType( "UrlStatus", object )
URaw = NewType( "URaw", UrlStatus )
UNorm = NewType( "UNorm", UrlStatus )
S = TypeVar( "S", bound = UrlStatus )


class UrlKinds( enum.Enum ):
	YOUTUBE = "youtube"
	ARXIV = "arxiv"
	GITHUBIO = "github.io"
	DATASKEPTIC = "dataskeptic"
	OTHER = "other"


@dataclass( frozen = True )
class UrlEvent( Generic[ S ] ):
	raw: String
	quality: String
	scheme: String | None
	netloc: String | None
	path: String | None
	query: String | None
	hostname: String | None

	def update( self, kwargs ) -> UrlEvent[ S ]:
		return replace( self, **kwargs )

	@property
	def kind( self ) -> UrlKinds:
		if "youtube.com" in self.hostname:
			return UrlKinds.YOUTUBE
		if "arxiv.com" in self.hostname:
			return UrlKinds.ARXIV
		if "github.io" in self.hostname:
			return UrlKinds.GITHUBIO
		if "dataskeptic.com" in self.hostname:
			return UrlKinds.DATASKEPTIC
		return UrlKinds.OTHER

	def digest( self ) -> String:
		return hashlib.md5( self.raw.encode() ).digest().hex()


#
#
#

@dataclass()
class PageContent:
	url: UrlEvent
	text: String
	title: String | None = None
	duration: Second | None = None
	author: String | None = None
	date: IsoTime | None = None
	image: String | None = None
	tags: Iterable[ String ] | None = None
	neighbors: Iterable[ String ] = field( default_factory = list )
	categories: Iterable[ String ] | None = field( default_factory = list )
	comments: Iterable[ String ] | None = field( default_factory = list )

	def update( self, **kwargs ) -> PageContent:
		return replace( self, **kwargs )

	def digest( self ) -> String:
		return hashlib.md5( self.url.raw.encode() ).digest().hex()


@dataclass
class NetworkArchive:
	host: String
	request_headers: Mapping
	request_method: String
	request_real_url: String
	request_url: String
	response_charset: String
	response_content: bytes
	response_content_type: String
	response_headers: Mapping
	response_real_url: String
	response_status : int
	response_url: String

@dataclass
class WebArchive:
	url: UrlEvent[ ... ]
	content: NetworkArchive

	def digest( self ) -> String:
		return hashlib.md5( self.url.raw.encode() ).digest().hex()

	def update( self, **kwargs ) -> WebArchive:
		return replace( self, **kwargs )

	@classmethod
	def from_dict( cls, res ) -> WebArchive:
		return  WebArchive( **res )



#

class PageException( Exception ):
	def __init__( self, url, status, message ):
		self.url = url
		self.status = status
		self.message = message


class EventParser( Protocol[ S ] ):
	def __call__( self, string: TabSeparated ) -> Result[ UrlEvent[ S ] ]:
		...


class WebFetcher( Protocol ):
	def __call__( self, url: UrlEvent[ ... ], headers: Mapping[ String, String ] ) -> WebArchive:
		...


class ResponseProcesser( Protocol ):
	def __call__( self, response: WebArchive ) -> Result[ PageContent ]:
		...


class Digestable( Protocol ):
	def digest( self ) -> String:
		...
