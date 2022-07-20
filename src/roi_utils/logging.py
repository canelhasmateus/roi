import asyncio
import json
import queue
import time
import traceback
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

	def __init__( self, operation: str, *, extra: Mapping = None,
	              exc_suppress = False,
	              exc_level = "error" ):

		self.operation = operation
		self.supress_error = exc_suppress
		self.exception_level = exc_level
		self.start = time.perf_counter()

		extra = extra or { }
		extra = { k: extra[ k ] for k in sorted( extra.keys() ) }
		self.context = {
				"step"     : "INIT",
				"start"    : self.width_value( self.start ),
				"finish"   : self.width_value( self.start ),
				"duration" : self.width_string( "" ),
				"operation": self.operation,
				**extra,
		}

	def __enter__( self ):
		self.start = time.perf_counter()
		self.context[ "start" ] = self.width_value( self.start )

		msg = self.as_message( self.blue, self.context )
		sync_queue.put( ("info", msg) )

	def __exit__( self, exc_type, exc_val, exc_tb ):
		finish = time.perf_counter()
		self.context[ "finish" ] = self.width_value( finish )
		self.context[ "duration" ] = self.width_value( finish - self.start )

		if not exc_val:
			self.context[ "step" ] = "DONE"
			level = "info"
			color = self.green
		elif exc_val and self.exception_level == "warn":
			self.context[ "error" ] = self.as_error( exc_type, exc_val )
			self.context[ "step" ] = "WARN"
			level = self.exception_level
			color = self.yellow
		else:
			self.context[ "error" ] = self.as_error( exc_type, exc_val )
			self.context[ "traceback" ] = self.as_traceback( exc_tb )
			self.context[ "step" ] = "FAIL"
			level = self.exception_level
			color = self.red

		msg = self.as_message( color, self.context )
		sync_queue.put( (level, msg) )

		if exc_val and self.supress_error:
			return True

	@classmethod
	def as_message( cls, color, mapping ):
		return color + json.dumps( mapping ) + cls.reset

	@classmethod
	def width_value( cls, value, width = 6, precision = 2 ):
		return format( value, f"{width}.{precision}f" )

	@classmethod
	def width_string( cls, value: str, width = 6 ):
		return value.ljust( width )

	@classmethod
	def as_error( cls, exc, val, ):
		return str( exc ) + " " + str( val )

	@classmethod
	def as_traceback( cls, tb ):
		return "\n".join( traceback.format_tb( tb )[ :5 ] )


async def asyncLog( logger ):
	...


def log( logger, this_queue: queue.Queue ):
	while True:
		try:
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
