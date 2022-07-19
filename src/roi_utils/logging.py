import asyncio
import json
import queue
import time
from typing import Protocol, Mapping

logging_queue = asyncio.Queue()
sync_queue = queue.Queue()


class Logger( Protocol ):

	async def info( self, message: str, extra: Mapping ) -> None:
		...

	async def warn( self, message: str, extra: Mapping ) -> None:
		...

	async def error( self, message: str, extra: Mapping, exc_info: Exception ) -> None:
		...


class ExecutionContext:
	blue = "\x1b[0m\x1b[0;34m"
	reset = "\x1b[0m"
	green = "\x1b[0m\x1b[0;32m"
	yellow = "\x1b[0m\x1b[0;33m"
	red = "\x1b[0m\x1b[0;31m"

	def __init__( self, operation: str, extra: Mapping = None,
	              raises = True,
	              exception_level = "warn" ):

		self.operation = operation
		self.raises = raises
		self.exception_level = exception_level
		self.start = None

		extra = dict( extra ) if extra else { }
		extra = { k: extra[ k ] for k in sorted( extra.keys() ) }
		self.context = {
				**extra,
				"step"     : "START",
				"operation": self.operation,
				"start"    : self.start,
		}

	async def __aenter__( self ):
		self.start = time.perf_counter()
		self.context[ "start" ] = self.start

		msg = (self.blue +
		       json.dumps( self.context, separators = (",\t", ":") ) +
		       self.reset)

		sync_queue.put( ("info", msg) )

	async def __aexit__( self, exc_type, exc_val, exc_tb ):
		finish = time.perf_counter()
		self.context[ "finish" ] = finish
		self.context[ "duration" ] = round( finish - self.start, 2 )

		if not exc_val:
			self.context[ "step" ] = "DONE"
			level = "info"
			color = self.green


		else:
			self.context[ "step" ] = "FAIL"
			level = "warn" if self.exception_level == "warn" else "error"
			color = self.yellow if self.exception_level == "warn" else self.red

			self.context[ level ] = str( exc_type ) + " " + str( exc_val )

		msg = color + json.dumps( self.context, separators = (",\t", ":") ) + self.reset
		sync_queue.put( (level, msg) )

		if not self.raises:
			return True


async def asyncLog( logger ):
	...


def log( logger, this_queue: queue.Queue ):
	try:
		while True:

			level, msg = this_queue.get( timeout = 10 )

			match level:
				case 'info':
					logger.info( msg )
				case 'warn':
					logger.warning( msg )
				case 'error':
					logger.error( msg )

	except Exception as e:
		print( e )
