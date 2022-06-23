import asyncio
import pathlib
import pickle
import random
from typing import Iterable, AsyncIterable

import aiofiles
from aiohttp import ClientSession

from roi_utils import Result
from .domain import WebArchive, TabSeparated, UrlEvent, UNorm, PageContent, Digestable
from .persistence import load_archive, save_response, save_errors, save_processed, load_stream, load_archive_async, save_response_async
from .process import default_url_parser, default_response_fetcher, default_response_processer, Youtube, Htmls, async_response_fetcher


def baseLoadStream() -> Iterable[ UrlEvent ]:
	for line in load_stream():
		yield baseParseUrl( line )


def baseParseUrl( line: TabSeparated ) -> Result[ UrlEvent[ UNorm ] ]:
	parser = default_url_parser()
	return parser( line )


def fetchResponseBase( url: UrlEvent ) -> WebArchive:
	print( f"Looking for url: {url.raw}" )
	cached = load_archive( url.digest() )
	if cached.successful():
		print( "Cached Response" )
		return cached.expect()

	print( "Fetching Response" )
	fetcher = default_response_fetcher()
	return fetcher( url )


async def fetchResponseAsync( session: ClientSession, url: UrlEvent ) -> WebArchive:
	print( f"{url.digest()}: Looking for cache for url: {url.raw}" )

	cached = load_archive_async( url )
	try:
		res = cached.expect()
		print( f"{url.digest()}: Found Cached Response" )
		return res
	except Exception as e:
		print( f"{url.digest()}: No cache found - fetching Response after {str( e )}" )
		fetcher = async_response_fetcher()
		return await fetcher( session, url )


def persistResponseBase( info: WebArchive ) -> None:
	save_response( info )


def persistResponseAsync( archive: WebArchive ) -> None:
	save_response_async( archive )


def baseProcessResponse( content: WebArchive ) -> Result[ PageContent ]:
	print( "Processing content!" )
	parser = default_response_processer()
	return parser( content )


def basePersistProcessed( content: Result[ PageContent ] ) -> None:
	content.map( save_processed ).orElse( save_errors )


__all__ = (
		baseLoadStream,
		baseParseUrl,
		fetchResponseBase,
		persistResponseBase,
		baseProcessResponse,
		basePersistProcessed,
		WebArchive,
		UrlEvent,
		PageContent,
		TabSeparated,
		Youtube,
		Htmls,
		Digestable
)
