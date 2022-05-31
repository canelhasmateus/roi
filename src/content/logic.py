from domain import *


def _clean_url( url: Url[ URaw ] ) -> Url[ UClean ]:
	...


def _fetch_info( url: Url[ UClean ] ) -> Result[ PageInfo ]:
	...



def _parse_content( info: PageInfo ) -> PageContent[ CRaw ]:
	...


def _enrich_content( content: PageContent[ CRaw ] ) -> PageContent[ CRich ]:
	...

#
def to_url( url: String ) -> Result[ Url[ URaw ] ]:
	...

def to_info( value: String ) -> Result[ PageInfo ]:
	return (
		to_url( value )
			.map( _clean_url )
			.flatMap( _fetch_info ))

def to_content( value: String ) -> Result[ PageContent[ CRich ] ]:
	return (
		to_info( value )
			.map( _parse_content )
			.map( _enrich_content ))
