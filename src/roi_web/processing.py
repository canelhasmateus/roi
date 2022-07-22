import asyncio
import os
import pathlib
import re
from typing import Iterable, ClassVar

from aiohttp import ClientSession

from roi_utils import Result, save_async, load_async, ExecutionContext
from roi_web import WebArchive, UrlEvent, PageContent, NetworkArchive, ResponseEnrichment, UrlKinds, String, EventParsing, HTML, PDF, Youtube

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


class Processer:
	basepath: ClassVar = "C:/Users/Mateus/Desktop/files"
	DEFAULT_RAW_PATH: ClassVar = pathlib.Path( basepath ) / "raw"
	DEFAULT_PATH: ClassVar = pathlib.Path( basepath ) / "processed"
	DEFAULT_RICH_PATH: ClassVar = pathlib.Path( basepath ) / "enriched"
	youtube_pattern: ClassVar = re.compile( r"(?<=v=)(\w+?)(?=\b|&)" )
	def __init__( self, session: ClientSession ):
		self.session = session
		self.semaphore = asyncio.Semaphore( 1000 )
		self.fetcher = Fetcher( self.session )

	async def __aenter__( self ):
		return self

	async def __aexit__( self, exc_type, exc_val, exc_tb ):
		await self.session.__aexit__( exc_type, exc_val, exc_tb )

	async def process( self, url: Result[ UrlEvent ] ) -> None:
		url = url.expect()
		with ExecutionContext( "Processing url",
		                       extra = { "digest": url.digest(), "kind": url.kind.value },
		                       exc_suppress = True ):
			rawArchive = await self.getRaw( url )
			richArchive = await self.getRich( rawArchive )
			processed = self.getFinal( rawArchive, richArchive )

		await asyncio.gather( self.saveRaw( rawArchive ),
		                      self.saveRich( richArchive ),
		                      self.saveFinal( processed ) )

		...

	# region raw
	async def fetchRaw( self, url: UrlEvent ) -> WebArchive:
		with ExecutionContext( "Fetching Raw",
		                       extra = { "digest": url.digest(), "kind": url.kind.value } ):

			response = await self.fetcher.fetch( url.raw )
			if 200 <= response.response_status <= 299:
				return WebArchive( url = url, content = response )
			else:
				raise Exception( "Unsucessful response" )

	async def loadRaw( self, url: UrlEvent ):
		with ExecutionContext( "Loading Raw",
		                       extra = { "digest": url.digest(), "kind": url.kind.value },
		                       exc_level = "warn" ):

			file_path = self.DEFAULT_RAW_PATH / url.digest()
			content = await load_async( file_path )
			saved = WebArchive.from_json( content )

			status = saved.content.response_status
			if 200 <= status <= 299:
				return saved
			else:
				file_path.unlink( missing_ok = True )
				raise Exception( "Bad response status " + str( status ) )

	async def getRaw( self, url: UrlEvent ) -> WebArchive:
		try:
			return await self.loadRaw( url )
		except:
			return await self.fetchRaw( url )

	async def saveRaw( self, archive: WebArchive ) -> None:
		with ExecutionContext( "Persisting Archive",
		                       exc_suppress = True,
		                       extra = { "kind": archive.kind.value, "digest": archive.digest() } ):
			file_name = self.DEFAULT_RAW_PATH / archive.digest()
			await save_async( archive, file_name )

	# endregion

	# region rich
	async def loadRich( self, url: UrlEvent ):
		with ExecutionContext( "Loading Rich",
		                       exc_level = "warn",
		                       extra = { "kind": url.kind.value, "digest": url.digest() } ):
			filename = self.DEFAULT_RICH_PATH / url.digest()
			content = await load_async( filename )
			return ResponseEnrichment.from_json( content )

	async def getRich( self, archive: WebArchive ) -> ResponseEnrichment | None:

		try:
			return await self.loadRich( archive.url )
		except:
			try:
				return await self.fetchRich( archive )
			except:
				return None

	async def fetchRich( self, archive: WebArchive ) -> ResponseEnrichment:
		with ExecutionContext( "Fetching rich",
		                       exc_level = "warn",
		                       extra = { "kind": archive.kind.value, "digest": archive.digest() } ):
			match archive.url.kind:
				case UrlKinds.YOUTUBE:
					return await self.richYoutube( archive )
				case _:
					raise Exception( "No enrichment is known for this archive." )

	async def saveRich( self, enrichment: ResponseEnrichment | None ) -> None:
		if enrichment:
			with ExecutionContext( "Persisting Enrichment",
			                       exc_suppress = True,
			                       extra = { "kind": enrichment.kind.value, "digest": enrichment.digest() } ):
				file_path = self.DEFAULT_RICH_PATH / enrichment.digest()
				await save_async( enrichment, file_path )

	async def richYoutube( self, archive: WebArchive ) -> ResponseEnrichment:
		videoId = self.youtube_pattern.search( archive.url.raw )

		if not videoId:
			raise Exception( f"{archive.url.raw} is not a youtube video" )

		with ExecutionContext( "Youtube Transcript",
		                       extra = { "kind": archive.kind.value, "digest": archive.digest() } ):
			content = await self.fetcher.fetch( "https://youtubetranscript.com",
			                                    params = { "server_vid": videoId.group( 0 ) } )

			status = content.response_status
			if 200 <= status <= 299:
				return ResponseEnrichment( url = archive.url,
				                           transcriptions = [ HTML.youtubeTranscript( content ) ] )
			else:
				raise Exception( "Bad response status " + str( status ) )

	# endregion

	# region processed
	def getFinal( self, archive: WebArchive, enrichment: ResponseEnrichment | None ) -> PageContent:

		with ExecutionContext( "Processing",
		                       exc_level = "error",
		                       exc_suppress = True,
		                       extra = { "digest": archive.digest(), "kind": archive.kind.value } ):

			match archive.url.kind, archive.content.response_content_type, enrichment:
				case UrlKinds.YOUTUBE, _, valid:
					return Youtube.structure( archive ).update( text = " ".join( valid.transcriptions ) )
				case _, "text/html", _:
					return HTML.structure( archive )
				case _, "application/pdf", _:
					return PDF.structure( archive )
				case _, mime, _:
					raise Exception( "Unsupported Mime Type " + mime )

	async def saveFinal( self, processed: PageContent ):
		with ExecutionContext( "Persist Processed",
		                       exc_suppress = True,
		                       extra = { "digest": processed.digest(), "kind": "Unknown" } ):
			await save_async( processed, path = self.DEFAULT_PATH / processed.digest() )

	# endregion
	...
