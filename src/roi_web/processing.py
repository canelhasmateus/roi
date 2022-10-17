import asyncio
import os
import pathlib
import re
from typing import Iterable, ClassVar

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from roi_utils import save_async, ExecutionContext
from roi_web import WebArchive, UrlEvent, PageContent, NetworkArchive, UrlKinds, String, EventParsing, HTML, PDF, Youtube

WEB_STREAM_FILEPATH = os.environ.get( "GNOSIS_WEB_STREAM", "C:/Users/Mateus/OneDrive/gnosis/limni/lists/stream/articles.tsv" )
DEFAULT_STREAM_PATH = pathlib.Path( WEB_STREAM_FILEPATH )


def load_events( filepath: pathlib.Path = None, seen=None ) -> Iterable[ UrlEvent ]:
    filepath = filepath or DEFAULT_STREAM_PATH
    seen = seen or set()

    with open( str( filepath ), "r" ) as file:
        for i, content in enumerate( file.readlines() ):
            if i > 0:
                url = EventParsing.parse_url( content )
                if url.successful():
                    event = url.expect()
                    if event.raw not in seen:
                        yield event


def remove_file( content: PageContent ):
    file = pathlib.Path( Processer.DEFAULT_PATH ) / content.digest()
    file.unlink()


def load_processed() -> Iterable[ PageContent ]:
    for f in Processer.DEFAULT_PATH.glob( "*" ):
        try:
            with open( f, "rb" ) as file:
                payload = file.read()
                content =  PageContent.from_json( payload )
        except Exception as e:
            print( e )
            continue

        yield content


class Fetcher:
    _USER_AGENT: ClassVar = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'

    def __init__( self, session: ClientSession = None ):
        if not session:
            tcp_connector = aiohttp.TCPConnector( verify_ssl=False, limit_per_host=2, limit=10 )
            timeout = ClientTimeout( total=300 )
            session = aiohttp.ClientSession( connector=tcp_connector, timeout=timeout )

        self.session = session

    async def fetch( self, url: String, headers=None, params=None ) -> NetworkArchive:
        headers = headers or {"User-Agent": self._USER_AGENT}
        params = params or {}

        async with self.session.get( url, headers=headers, params=params ) as resp:
            response = NetworkArchive( response_status=resp.status,
                                       response_charset=resp.charset,
                                       response_content=await resp.read(),
                                       response_content_type=resp.content_type,
                                       response_headers={k: v for k, v in resp.headers.items()},
                                       response_url=str( resp.url ),
                                       response_real_url=str( resp.real_url ),
                                       host=resp.host,
                                       request_headers={k: v for k, v in resp.request_info.headers.items()},
                                       request_method=resp.request_info.method,
                                       request_url=str( resp.request_info.url ),
                                       request_real_url=str( resp.request_info.real_url ),
                                       )
            return response

    async def __aexit__( self, exc_type, exc_val, exc_tb ):
        await self.session.__aexit__( exc_type, exc_val, exc_tb )


class Processer:
    basepath: ClassVar = os.environ.get( "ROI_BASEDIR" )

    DEFAULT_PATH: ClassVar = pathlib.Path( basepath ) / "processed"

    youtube_pattern: ClassVar = re.compile( r"(?<=v=)(\w+?)(?=\b|&)" )

    def __init__( self, fetcher: Fetcher, connection="" ):

        self.semaphore = asyncio.Semaphore( 1000 )
        self.fetcher = fetcher
        # self.connection = sqlite3.connect( connection )

    async def __aenter__( self ):
        return self

    async def __aexit__( self, exc_type, exc_val, exc_tb ):
        await self.fetcher.__aexit__( exc_type, exc_val, exc_tb )

    async def process( self, url: UrlEvent ) -> None:

        with ExecutionContext( "Processing url", exc_suppress=True,
                               extra={"digest": url.digest(), "kind": url.kind.value} ):

            raw_archive = await self.fetch( url )
            rich_content = await self.enrich( raw_archive )
            if not rich_content.text:
                raise Exception("No text")

            await self.persist( rich_content )


    # region raw
    async def fetch( self, url: UrlEvent ) -> WebArchive:

        with ExecutionContext( "Fetching Raw",
                               extra={"digest": url.digest(), "kind": url.kind.value} ):

            response = await self.fetcher.fetch( url.raw )

            if 200 <= response.response_status <= 299:
                return WebArchive( url=url, content=response )
            else:
                raise Exception( "Unsucessful response" )

    # endregion

    # region rich
    async def enrich( self, archive: WebArchive ) -> PageContent:

        url = archive.url
        content = archive.content.response_content

        with ExecutionContext( "Processing", exc_level="error", exc_suppress=False,
                               extra={"digest": archive.digest(), "kind": archive.kind.value} ):

            match archive.content.response_content_type, archive.kind:

                case "text/html", UrlKinds.YOUTUBE:
                    content = Youtube.structure( url, content.decode() )
                    return await self.add_transcript( content )

                case "text/html", _:

                    try:
                        return HTML.structure( url, content )
                    except Exception as e:
                        print( e )

                case "application/pdf", _:
                    return PDF.structure( url, content )

                case mime:

                    raise Exception( "Unsupported Mime Type and kind " + mime )

    # endregion

    async def persist( self, processed: PageContent ):
        with ExecutionContext( "Persist Processed", exc_suppress=True,
                               extra={"digest": processed.digest(), "kind": "Unknown"} ):
            await save_async( processed, path=self.DEFAULT_PATH / processed.digest() )

    async def add_transcript( self, item: PageContent ):
        video_id = self.youtube_pattern.search( item.url )
        if video_id:
            content = await self.fetcher.fetch( "https://youtubetranscript.com", params={"server_vid": video_id.group( 0 )} )
            status = content.response_status
            if 200 <= status <= 299:
                transcript = Youtube.transcript( content )
                return item.update( text=transcript )

        return item

    def remaining_events( self ):
        return
