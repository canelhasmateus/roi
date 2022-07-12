import time
from logging import getLogger
from typing import Protocol, Mapping


class Logger( Protocol ):

	def info( self, message: str, extra: Mapping ) -> None:
		...

	def error( self, message: str, extra: Mapping, exc_info: Exception ) -> None:
		...


class ExecutionContext:
	def __init__( self, operation: str, extra: Mapping,
	              logger = None,
	              raises = True,
	              exception_level = "warn" ):
		self.logger: Logger = logger or getLogger( "Roi" )
		self.extra = dict( extra )
		self.operation = operation
		self.raises = raises
		self.exception_level = exception_level
		self.start = None

	def __enter__( self, ):
		self.start = time.perf_counter()
		self.logger.info( "\x1b[0m" + "\x1b[0;34m" +
		                  "[START]\t" + self.operation +
		                  "\x1b[0m", extra = self.extra )

	def __exit__( self, exc_type, exc_val, exc_tb ):
		finish = time.perf_counter()
		duration = finish - self.start
		duration = round( duration, 2 )
		if not exc_val:

			self.logger.info( "\x1b[0m" + "\x1b[0;32m"
			                  + f"\t[DONE]\t" + f"\t{duration}s " +
			                  self.operation
			                  + "\x1b[0m", extra = self.extra )
		else:
			if self.exception_level == "warn":

				self.logger.info( "\x1b[0m" + "\x1b[0;33m" +
				                  f"\t[FAIL]\t" + f"\t{duration}s " +
				                  self.operation + "\t" + str( exc_val ) +
				                  "\x1b[0m", extra = self.extra )
			else:

				self.logger.error( "\x1b[0m" + "\x1b[0;31m" +
				                   f"\t[FAIL]\t" + f"\t{duration}s " +
				                   self.operation +
				                   "\x1b[0m", extra = self.extra, exc_info = exc_val )

		if not self.raises:
			return True
