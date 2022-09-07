from __future__ import annotations

from typing import Iterable

from prefect import task, Flow
from prefect.executors import LocalDaskExecutor

from roi_utils import Result
from roi_web import UrlEvent, UNorm, load_events, WebArchive, fetchResponseBase, persistResponseBase, processResponseBase, persistProcessedBase, PageContent


@task
def prefect_load_stream() -> Iterable[ UrlEvent[ UNorm ] ]:
    return [ i for i in load_events() ]


@task
def prefect_fetch_response( url: Result[ UrlEvent[ ... ] ] ) -> Result[ WebArchive ]:
    return url.map( fetchResponseBase )


@task
def prefect_persist_response( info: Result[ WebArchive ] ) -> None:
    info.map( persistResponseBase )


@task
def prefect_process_response( content: Result[ WebArchive ] ) -> Result[ PageContent ]:
    return content.flatMap( processResponseBase )


@task
def prefect_persist_processed( content: Result[ PageContent ] ) -> None:
    persistProcessedBase( content )


with Flow( "Article Extraction" ) as flow:
    data = prefect_load_stream()

    responses = prefect_fetch_response.map( data )
    prefect_persist_response.map( responses )

# processed = prefect_process_response.map( responses )
# prefect_persist_processed.map( processed )

flow.executor = LocalDaskExecutor( num_workers=30 )
# flow.register( "Gnosis" )
flow.run()
