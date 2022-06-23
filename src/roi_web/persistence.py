from __future__ import annotations

import asyncio
import os
import pathlib
import pickle
import sqlite3
from dataclasses import dataclass
from typing import Iterable, Mapping, AsyncIterable

import aiofiles
from warcio import ArchiveIterator, WARCWriter

from roi_utils import Result
from . import TabSeparated, WebArchive, Digestable, PageContent
from .domain import String, UrlEvent

WEB_STREAM_FILEPATH = os.environ.get( "GNOSIS_WEB_STREAM", "C:/Users/Mateus/OneDrive/gnosis/limni/lists/stream/articles.tsv" )
DEFAULT_STREAM_PATH = pathlib.Path( WEB_STREAM_FILEPATH )

WEB_RAW_FILEPATH = os.environ.get( "GNOSIS_RAW_PATH", "C:/Users/Mateus/Desktop/files" )
DEFAULT_RAW_PATH = pathlib.Path( WEB_RAW_FILEPATH ) / "raw"
WEB_PROCESSED_PATH = os.environ.get( "GNOSIS_PROCESSED_PATH", "C:/Users/Mateus/Desktop/files" )
DEFAULT_ENRICHMENT_PATH = pathlib.Path( WEB_PROCESSED_PATH ) / "processed"

WEB_FAIL_PATH = os.environ.get( "GNOSIS_FAIL_PATH", "C:/Users/Mateus/Desktop/files" )
DEFAULT_FAIL_PATH = pathlib.Path( WEB_FAIL_PATH ) / "fail"


@dataclass
class Execution:
	url: String
	status: String
	datetime: String
	content_path: String

	@classmethod
	def of( cls, row ) -> Execution:
		return Execution()


class Sql:
	QUERY_CREATE_MAIN = '''
		create table if not exists url_exec (
		url not null string,
		status not null string,
		content_path null string,
		datetime not null string	
		)
	'''

	def __init__( self, datbase_location: String ):
		self.database_location = datbase_location
		self.con = None

	def __enter__( self ):
		con = sqlite3.connect( self.database_location )
		con.execute( self.QUERY_CREATE_MAIN )
		self.con = con
		return self

	def last_executions( self ):
		cursor = self.con.cursor()
		cursor.execute( "select * from url_exec where status not like 'OK'" )
		rows = cursor.fetchall()
		return { Execution.of( row ) for row in rows }


sql = Sql( WEB_RAW_FILEPATH )


def _dump_to( base_path: pathlib.Path, obj: Digestable ):
	base_path.parent.mkdir( parents = True, exist_ok = True )

	if base_path.exists():
		base_path.unlink()

	with base_path.open( "wb" ) as file:
		pickle.dump( obj, file )
		print( "Serialized!" )


def load_from( filename: pathlib.Path, ) -> Mapping:
	with filename.open( "rb" ) as file:
		return pickle.load( file )


def load_stream( filepath = None ) -> Iterable[ TabSeparated ]:
	filepath = filepath or str( DEFAULT_STREAM_PATH )
	con = sqlite3.connect( filepath )

	with open( filepath, "r" ) as file:
		for i, content in enumerate( file.readlines() ):
			if i > 0:
				yield content


def load_archive_async( url: UrlEvent, base_path: pathlib.Path = None ) -> Result[ WebArchive ]:
	base_path = base_path or DEFAULT_RAW_PATH
	file_name = base_path / url.digest()
	try:
		with open( str( file_name ), "rb" ) as file:
			contents = [ archive for archive in ArchiveIterator( file )]
			return Result.ok( WebArchive( url = url , content =  contents) )
	except Exception as e:
		return Result.failure( e )


def load_archive( file_name: String, base_path: pathlib.Path = None ) -> Result[ WebArchive ]:
	base_path = base_path or DEFAULT_RAW_PATH
	file_name = base_path / file_name
	try:
		res = (load_from( file_name ))
		print( "Loaded Response" )
		return Result.ok( res )
	except Exception as e:
		return Result.failure( e )


def save_response( info: WebArchive, base_path: pathlib.Path = None ) -> None:
	print( "Persisting Response" )
	base_path = base_path or DEFAULT_RAW_PATH
	path = base_path / info.digest()
	_dump_to( path, info )


def save_response_async( info: WebArchive ,base_path: pathlib.Path = None ) -> None:

	print( f"{	info.digest() } Starting Persisting Response" )
	base_path = base_path or DEFAULT_RAW_PATH
	path = base_path / info.digest()
	try:

		with open( str( path ), "wb" ) as file:
			writer = WARCWriter( file, gzip = True)
			for record in info.content:
				writer.write_record( record )

			print( f"{	info.digest() } Finished Persisting Response" )
	except Exception as e:
		print( f"{	info.digest() } error Persisting Response: {str( e )}" )




def save_processed( content: PageContent, base_path: pathlib.Path = None ) -> None:
	print( "Persisting Processed" )
	base_path = base_path or DEFAULT_ENRICHMENT_PATH
	path = base_path / content.digest()
	_dump_to( path, content )


def save_errors( ex: Exception ) -> None:
	print( "Persisting Errors" )
	if False:
		_dump_to( DEFAULT_FAIL_PATH, { "message": ex.args, } )
