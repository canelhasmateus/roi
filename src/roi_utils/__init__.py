from __future__ import annotations
from __future__ import annotations

from inspect import iscoroutinefunction
from typing import Callable
from typing import TypeVar, Generic, Protocol
from typing import overload


K = TypeVar( "K" )
V = TypeVar( "V" )


class Result( Generic[ K ] ):
	__slots__ = ("__value", "__error")

	def __init__( self, value: K = None, error: Exception = None ):
		self.__value = value
		self.__error = error

	def successful( self ) -> bool:
		if self.__error:
			return False
		return True

	def map( self, fn: Callable[ [ K, ... ], V ], **kwargs ) -> Result[ V ]:
		# noinspection PyBroadException
		if not self.successful():
			return self

		try:
			v = fn( self.__value, **kwargs )
			return Result.ok( v )
		except Exception as e:
			return Result.failure( e )

	def flatMap( self, fn: Callable[ [ K ], Result[ V ] ], **kwargs ) -> Result[ V ]:
		if not self.successful():
			return self
		return fn( self.__value, **kwargs )

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


class Transformation( Protocol[ K, V ] ):
	def __call__( self, value: K, *args, **kwargs ) -> V:
		...


class Thunk( Protocol[ K, V ] ):
	def __call__( self ) -> V:
		...


class Pull( Protocol[ K, V ] ):
	async def __call__( self, value: K, *args, **kwargs ) -> V:
		...


# Morphism = Transformation | Pull
# class Resolver( Generic[ K ] ):
# 	def __init__( self, value: K ):
# 		self.seed = value
# 		self.todos = [ ]
#
# 	def __enter__( self ):
# 		return self.root( self.seed )
#
# 	async def __resolve( self ):
# 		async with trio.open_nursery() as nursery:
# 			for fn in self.todos:
# 				nursery.start_soon( fn )
#
# 	def __exit__( self, exc_type, exc_val, exc_tb ):
# 		trio.run( self.__resolve )
#
# 	def register( self, fn ):
# 		self.todos.append( fn )
#
# 	def root( self, value: K ) -> FutureResult[ K ]:
# 		res = LazyResult.of( value )
# 		return ResultProxy( res, self.register )


# class ResultProxy:
# 	__slots__ = ("__delegate", "__callback", "__weakref__")
#
# 	def __init__( self, delegate: LazyResult, callback ):
# 		self.__delegate: LazyResult = delegate
# 		self.__callback = callback
#
# 	def __getattr__( self, item ):
# 		if item == "map":
# 			return self.map
#
# 		return getattr( self.__delegate, item )
#
# 	def map( self, fn, **kwargs ):
# 		newres = self.__delegate.map( fn, **kwargs )
# 		if not iscoroutinefunction( fn ):
# 			async def a():
# 				return newres.value()
# 		else:
# 			async def a():
# 				return await newres.value()
#
# 		self.__callback( a )
# 		return ResultProxy( newres, self.__callback )
#
#
# class LazyResult( Generic[ K ] ):
# 	class Guard:
# 		...
#
# 	__slots__ = ("__supply", "__value", "__error")
#
# 	def __init__( self, supplier: Thunk[ K ] ):
# 		self.__supply = supplier
# 		self.__value = self.Guard
# 		self.__error = None
#
# 	@property
# 	def __done( self ):
# 		return self.__error is not None or self.__value != self.Guard
#
# 	def successful( self ):
# 		...
#
# 	def value( self ):
# 		if not self.__done:
# 			try:
# 				self.__value = self.__supply()
# 			except Exception as e:
# 				self.__error = e
#
# 		return self.__value or self.__error
#
# 	def map( self, fn: Transformation[ K, V ], **kwargs ) -> LazyResult[ V ]:
# 		def supplier():
# 			val = self.value()
# 			if isinstance( val, Exception ):
# 				raise val
# 			return fn( val, **kwargs )
#
# 		return LazyResult( supplier )
#
# 	@classmethod
# 	def of( cls, value ):
# 		if not hasattr( value, "__call__" ):
# 			return LazyResult( lambda: value )
# 		return LazyResult( value )
