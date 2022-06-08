from __future__ import annotations
import traceback
from typing import TypeVar, Callable, Generic

K = TypeVar( "K" )
V = TypeVar( "V" )


class Result( Generic[ K ] ):
	__slots__ = ("__value", "__error")

	def __init__( self, value: K = None, error: Exception = None ):
		self.__value = value
		self.__error = error

	def is_success( self ) -> bool:
		if self.__value:
			return True
		return False

	def map( self, fn: Callable[ [ K ], V ] ) -> Result[ V ]:
		# noinspection PyBroadException
		if not self.is_success():
			return self

		try:
			v = fn( self.__value )
			return Result.ok( v )
		except Exception as e:
			return Result.failure( e )

	def flatMap( self, fn: Callable[ [ K ], Result[ V ] ] ) -> Result[ V ]:
		if not self.is_success():
			return self
		# noinspection PyBroadException
		try:
			return fn( self.__value )
		except Exception as e:
			return Result.failure( e )

	def recover( self, handler: Callable[ [ Exception ], K ] ) -> Result[ K ]:
		if not self.is_success():
			try:
				res = handler( self.__error )
				return Result.ok( res )
			except Exception as e:
				return Result.failure( self.__error )
		return self

	def orElse( self, fallback: K | Callable[ [ ], K ] ) -> K:

		if self.is_success():
			return self.__value

		if callable( fallback ):
			return fallback()

		return fallback

	def unwrap( self ) -> K:
		if self.__error:
			traceback.print_exception( self.__error )
			raise self.__error
		return self.__value

	@classmethod
	def ok( cls, value: K ) -> Result[ K ]:
		return cls( value = value )

	@classmethod
	def failure( cls, error: Exception ) -> Result[ K ]:
		return cls( error = error )
