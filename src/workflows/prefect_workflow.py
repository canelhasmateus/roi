from __future__ import annotations

from typing import Iterable

from prefect import task, Flow
from prefect.executors import LocalDaskExecutor

from roi_utils import Result
from roi_web import UrlEvent, UNorm, baseLoadStream, ResponseInfo, baseFetchResponse, basePersistResponse, baseProcessResponse, basePersistProcessed, PageContent


@task
def prefect_load_stream() -> Iterable[ UrlEvent[ UNorm ] ]:
	return [ i for i in baseLoadStream() ]


@task
def prefect_fetch_response( url: Result[ UrlEvent[ ... ] ] ) -> Result[ ResponseInfo ]:
	res = url.flatMap( baseFetchResponse )
	res.expect()
	return res


@task
def prefect_persist_response( info: Result[ ResponseInfo ] ) -> None:
	basePersistResponse( info )


@task
def prefect_process_response( content: Result[ ResponseInfo ] ) -> Result[ PageContent ]:
	return content.flatMap( baseProcessResponse )


@task
def prefect_persist_processed( content: Result[ PageContent ] ) -> None:
	basePersistProcessed( content )


with Flow( "Article Extraction" ) as flow:
	data = prefect_load_stream()

	responses = prefect_fetch_response.map( data )
	prefect_persist_response.map( responses )

	processed = prefect_process_response.map( responses )
	prefect_persist_processed.map( processed )

flow.executor = LocalDaskExecutor( num_workers = 30 )
flow.register( "Gnosis" )
