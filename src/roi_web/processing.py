import asyncio
import os
import pathlib
import re
from typing import Iterable, ClassVar

from aiohttp import ClientSession

from roi_utils import Result, save_async, load_async
from .domain import WebArchive, UrlEvent, PageContent, NetworkArchive, ResponseEnrichment, UrlKinds, String
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

	async def fetch( self, url: String, headers = None , params = None) -> NetworkArchive:
		headers = headers or { "User-Agent": self._USER_AGENT }
		params = params or {  }

		async with self.session.get( url, headers = headers , params = params) as resp:
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
		response = await self.fetcher.fetch( url.raw )
		return WebArchive( url = url, content = response )

	async def _loadArchive( self, url: UrlEvent ) -> WebArchive:
		file_name = self.DEFAULT_PATH / url.digest()
		async with self.semaphore:
			cached = await load_async( file_name )
		return cached.map( WebArchive.from_json ).expect()

	async def loadArchive( self, url: UrlEvent ) -> WebArchive:
		try:
			archive = await self._loadArchive( url )
			print( f"Loaded {archive.url}" )
			return archive
		except Exception as e:
			print( f"{url.digest()}: No cache found - fetching Response after {str( e )}" )
			return await self._fetchArchive( url )

	async def persistArchive( self, archive: WebArchive ) -> None:
		file_name = self.DEFAULT_PATH / archive.digest()
		async with self.semaphore:
			await save_async( archive, file_name )


class Enricher:
	basepath: ClassVar = "C:/Users/Mateus/Desktop/files"
	DEFAULT_PATH: ClassVar = pathlib.Path( basepath ) / "enriched"
	pattern = re.compile( r"(?<=v=)([a-zA-Z0-9]+)(?=\b|&)" )
	def __init__( self, fetcher: Fetcher, semaphore = None ):
		self.fetcher = fetcher
		self.semaphore = semaphore or asyncio.Semaphore( 1000 )

	async def _fetch_youtube( self, archive: WebArchive ) -> Result[ ResponseEnrichment ]:
		videoId = self.pattern.search( archive.url.raw )
		if not videoId:
			return Result.failure( Exception( f"{archive.url.raw} is not a youtube video" ) )

		try:

			content = await self.fetcher.fetch( "https://youtubetranscript.com", params = { "server_vid": videoId.group(0) }  )

			enrich = ResponseEnrichment( url = archive.url, transcriptions = [ Htmls.youtubeTranscript(content) ] )
			return Result.ok( enrich )
		except Exception as e:
			return Result.failure( e )

		# archive.url
			# response = requests.get( ")
		# ...
	async def _fetch_html( self, archive: WebArchive ) -> Result[ ResponseEnrichment ]:
		# for image in Htmls.getImage( ar):
		# 	...
		...

	async def enrichArchive( self , archive : WebArchive) -> ResponseEnrichment:

		filename = self.DEFAULT_PATH / archive.digest()
		content = await load_async( filename )
		try:
			return content.map( ResponseEnrichment.from_json ).expect()
		except Exception as e:
			print( f"{archive.digest()}: No cache found - fetching Response after {str( e )}" )
			return await self._fetch_enrichment( archive )


	async def _fetch_enrichment( self, archive: WebArchive ) -> ResponseEnrichment :

		match archive.url.kind:
			case UrlKinds.YOUTUBE:
				return await self._fetch_youtube( archive )
			case _:
				return ResponseEnrichment( url = archive.url , transcriptions = [])

	async def persistEnrich( self, enrichment: Result[ResponseEnrichment]  ) -> None:
		enrichment= enrichment.expect()
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
			res = await asyncio.gather( persistArchive, enrichCoro )
			_, enrichment = res
			persistEnrichment = self.enricher.persistEnrich( enrichment )
			doProcess = self._doProcess( archive, enrichment )
			_, processed = await asyncio.gather( persistEnrichment, doProcess )

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
