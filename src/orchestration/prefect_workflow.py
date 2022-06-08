from __future__ import annotations

import time
from typing import Iterable

from prefect import task, Flow

from src.processing.web.domain import ResponseInfo, UNorm, UrlEvent, RichResponse
from src.processing.web.persistence import load_response
from src.processing.web.processing import baseLoadStream, basePersistResponse, baseProcessResponse, basePersistProcessed, baseFetchResponse
from src.utils.monad import Result


@task
def prefect_load_stream() -> Iterable[ UrlEvent[ UNorm ] ]:
	return [ i for i in baseLoadStream() ]


@task
def prefect_fetch_response( url: Result[ UrlEvent[ ... ] ] ) -> Result[ ResponseInfo ]:
	return url.flatMap( baseFetchResponse )


@task
def prefect_persist_response( info: Result[ ResponseInfo ] ) -> None:
	basePersistResponse( info )


@task
def prefect_process_response( content: Result[ ResponseInfo ] ) -> Result[ RichResponse ]:
	return content.flatMap( baseProcessResponse )


@task
def prefect_persist_processed( content: Result[ RichResponse ] ) -> None:
	basePersistProcessed( content )


with Flow( "Hello-Flow" ) as flow:
	data = prefect_load_stream()

	responses = prefect_fetch_response.map( data )
	prefect_persist_response.map( responses )

	processed = prefect_process_response.map( responses )
	prefect_persist_processed.map( processed )


# flow.executor = LocalDaskExecutor( scheduler = "threads", num_workers = 5 )
flow.run()
finish = time.time()
