from __future__ import annotations

import time
from typing import Iterable

from prefect import task, Flow

from src.processing.web.domain import ResponseInfo, UClean, Url, PageInfo
from src.processing.web.persistence import save_content, load_response
from src.processing.web.processing import loadStream, persistRaw, parseResponse, persistProcessed
from src.utils.monad import Result


@task
def prefect_load_stream() -> Iterable[ Url[ UClean ] ]:
	return [ i for i in loadStream()]


@task
def prefect_fetch_response( url: Result[ Url[ ... ] ] ) -> Result[ ResponseInfo ]:
	return url.flatMap( load_response )


@task
def prefect_persist_response( info: Result[ ResponseInfo ] ) -> None:
	persistRaw( info )


@task
def prefect_parse_response( content: Result[ ResponseInfo ] ) -> Result[ PageInfo ]:
	return content.flatMap( parseResponse )


@task
def prefect_persist_processed( content: Result[ PageInfo ] ) -> None:
	persistProcessed( content )


with Flow( "Hello-Flow" ) as flow:
	data = prefect_load_stream()

	responses = prefect_fetch_response.map( data )
	prefect_persist_response.map( responses )

	processed = prefect_parse_response.map( responses )
	prefect_persist_processed.map( processed )

finish_planning = time.time()
# flow.executor = LocalDaskExecutor( scheduler = "threads", num_workers = 5 )
flow.run()
finish = time.time()
