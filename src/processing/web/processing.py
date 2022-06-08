import random
from typing import Iterable

from requests import Response

from src.processing.web.domain import ResponseInfo, TabSeparated, UrlEvent, UNorm, RichResponse
from src.processing.web.logic import default_response_fetcher, default_url_parser, default_response_processer
from src.processing.web.persistence import load_response, save_response, save_errors, save_content, load_stream
from src.utils.monad import Result


def baseLoadStream() -> Iterable[ UrlEvent ]:
	for line in load_stream():
		dice = random.randint( 1, 100_000 )
		if dice <= 1000:
			yield baseParseUrl( line )


def baseParseUrl( line: TabSeparated ) -> Result[ UrlEvent[ UNorm ] ]:
	parser = default_url_parser()
	return parser( line )


def baseFetchResponse( url: UrlEvent ) -> Result[ ResponseInfo ]:
	cached = load_response( url )
	if cached.successful():
		print( "Cached Response" )
		return cached

	if True:
		return Result.failure( Exception( "No cached response found." ) )

	print( "Fetching Response" )
	fetcher = default_response_fetcher()
	return fetcher( url )


def basePersistResponse( info: Result[ ResponseInfo ] ) -> None:
	if False:
		info.map( save_response ).orElse( save_errors )


def baseProcessResponse( content: Response ) -> Result[ RichResponse ]:
	print( "Processing content!" )
	parser = default_response_processer()
	return parser( content )


def basePersistProcessed( content: Result[ RichResponse ] ) -> None:
	if False:
		content.map( save_content ).orElse( save_errors )
