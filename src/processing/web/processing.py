from typing import Iterable

from src.processing.web.domain import ResponseInfo, TabSeparated, Url, UClean, PageInfo
from src.processing.web.logic import default_fetcher, default_url_parser, default_content_parser
from src.processing.web.persistence import load_response, save_response, save_errors, save_content, load_stream
from src.utils.monad import Result


def loadStream() -> Iterable[ Url ]:
	parse = default_url_parser()
	for line in load_stream():
		yield parse( line )


def parseUrl( line: TabSeparated ) -> Result[ Url[ UClean ] ]:
	parser = default_url_parser()
	return parser( line )


def fetchResponse( url: Url ) -> Result[ ResponseInfo ]:
	cached = load_response( url )
	if cached.is_success():
		print( "Cached Response" )
		return cached

	print( "Fetching Response" )
	fetcher = default_fetcher()
	return fetcher( url )


def persistRaw( info: Result[ ResponseInfo ] ) -> None:
	(info
	 .map( save_response )
	 .recover( save_errors )
	 )


def parseResponse( content: ResponseInfo ) -> Result[ PageInfo ]:
	print( "Processing content!" )
	parser = default_content_parser()
	return parser( content )


def persistProcessed( content: Result[ PageInfo ] ) -> None:
	(content
	 .map( save_content )
	 .recover( save_errors ))
