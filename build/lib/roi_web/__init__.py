import random
from typing import Iterable

from roi_utils import Result
from .domain import ResponseInfo, TabSeparated, UrlEvent, UNorm, PageContent, Digestable
from .persistence import load_response, save_response, save_errors, save_processed, load_stream
from .process import default_url_parser, default_response_fetcher, default_response_processer, Youtube, Htmls


def baseLoadStream() -> Iterable[ UrlEvent ]:
	for line in load_stream():
		yield baseParseUrl( line )


def baseParseUrl( line: TabSeparated ) -> Result[ UrlEvent[ UNorm ] ]:
	parser = default_url_parser()
	return parser( line )


def baseFetchResponse( url: UrlEvent ) -> Result[ ResponseInfo ]:
	cached = load_response( url.digest() )
	if cached.successful():
		print( "Cached Response" )
		return cached

	print( "Fetching Response" )
	fetcher = default_response_fetcher()
	return fetcher( url )


def basePersistResponse( info: Result[ ResponseInfo ] ) -> None:
	info.map( save_response ).orElse( save_errors )


def baseProcessResponse( content: ResponseInfo ) -> Result[ PageContent ]:
	print( "Processing content!" )
	parser = default_response_processer()
	return parser( content )


def basePersistProcessed( content: Result[ PageContent ] ) -> None:
	content.map( save_processed ).orElse( save_errors )


__all__ = (
		baseLoadStream,
		baseParseUrl,
		baseFetchResponse,
		basePersistResponse,
		baseProcessResponse,
		basePersistProcessed,
		ResponseInfo,
		UrlEvent,
		PageContent,
		TabSeparated,
		Youtube,
		Htmls,
		Digestable
)
