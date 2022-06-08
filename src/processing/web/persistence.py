import os
import pathlib
import pickle
import random
from typing import Iterable

from src.processing.web.domain import TabSeparated, UrlEvent, ResponseInfo, RichResponse, Digestable
from src.utils.monad import Result

WEB_STREAM_FILEPATH = os.environ.get( "GNOSIS_WEB_STREAM", "" )
DEFAULT_STREAM_PATH = pathlib.Path( WEB_STREAM_FILEPATH )

WEB_RAW_FILEPATH = os.environ.get( "GNOSIS_RAW_PATH", "" )
DEFAULT_RAW_PATH = pathlib.Path( WEB_RAW_FILEPATH ) / "raw"

WEB_PROCESSED_PATH = os.environ.get( "GNOSIS_PROCESSED_PATH", "" )
DEFAULT_PROCESSED_PATH = pathlib.Path( WEB_PROCESSED_PATH ) / "processed"

WEB_FAIL_PATH = os.environ.get( "GNOSIS_FAIL_PATH", "" )
DEFAULT_FAIL_PATH = pathlib.Path( WEB_FAIL_PATH ) / "fail"


def _pickle_to( base_path: pathlib.Path, obj: Digestable ):
	base_path.mkdir( parents = True, exist_ok = True )
	filename = base_path / obj.digest()
	with open( str( filename ), "wb" ) as file:
		pickle.dump( obj, file )
		print( "Pickled!" )


def _pickle_from( filename: pathlib.Path ):
	with open( str( filename ), "rb" ) as file:
		return pickle.load( file )


def load_stream( filepath = None ) -> Iterable[ TabSeparated ]:
	filepath = filepath or str( DEFAULT_STREAM_PATH )
	with open( filepath, "r" ) as file:
		for i, content in enumerate( file.readlines() ):
			if i > 0:
				yield content

def load_response( url: UrlEvent, base_path: pathlib.Path = None ) -> Result[ ResponseInfo ]:
	base_path = base_path or DEFAULT_RAW_PATH
	file_name = base_path / url.digest()
	try:
		res = _pickle_from( file_name )
		print( "Loaded Response" )
		return Result.ok( res )
	except Exception as e:
		return Result.failure( e )


def save_response( info: ResponseInfo, base_path: pathlib.Path = None ) -> None:
	print( "Persisting Response" )
	base_path = base_path or DEFAULT_RAW_PATH
	_pickle_to( base_path, info )


def save_content( content: RichResponse, base_path: pathlib.Path = None ) -> None:
	print( "Persisting Processed" )
	base_path = base_path or DEFAULT_PROCESSED_PATH
	_pickle_to( base_path, content )


def save_errors( ex: Exception ) -> None:
	print( "Persisting Errors" )

	_pickle_to( DEFAULT_FAIL_PATH, { "message": ex.args, } )
