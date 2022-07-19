from __future__ import annotations

import pathlib
from typing import Protocol

import aiofiles


class Jsonable( Protocol ):
	def json( self ) -> str:
		...


async def load_async( file_name: pathlib.Path ) -> bytes:
	# async with AIOFile( str(file_name) , "rb") as file:
	async with aiofiles.open( str( file_name ), "rb" ) as file:
		content = await file.read()
		return content


async def save_async( obj: Jsonable, path: pathlib.Path ) -> None:
	async with aiofiles.open( str( path ), "w" ) as file:
		content = obj.json()
		if content:
			await file.write( content )
		else:
			raise Exception( "Empty content!" )
