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

			return response


class Archiver:
	basepath: ClassVar = "C:/Users/Mateus/Desktop/files"
	DEFAULT_PATH: ClassVar = pathlib.Path( basepath ) / "raw"

	def __init__( self, fetcher: Fetcher, semaphore = None ):
		self.fetcher = fetcher
		self.semaphore = semaphore or asyncio.Semaphore( 1000 )

	async def _fetchArchive( self, url: UrlEvent ) -> WebArchive:
		with ExecutionContext( "Fetching WebArchive",
		                       extra = { "digest": url.digest(), "kind": url.kind } ):
			response = await self.fetcher.fetch( url.raw )
			return WebArchive( url = url, content = response )

	async def loadArchive( self, url: UrlEvent ) -> WebArchive:

		try:
			async with self.semaphore:
				with ExecutionContext( "Loading cached web archive",
				                       extra = { "digest": url.digest(), "kind": url.kind } ):
					file_name = self.DEFAULT_PATH / url.digest()
					cached = await load_async( file_name )
					cached = cached.map( WebArchive.from_json ).expect()
					status = cached.content.response_status
					if status < 200 and 299 < status:
						file_name.unlink()
						raise Exception( "Unsucessful response" )

					return cached

		except:
			return await self._fetchArchive( url )

	async def persistArchive( self, archive: WebArchive ) -> None:
		async with self.semaphore:
			with ExecutionContext( "Persisting Archive", raises = False,
			                       extra = { "kind": archive.kind, "digest": archive.digest() } ):
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

		with ExecutionContext( "Calling youtubetranscript",
		                       extra = { "kind": archive.kind, "digest": archive.digest() } ):
			content = await self.fetcher.fetch( "https://youtubetranscript.com", params = { "server_vid": videoId.group( 0 ) } )
			enrich = ResponseEnrichment( url = archive.url, transcriptions = [ HTML.youtubeTranscript( content ) ] )
			return enrich

	async def enrichArchive( self, archive: WebArchive ) -> ResponseEnrichment | None:

		try:
			with ExecutionContext( "Loading Cached Enrichment",
			                       extra = { "kind": archive.kind, "digest": archive.digest() } ):

				filename = self.DEFAULT_PATH / archive.digest()
				content = await load_async( filename )
				return content.map( ResponseEnrichment.from_json ).expect()

		except:
			return await self._fetch_enrichment( archive )

	async def _fetch_enrichment( self, archive: WebArchive ) -> ResponseEnrichment:

		with ExecutionContext( "Fetching new Enrichment",
		                       extra = { "kind": archive.kind, "digest": archive.digest() } ):

			match archive.url.kind:

				case UrlKinds.YOUTUBE:
					return await self._fetch_youtube( archive )
				case _:
					raise Exception( "No enrichment is known for this archive." )

	async def persistEnrich( self, enrichment: ResponseEnrichment | None ) -> None:

		if enrichment:
			file_name = self.DEFAULT_PATH / enrichment.digest()
			async with self.semaphore:
				with ExecutionContext( "Persisting Enrichment", raises = False,
				                       extra = { "kind": enrichment.kind, "digest": enrichment.digest() } ):
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

	async def process( self, url: Result[ UrlEvent ] ) -> PageContent:
		try:
			url = url.expect()
			archive = await self.archiver.loadArchive( url )
			enrichment = await self.enricher.enrichArchive( archive )
			processed = await self._doProcess( archive, enrichment )

			await asyncio.gather(
					self.archiver.persistArchive( archive ),
					self.enricher.persistEnrich( enrichment ),
					self.persistProcessed( processed ) )

			return processed

		except Exception as e:
			...

	async def _doProcess( self, archive: WebArchive, enrichment: ResponseEnrichment | None ) -> PageContent:
		with ExecutionContext( "Processing archive",
		                       extra = { "kind": enrichment.kind, "digest": enrichment.digest() } ):

			match archive.url.kind, archive.content.response_content_type, enrichment:
				case UrlKinds.YOUTUBE, _, valid:
					structure = Youtube.structure( archive )
					return structure.update(
							text = " ".join( valid.transcriptions ) )
				case _, "text/html", _:
					return HTML.structure( archive )
				case _, "application/pdf", _:
					return PDF.structure( archive )

				case _:
					raise Exception( "Unsupported Mime Type" )

	async def persistProcessed( self, processed: PageContent ):
		async with self.semaphore:
			with ExecutionContext( "Persist Processed",
			                       extra = { "digest": processed.digest(), "kind": "Unknown" } ):
				try:
					await save_async( processed, path = self.DEFAULT_PATH / processed.digest() )
				except Exception as e:
					print()
