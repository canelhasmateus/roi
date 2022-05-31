from __future__ import annotations

from dataclasses import dataclass
from typing import NewType, TypeAlias, Iterable, Generic, TypeVar, Protocol, Callable

K = TypeVar( "K" )
V = TypeVar( "V" )
T = TypeVar( "T", covariant=True )

String: TypeAlias = str
IsoTime = NewType( "IsoTime", str )

#
UrlStatus = NewType( "UrlStatus", object )
URaw = NewType( "URaw", UrlStatus )
UClean = NewType( "UClean", UrlStatus )
S = TypeVar( "S", bound=UrlStatus )


class Result( Protocol[ K ] ):

	def map( self, fn: Callable[ [ K ], V ] ) -> Result[ V ]:
		...

	def flatMap( self, fn: Callable[ [ K ], Result[ V ] ] ) -> Result[ V ]:
		...


#

@dataclass
class Url( Generic[ S ] ):
	raw: String




@dataclass
class PageInfo:
	url: Url[ UClean ]



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

