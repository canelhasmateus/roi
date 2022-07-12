from __future__ import annotations

import pathlib
from typing import Protocol

import aiofiles

from roi_utils import Result



class Jsonable( Protocol ):
	def json( self ) -> str:
		...


async def load_async( file_name: pathlib.Path ) -> Result[ bytes ]:

	if not file_name.exists():
		return Result.failure( Exception( "File not found " ) )

	try:
		async with aiofiles.open( str( file_name ), "rb" ) as file:
			content = await file.read()
			return Result.ok( content )
	except Exception as e:
		return Result.failure( e )


async def save_async( obj: Jsonable, path: pathlib.Path ) -> None:
	fullPath = str( path )

	content = obj.json()
	async with aiofiles.open( fullPath, "w" ) as file:
		await file.write( content )



