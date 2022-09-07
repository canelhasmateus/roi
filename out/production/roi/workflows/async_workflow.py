import asyncio
import logging
import threading

from roi_utils.logging import ExecutionContext, log, sync_queue
from roi_web import Processer, load_events
from roi_web.processing import Fetcher, load_processed


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
    seen = {i.url for i in load_processed()}
    events = load_events( seen=seen )
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
