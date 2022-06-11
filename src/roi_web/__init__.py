import random
from typing import Iterable

from roi_utils import Result
from .domain import ResponseInfo, TabSeparated, UrlEvent, UNorm, PageContent
from .logic import default_response_fetcher, default_url_parser, default_response_processer, Youtube, Htmls
from .persistence import load_response, save_response, save_errors, save_enrichment, load_stream


def baseLoadStream() -> Iterable[ UrlEvent ]:
	for line in load_stream():
		dice = random.randint( 1, 100_000 )
		if dice <= 1000:
			yield baseParseUrl( line )


def baseParseUrl( line: TabSeparated ) -> Result[ UrlEvent[ UNorm ] ]:
	parser = default_url_parser()
	return parser( line )


def baseFetchResponse( url: UrlEvent ) -> Result[ ResponseInfo ]:
	print( url )
	cached = load_response( url )
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
	content.map( save_enrichment ).orElse( save_errors )


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
		Htmls
)
