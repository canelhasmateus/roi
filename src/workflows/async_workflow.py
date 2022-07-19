import asyncio
import logging
import threading

import aiohttp
from aiohttp import ClientTimeout

from roi_utils.logging import ExecutionContext, log, sync_queue
from roi_web import loadEvents, Processer


def batch( n, itr ):
	batch = [ ]
	cnt = 0
	for el in itr:
		batch.append( el )
		cnt += 1
		if cnt == n:
			yield batch
			batch = [ ]
			cnt = 0
	else:
		yield batch


async def main():
	tcp_connector = aiohttp.TCPConnector( verify_ssl = False, limit_per_host = 2, limit = 200 )
	timeout = ClientTimeout( total = 300 )
	session = aiohttp.ClientSession( connector = tcp_connector, timeout = timeout )

	async with ExecutionContext( "Processing all events" ):
		events = loadEvents()
		processer = Processer( session )
		work = map( processer.process, events )
		await asyncio.gather( *work )


if __name__ == "__main__":
	logger = logging.getLogger( "Roi" )
	logger.setLevel( logging.INFO )

	handler = logging.StreamHandler()
	handler.setLevel( logging.INFO )
	logger.addHandler( handler )

	threading.Thread( target = log, args = (logger, sync_queue) ).start()

	asyncio.set_event_loop_policy( asyncio.WindowsSelectorEventLoopPolicy() )
	asyncio.run( main() )
# cProfile.run( "", sort = "tottime" )
