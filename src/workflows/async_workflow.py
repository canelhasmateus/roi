import asyncio

import aiohttp
from tqdm import tqdm

from roi_utils import Result
from roi_web import fetchResponseAsync, baseLoadStream, persistResponseAsync, processResponseBase, persistProcessedBase, processResponseAsync, UrlEvent


async def doIt( session, semaphore, url: Result[ UrlEvent ] ):
	try:
		url = url.expect()
		async with semaphore:
			archive = await fetchResponseAsync( session, url )
			await persistResponseAsync( archive )
			processed = await processResponseAsync( session, archive )
			print()
	# await persistProcessedBase()
	except Exception as e:
		print( e )


async def main():
	semaphore = asyncio.Semaphore( 30 )
	async with aiohttp.ClientSession( connector = aiohttp.TCPConnector( verify_ssl = False, limit_per_host = 5, limit = 15 ) ) as session:
		results = [ doIt( session, semaphore, url ) for url in baseLoadStream()]
		await asyncio.gather( *results )


if __name__ == "__main__":
	asyncio.set_event_loop_policy( asyncio.WindowsSelectorEventLoopPolicy() )
	asyncio.run( main() )
