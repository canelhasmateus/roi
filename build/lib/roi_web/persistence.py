import os
import pathlib
import pickle
from typing import Iterable, Mapping

from roi_utils import Result
from . import TabSeparated, ResponseInfo, Digestable, PageContent
from .domain import String

WEB_STREAM_FILEPATH = os.environ.get( "GNOSIS_WEB_STREAM", "C:/Users/Mateus/OneDrive/gnosis/limni/lists/stream/articles.tsv" )
DEFAULT_STREAM_PATH = pathlib.Path( WEB_STREAM_FILEPATH )

WEB_RAW_FILEPATH = os.environ.get( "GNOSIS_RAW_PATH", "C:/Users/Mateus/Desktop/files" )
DEFAULT_RAW_PATH = pathlib.Path( WEB_RAW_FILEPATH ) / "raw"
WEB_PROCESSED_PATH = os.environ.get( "GNOSIS_PROCESSED_PATH", "C:/Users/Mateus/Desktop/files" )
DEFAULT_ENRICHMENT_PATH = pathlib.Path( WEB_PROCESSED_PATH ) / "processed"

WEB_FAIL_PATH = os.environ.get( "GNOSIS_FAIL_PATH", "C:/Users/Mateus/Desktop/files" )
DEFAULT_FAIL_PATH = pathlib.Path( WEB_FAIL_PATH ) / "fail"


def _dump_to( base_path: pathlib.Path, obj: Digestable ):

	base_path.parent.mkdir( parents = True, exist_ok = True )

	if base_path.exists():
		base_path.unlink()



	with base_path.open( "wb") as file:
		pickle.dump( obj, file )
		print( "Serialized!" )


def load_from( filename: pathlib.Path ) -> Mapping:
	with filename.open("rb") as file:
		return pickle.load( file )


def load_stream( filepath = None ) -> Iterable[ TabSeparated ]:
	filepath = filepath or str( DEFAULT_STREAM_PATH )
	with open( filepath, "r" ) as file:
		for i, content in enumerate( file.readlines() ):
			if i > 0:
				yield content


def load_response( file_name : String, base_path: pathlib.Path = None ) -> Result[ ResponseInfo ]:
	base_path = base_path or DEFAULT_RAW_PATH
	file_name = base_path / file_name
	try:
		res = ResponseInfo.from_dict( load_from( file_name ) )
		print( "Loaded Response" )
		return Result.ok( res )
	except Exception as e:
		return Result.failure( e )


def save_response( info: ResponseInfo, base_path: pathlib.Path = None ) -> None:
	print( "Persisting Response" )
	base_path = base_path or DEFAULT_RAW_PATH
	path = base_path / info.digest()
	_dump_to(path, info )


def save_processed( content: PageContent, base_path: pathlib.Path = None ) -> None:
	print( "Persisting Processed" )
	base_path = base_path or DEFAULT_ENRICHMENT_PATH
	path = base_path / content.digest()
	_dump_to( path, content )


def save_errors( ex: Exception ) -> None:
	print( "Persisting Errors" )
	if False:
		_dump_to( DEFAULT_FAIL_PATH, { "message": ex.args, } )
