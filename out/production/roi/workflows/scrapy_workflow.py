import pathlib
import re
from typing import Iterable

import aiohttp
import scrapy
from aiohttp import ClientTimeout
from scrapy.crawler import CrawlerProcess
from scrapy.http import Response

from roi_utils.persistence import save_sync
from roi_web import UrlEvent, HTML, Youtube, PageContent, PDF
from roi_web.processing import load_events, Fetcher


def load_good_events( filepath: pathlib.Path = None ) -> Iterable[ UrlEvent ]:
    for url in load_events( filepath ):
        if url.successful():
            yield url.expect().raw


tcp_connector = aiohttp.TCPConnector( verify_ssl=False, limit_per_host=2, limit=50 )
timeout = ClientTimeout( total=300 )
session = aiohttp.ClientSession( connector=tcp_connector, timeout=timeout )
fetcher = Fetcher( session )
basepath = "C:/Users/Mateus/Desktop/files"
DEFAULT_RAW_PATH = pathlib.Path( basepath ) / "raw"
DEFAULT_PATH = pathlib.Path( basepath ) / "processed"
DEFAULT_RICH_PATH = pathlib.Path( basepath ) / "enriched"
youtube_pattern = re.compile( r"(?<=v=)(\w+?)(?=\b|&)" )


class YoutubePipeline:
    async def process_item( self, item: PageContent, spider ):
        videoId = youtube_pattern.search( item.url )
        if not videoId:
            return item

        content = await fetcher.fetch( "https://youtubetranscript.com", params={"server_vid": videoId.group( 0 )} )
        status = content.response_status
        if 200 <= status <= 299:
            transcript = HTML.youtubeTranscript( content )
            return item.update( text=transcript )


class PersistencePipeline:
    async def process_item( self, item: PageContent, spider ):
        digest = item.digest()
        path = pathlib.Path( DEFAULT_RICH_PATH ) / digest
        save_sync( item, path )


class ArticlesSpider( scrapy.Spider ):
    name = 'articles'
    start_urls = load_good_events()
    custom_settings = {
        'ITEM_PIPELINES': {
            YoutubePipeline: 400,
            PersistencePipeline: 500
        }
    }

    def parse( self, response: Response, **kwargs ):
        mime, *_ = response.headers[ "content-type" ].decode().split( ";" )

        match mime:
            case "text/html":
                if "youtube" in response.url:
                    yield Youtube.structure( response.url, response.text )
                else:
                    yield HTML.structure( response.url, response.text )

            case "application/pdf":
                yield PDF.structure( response.url, response.body )
            case 'application/xhtml+xml':
                yield HTML.structure( response.url, response.text )
            case _:
                print( response )


# with ExecutionContext( "Youtube Transcript",
#                        extra={"kind": archive.kind.value, "digest": archive.digest()} ):
# 	content = await self.fetcher.fetch( "https://youtubetranscript.com",
# 	                                    params={"server_vid": videoId.group( 0 )} )

#
# 	status = content.response_status
# 	if 200 <= status <= 299:
# 		return ResponseEnrichment( url=archive.url,
# 		                           transcriptions=[ HTML.youtubeTranscript( content ) ] )
# 	else:
# 		raise Exception( "Bad response status " + str( status ) )


process = CrawlerProcess()

process.crawl( ArticlesSpider )
process.start()
