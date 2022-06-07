from __future__ import annotations
import traceback
from typing import TypeVar, Callable, Generic

K = TypeVar( "K" )
V = TypeVar( "V" )


class Result( Generic[ K ] ):
	__slots__ = ("value", "error")

	def __init__( self, value: K = None, error: Exception = None ):
		self.value = value
		self.error = error

	def map( self, fn: Callable[ [ K ], V ] ) -> Result[ V ]:

		# noinspection PyBroadException
		try:
			v = fn( self.value )
			return Result.ok( v )
		except Exception as e:
			return Result.failure( e )

	def flatMap( self, fn: Callable[ [ K ], Result[ V ] ] ) -> Result[ V ]:

		# noinspection PyBroadException
		try:
			return fn( self.value )
		except Exception as e:
			return Result.failure( e )

	def orElse( self, fallback: K | Callable[ [ ], K ] ) -> K:

		if not self.error:
			return self.value

		if callable( fallback ):
			return fallback()

		return fallback

	def unwrap( self ) -> K:
		if self.error:
			traceback.print_exception( self.error )
			raise self.error
		return self.value

	@classmethod
	def ok( cls, value: K ) -> Result[ K ]:
		return cls( value = value )

	@classmethod
	def failure( cls, error: Exception ) -> Result[ K ]:
		return cls( error = error )
