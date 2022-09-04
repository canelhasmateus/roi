import asyncio
import json
import logging
import threading

from roi_utils.logging import ExecutionContext, log, sync_queue
from roi_web import Processer, loadEvents
from roi_web.processing import Fetcher


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
    seen = set()
    for f in Processer.DEFAULT_PATH.glob( "*" ):
        try:
            with open( f, "r" ) as file:
                payload = json.loads( file.read() )
                seen.add( payload[ "url" ] )
        except Exception as e:
            f.unlink()

    events = loadEvents( seen=seen )
    batches = batch( 3000, events )

    async with Processer( fetcher=Fetcher() ) as processer:
        with ExecutionContext( "Processing all events" ):
            for i, minibatch in enumerate( batches ):
                with ExecutionContext( f"Processing batch", exc_suppress=True,
                                       extra={"number": i + 1, "length": len( minibatch )} ):
                    #
                    #
                    await asyncio.gather( *map( processer.process, minibatch ) )

    logging.finished = True


if __name__ == "__main__":
    logger = logging.getLogger( "Roi" )
    logger.setLevel( logging.INFO )
    handler = logging.StreamHandler()
    handler.setLevel( logging.INFO )
    logger.addHandler( handler )

    logging_thread = threading.Thread( target=log, args=(logger, sync_queue) )
    logging_thread.start()

    asyncio.run( main() )
