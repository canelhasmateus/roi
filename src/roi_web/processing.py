import asyncio
import os
import pathlib
from typing import Iterable, ClassVar

from aiohttp import ClientSession

from roi_utils import Result, save_async, load_async
from .domain import WebArchive, UrlEvent, PageContent, NetworkArchive, ResponseEnrichment, UrlKinds
from .parsing import EventParsing, Htmls

WEB_STREAM_FILEPATH = os.environ.get( "GNOSIS_WEB_STREAM", "C:/Users/Mateus/OneDrive/gnosis/limni/lists/stream/articles.tsv" )
DEFAULT_STREAM_PATH = pathlib.Path( WEB_STREAM_FILEPATH )


def loadEvents( filepath: pathlib.Path = None ) -> Iterable[ Result[ UrlEvent ] ]:
	filepath = filepath or DEFAULT_STREAM_PATH
	with open( str( filepath ), "r" ) as file:
		for i, content in enumerate( file.readlines() ):
			if i > 0:
				yield EventParsing.parse_url( content )


class Fetcher:
	_USER_AGENT: ClassVar = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'

	def __init__( self, session: ClientSession = None ):
		self.session = session or ClientSession()

	async def fetch( self, url: UrlEvent, headers = None ) -> NetworkArchive:
		headers = headers or { "User-Agent": self._USER_AGENT }
		async with self.session as session:
			async with self.session.get( url.raw, headers = headers ) as resp:
				response = NetworkArchive( response_status = resp.status,
				                           response_charset = resp.charset,
				                           response_content = await resp.read(),
				                           response_content_type = resp.content_type,
				                           response_headers = { k: v for k, v in resp.headers.items() },
				                           response_url = str( resp.url ),
				                           response_real_url = str( resp.real_url ),
				                           host = resp.host,
				                           request_headers = { k: v for k, v in resp.request_info.headers.items() },
				                           request_method = resp.request_info.method,
				                           request_url = str( resp.request_info.url ),
				                           request_real_url = str( resp.request_info.real_url ),
				                           )

				return response


class Archiver:
	basepath: ClassVar = "C:/Users/Mateus/Desktop/files"
	DEFAULT_PATH: ClassVar = pathlib.Path( basepath ) / "raw"

	def __init__( self, fetcher: Fetcher, semaphore = None ):
		self.fetcher = fetcher
		self.semaphore = semaphore or asyncio.Semaphore( 1000 )

	async def _fetchArchive( self, url: UrlEvent ) -> WebArchive:
		response = await self.fetcher.fetch( url )
		return WebArchive( url = url, content = response )

	async def _loadArchive( self, url: UrlEvent ) -> WebArchive:
		file_name = self.DEFAULT_PATH / url.digest()
		async with self.semaphore:
			cached = await load_async( file_name )
		return cached.map( WebArchive.from_json ).expect()

	async def loadArchive( self, url: UrlEvent ) -> WebArchive:
		try:
			return await self._loadArchive( url )
		except Exception as e:
			print( f"{url.digest()}: No cache found - fetching Response after {str( e )}" )
			return await self._fetchArchive( url )

	async def persistArchive( self, archive: WebArchive ) -> None:
		file_name = self.DEFAULT_PATH / archive.digest()
		with self.semaphore:
			await save_async( archive, file_name )


class Enricher:
	basepath: ClassVar = "C:/Users/Mateus/Desktop/files"
	DEFAULT_PATH: ClassVar = pathlib.Path( basepath ) / "enriched"

	def __init__( self, fetcher: Fetcher, semaphore = None ):
		self.fetcher = fetcher
		self.semaphore = semaphore or asyncio.Semaphore( 1000 )

	async def _fetch_youtube( self, archive: WebArchive ) -> Result[ ResponseEnrichment ]:

		...

	# archive.url
	# video_id = Htmls.toAttrib( "content", element.xpath( "//meta[@itemprop='videoId']" ) )
	# response = requests.get( "https://youtubetranscript.com/", params = { "server_vid": video_id } )
	# ...
	async def _fetch_html( self, archive: WebArchive ) -> Result[ ResponseEnrichment ]:
		for image in Htmls.getImage( ar):
			...
		...

	async def enrichArchive( self, archive: WebArchive ) -> Result[ ResponseEnrichment ]:
		match archive.url.kind:
			case UrlKinds.YOUTUBE:
				return await self._fetch_youtube( archive )
			case _:
				return await self._fetch_html( archive )

	async def persistEnrich( self, enrichment: ResponseEnrichment ) -> None:
		file_name = self.DEFAULT_PATH / enrichment.digest()
		async with self.semaphore:
			await save_async( enrichment, file_name )


class Processer:
	def __init__( self, session: ClientSession ):
		self.session = session
		self.semaphore = asyncio.Semaphore( 1000 )

		self.fetcher = Fetcher( self.session )
		self.archiver = Archiver( self.fetcher, self.semaphore )
		self.enricher = Enricher( self.fetcher, self.semaphore )

	async def process( self, url: Result[ UrlEvent ] ) -> PageContent:
		try:
			url = url.expect()
			archive = await self.archiver.loadArchive( url )

			persistArchive = self.archiver.persistArchive( archive )
			enrichCoro = self.enricher.enrichArchive( archive )
			_, enrichment = await asyncio.gather( persistArchive, enrichCoro )

			persistEnrichment = self.enricher.persistEnrich( enrichment )
			doProcess = self._doProcess( archive, enrichment )
			_, processed = await asyncio.gather( persistArchive, doProcess )

			return processed

		except Exception as e:
			print( e )

	async def _doProcess( self, archive: WebArchive, enrichment: ResponseEnrichment ) -> PageContent:
		...

# 		match info.content.response_content_type:
# 			case "text/html":
# 				return Result.ok( info ).flatMap( Htmls.getHtmlStructure )
# 			case "application/pdf":
# 				return Result.failure( Exception( "PDF not supported for now" ) )
# 			case other:
# 				return Result.failure( Exception( f"Unsupported mime type {other}" ) )
#
# #..
