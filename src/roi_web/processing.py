import asyncio
import os
import pathlib
import re
from typing import Iterable, ClassVar

from aiohttp import ClientSession

from roi_utils import Result, save_async, load_async
from roi_utils.logging import ExecutionContext
from .domain import WebArchive, UrlEvent, PageContent, NetworkArchive, ResponseEnrichment, UrlKinds, String
from .parsing import EventParsing, HTML, PDF, Youtube

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

	async def fetch( self, url: String, headers = None, params = None ) -> NetworkArchive:
		headers = headers or { "User-Agent": self._USER_AGENT }
		params = params or { }

		async with self.session.get( url, headers = headers, params = params ) as resp:
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
			if response.response_status < 200 or response.response_status > 299:
				raise Exception( "Bad Response status " + str( response.response_status ) )
			return response


class Archiver:
	basepath: ClassVar = "C:/Users/Mateus/Desktop/files"
	DEFAULT_PATH: ClassVar = pathlib.Path( basepath ) / "raw"

	def __init__( self, fetcher: Fetcher, semaphore = None ):
		self.fetcher = fetcher
		self.semaphore = semaphore or asyncio.Semaphore( 1000 )

	async def _fetchArchive( self, url: UrlEvent ) -> WebArchive:
		async with ExecutionContext( "Fetching WebArchive",
		                             extra = { "digest": url.digest(), "kind": url.kind.value } ):
			response = await self.fetcher.fetch( url.raw )
			return WebArchive( url = url, content = response )

	async def loadArchive( self, url: UrlEvent ) -> WebArchive:
		file_name = self.DEFAULT_PATH / url.digest()
		try:
			async with ExecutionContext( "Loading cached web archive",
			                             extra = { "digest": url.digest(), "kind": url.kind.value } ):
				cached = await load_async( file_name )
				cached = WebArchive.from_json( cached )
				status = cached.content.response_status
				if status < 200 or 299 < status:
					raise Exception( "Unsucessful response" )

				return cached

		except:
			return await self._fetchArchive( url )

	async def persistArchive( self, archive: WebArchive ) -> None:
		async with self.semaphore:
			async with ExecutionContext( "Persisting Archive", raises = False,
			                             extra = { "kind": archive.kind.value, "digest": archive.digest() } ):
				file_name = self.DEFAULT_PATH / archive.digest()
				await save_async( archive, file_name )


class Enricher:
	basepath: ClassVar = "C:/Users/Mateus/Desktop/files"
	DEFAULT_PATH: ClassVar = pathlib.Path( basepath ) / "enriched"
	pattern = re.compile( r"(?<=v=)([a-zA-Z0-9_]+)(?=\b|&)" )

	def __init__( self, fetcher: Fetcher, semaphore = None ):
		self.fetcher = fetcher
		self.semaphore = semaphore or asyncio.Semaphore( 1000 )

	async def _fetch_youtube( self, archive: WebArchive ) -> ResponseEnrichment:
		videoId = self.pattern.search( archive.url.raw )
		if not videoId:
			raise Exception( f"{archive.url.raw} is not a youtube video" )

		async with ExecutionContext( "Calling youtubetranscript",
		                             extra = { "kind": archive.kind.value, "digest": archive.digest() } ):
			content = await self.fetcher.fetch( "https://youtubetranscript.com", params = { "server_vid": videoId.group( 0 ) } )
			enrich = ResponseEnrichment( url = archive.url, transcriptions = [ HTML.youtubeTranscript( content ) ] )
			return enrich

	async def enrichArchive( self, archive: WebArchive ) -> ResponseEnrichment | None:

		try:
			async with ExecutionContext( "Loading Cached Enrichment",
			                             extra = { "kind": archive.kind.value, "digest": archive.digest() } ):
				filename = self.DEFAULT_PATH / archive.digest()
				content = await load_async( filename )
				return ResponseEnrichment.from_json( content )

		except:
			try:
				return await self._fetch_enrichment( archive )
			except:
				return None

	async def _fetch_enrichment( self, archive: WebArchive ) -> ResponseEnrichment:

		async with ExecutionContext( "Fetching new Enrichment",
		                             extra = { "kind": archive.kind.value, "digest": archive.digest() } ):

			match archive.url.kind:

				case UrlKinds.YOUTUBE:
					return await self._fetch_youtube( archive )
				case _:
					raise Exception( "No enrichment is known for this archive." )

	async def persistEnrich( self, enrichment: ResponseEnrichment | None ) -> None:

		if enrichment:
			file_name = self.DEFAULT_PATH / enrichment.digest()
			async with ExecutionContext( "Persisting Enrichment", raises = False,
			                             extra = { "kind": enrichment.kind.value, "digest": enrichment.digest() } ):
				await save_async( enrichment, file_name )


class Processer:
	basepath: ClassVar = "C:/Users/Mateus/Desktop/files"
	DEFAULT_PATH: ClassVar = pathlib.Path( basepath ) / "processed"

	def __init__( self, session: ClientSession ):
		self.session = session
		self.semaphore = asyncio.Semaphore( 1000 )

		self.fetcher = Fetcher( self.session )
		self.archiver = Archiver( self.fetcher, self.semaphore )
		self.enricher = Enricher( self.fetcher, self.semaphore )

	async def process( self, url: Result[ UrlEvent ] ) -> None:
		try:
			url = url.expect()
		except Exception as e:
			print( e )

		async with ExecutionContext( "Processing url",
		                             extra = { "digest": url.digest(), "kind": url.kind.value },
		                             exception_level = "fail", raises = False ):
			archive = await self.archiver.loadArchive( url )
			asyncio.create_task( self.archiver.persistArchive( archive ) )

			enrichment = await self.enricher.enrichArchive( archive )
			asyncio.create_task( self.enricher.persistEnrich( enrichment ) )

			processed = self._doProcess( archive, enrichment )
			asyncio.create_task( self.persistProcessed( processed ) )

	def _doProcess( self, archive: WebArchive, enrichment: ResponseEnrichment | None ) -> PageContent:

		match archive.url.kind, archive.content.response_content_type, enrichment:
			case UrlKinds.YOUTUBE, _, valid:
				return Youtube.structure( archive ).update( text = " ".join( valid.transcriptions ) )
			case _, "text/html", _:
				return HTML.structure( archive )
			case _, "application/pdf", _:
				return PDF.structure( archive )
			case _, mime, _:
				raise Exception( "Unsupported Mime Type " + mime )

	async def persistProcessed( self, processed: PageContent ):

		async with ExecutionContext( "Persist Processed",
		                             extra = { "digest": processed.digest(), "kind": "Unknown" } ):
			try:
				await save_async( processed, path = self.DEFAULT_PATH / processed.digest() )
			except Exception as e:
				print( e )
