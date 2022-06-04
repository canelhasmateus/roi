from __future__ import annotations

from dataclasses import dataclass , replace
from typing import NewType, TypeAlias, Iterable, Generic, TypeVar, overload

String: TypeAlias = str
Binary: TypeAlias = bytes
IsoTime = NewType( "IsoTime", str )

#
UrlStatus = NewType( "UrlStatus", object )
URaw = NewType( "URaw", UrlStatus )
UClean = NewType( "UClean", UrlStatus )
S = TypeVar( "S", bound=UrlStatus )


@dataclass
class Url( Generic[ S ] ):
	raw: String
	scheme: String | None
	netloc: String | None
	path: String | None
	query: String | None
	hostname: String | None

	def update(self , kwargs ) -> Url[ S ]:
		return replace( self , **kwargs )

@dataclass
class PageInfo:
	url: Url[ UClean ]
	source: String | Binary

#

ContentStatus = NewType( "ContentStatus", object )
CRaw = NewType( "CRaw", ContentStatus )
CRich = NewType( "CRich", ContentStatus )
C = TypeVar( "C", bound=ContentStatus )


@dataclass
class PageContent( Generic[ C ] ):
	...
	text: String

	title: String | None
	author: String | None
	date: IsoTime | None

	categories: Iterable[ String ] | None
	tags: Iterable[ String ] | None
	comments: Iterable[ String ] | None
	neighbors: Iterable[ Url[ URaw ] ]
