from __future__ import annotations

import enum
import hashlib
from dataclasses import dataclass, replace
from typing import NewType, TypeAlias, Iterable, Generic, TypeVar, Mapping, List, Protocol, Literal

from src.utils.monad import Result

String: TypeAlias = str
TabSeparated: TypeAlias = str
Binary: TypeAlias = bytes
MimeType: NewType( "MimeType", str )
TextEncoding: NewType( "TextEncoding", str )
WebHeader: NewType( "WebHeader", Mapping[ String, String | List[ String ] ] )
IsoTime = NewType( "IsoTime", str )

#
UrlStatus = NewType( "UrlStatus", object )
URaw = NewType( "URaw", UrlStatus )
UClean = NewType( "UClean", UrlStatus )
S = TypeVar( "S", bound = UrlStatus )


class UrlKinds( enum.Enum ):
	YOUTUBE = "youtube"
	ARXIV = "arxiv"
	GITHUBIO = "github.io"
	DATASKEPTIC = "dataskeptic"
	OTHER = "dataskeptic"


@dataclass( frozen = True )
class Url( Generic[ S ] ):
	raw: String
	quality: String
	scheme: String | None
	netloc: String | None
	path: String | None
	query: String | None
	hostname: String | None

	def update( self, kwargs ) -> Url[ S ]:
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


# noinspection PyUnresolvedReferences
@dataclass
class ResponseInfo:
	url: Url[ ... ]
	headers: WebHeader
	content: String | Binary

	mime: MimeType | None
	encoding: TextEncoding | None

	def text_content( self ):
		...


#

ContentStatus = NewType( "ContentStatus", object )
CRaw = NewType( "CRaw", ContentStatus )
CRich = NewType( "CRich", ContentStatus )
C = TypeVar( "C", bound = ContentStatus )


@dataclass
class PageInfo( Generic[ C ] ):
	url: Url
	text: String

	title: String | None
	author: String | None
	date: IsoTime | None

	categories: Iterable[ String ] | None
	tags: Iterable[ String ] | None
	comments: Iterable[ String ] | None
	preview: String | None

	neighbors: Iterable[ Url[ URaw ] ]

	def with_text( self, text: String ) -> PageInfo:
		replace( self, text = text )

#

class PageException( Exception ):
	def __init__( self, url, status, message ):
		self.url = url
		self.status = status
		self.message = message


class UrlParser( Protocol[ S ] ):
	def __call__( self, string: TabSeparated ) -> Result[ Url[ S ] ]:
		...


class WebFetcher( Protocol ):
	def __call__( self, url: Url[ ... ], headers: Mapping[ String, String ] ) -> Result[ ResponseInfo ]:
		...


class PageParser( Protocol ):
	def __call__( self, info: ResponseInfo ) -> Result[ PageInfo ]:
		...
