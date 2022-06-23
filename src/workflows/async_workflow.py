import asyncio

import aiohttp
from tqdm import tqdm

from roi_web import fetchResponseAsync, baseLoadStream, persistResponseAsync


async def main():
	urls = baseLoadStream()
	urls = map( lambda x: x.expect(),
	            filter( lambda x: x.successful(), urls ) )

	semaphore = asyncio.Semaphore( 30 )
	async with aiohttp.ClientSession( connector = aiohttp.TCPConnector( verify_ssl = False, limit_per_host = 5, limit = 15 ) ) as session:

		async def doIt( url ):
			async with semaphore:
				try:
					archive = await fetchResponseAsync( session, url )
					persistResponseAsync( archive )
				except Exception as e:
					print( e )

		results = [ doIt( url ) for url in tqdm( urls ) ]

		await asyncio.gather( *results )


if __name__ == "__main__":
	asyncio.set_event_loop_policy( asyncio.WindowsSelectorEventLoopPolicy() )
	asyncio.run( main() )
