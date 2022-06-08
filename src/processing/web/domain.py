from __future__ import annotations

import enum
import hashlib
from dataclasses import dataclass, replace
from typing import NewType, TypeAlias, Iterable, Generic, TypeVar, Mapping, List, Protocol

from requests import Response

from src.utils.monad import Result

String: TypeAlias = str
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
class ResponseEnrichment:
	text: String
	title: String | None
	author: String | None
	date: IsoTime | None
	categories: Iterable[ String ] | None
	tags: Iterable[ String ] | None
	comments: Iterable[ String ] | None
	preview: String | None
	neighbors: Iterable[ UrlEvent[ URaw ] ]

	def update( self, **kwargs ) -> ResponseEnrichment:
		return replace( self, **kwargs )




@dataclass
class ResponseInfo:
	url: UrlEvent[ ... ]
	content: Response
	structure: ResponseEnrichment | None

	def digest( self ) -> String:
		return hashlib.md5( self.url.raw.encode() ).digest().hex()


	def update( self, **kwargs ) -> ResponseInfo:
		return replace( self, **kwargs )


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
	def __call__( self, url: UrlEvent[ ... ], headers: Mapping[ String, String ] ) -> Result[ ResponseInfo ]:
		...


class Digestable( Protocol ):
	def digest( self ) -> String:
		...
