from __future__ import annotations
import traceback
from typing import TypeVar, Callable, Generic, overload

K = TypeVar( "K" )
V = TypeVar( "V" )


class Result( Generic[ K ] ):
	__slots__ = ("__value", "__error")

	def __init__( self, value: K = None, error: Exception = None ):
		self.__value = value
		self.__error = error

	def successful( self ) -> bool:
		if self.__value:
			return True
		return False

	def map( self, fn: Callable[ [ K, ... ], V ], **kwargs ) -> Result[ V ]:
		# noinspection PyBroadException
		if not self.successful():
			return self

		try:
			v = fn( self.__value, **kwargs )
			return Result.ok( v )
		except Exception as e:
			return Result.failure( e )

	def flatMap( self, fn: Callable[ [ K ], Result[ V ] ] , **kwargs ) -> Result[ V ]:
		if not self.successful():
			return self
		return fn( self.__value, **kwargs )

	def recover( self, handler: Callable[ [ Exception ], K ] ) -> Result[ K ]:
		if not self.successful():
			try:
				res = handler( self.__error )
				return Result.ok( res )
			except Exception as e:
				return Result.failure( self.__error )
		return self

	@overload
	def orElse( self, fallback: K ) -> K:
		...

	@overload
	def orElse( self, fallback: Callable[ [ Exception ], K ] ) -> K:
		...

	@overload
	def orElse( self, fallback: Callable[ [ Exception ], None ] ) -> None:
		...

	def orElse( self, fallback ) -> K:
		if self.successful():
			return self.__value

		if callable( fallback ):
			res = fallback( self.__error )
			return res

		return fallback

	def expect( self ) -> K:
		if self.__error:
			raise self.__error
		return self.__value

	@classmethod
	def ok( cls, value: K ) -> Result[ K ]:
		return cls( value = value )

	@classmethod
	def failure( cls, error: Exception ) -> Result[ K ]:

		return cls( error = error )
