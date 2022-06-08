import hashlib
import os
import pathlib
import random
from typing import Iterable, Any
import pickle
from src.processing.web.domain import TabSeparated, Url, ResponseInfo, PageInfo, String, PageException
from src.utils.monad import Result

WEB_STREAM_FILEPATH = os.environ.get( "GNOSIS_WEB_STREAM", "" )
DEFAULT_STREAM_PATH = pathlib.Path( WEB_STREAM_FILEPATH )

WEB_RAW_FILEPATH = os.environ.get( "GNOSIS_RAW_PATH", "" )
DEFAULT_RAW_PATH = pathlib.Path( WEB_RAW_FILEPATH ) / "raw"

WEB_PROCESSED_PATH = os.environ.get( "GNOSIS_PROCESSED_PATH", "" )
DEFAULT_PROCESSED_PATH = pathlib.Path( WEB_PROCESSED_PATH ) / "processed"

WEB_FAIL_PATH = os.environ.get( "GNOSIS_FAIL_PATH", "" )
DEFAULT_FAIL_PATH = pathlib.Path( WEB_FAIL_PATH ) / "fail"


def read_articles_tsv( filepath = None ) -> Iterable[ TabSeparated ]:
	filepath = filepath or str( DEFAULT_STREAM_PATH )

	with open( filepath, "r" ) as file:
		for content in file.readlines():
			yield content


def read_articles_response( url: Url, base_path: pathlib.Path = None ) -> Result[ ResponseInfo ]:
	base_path = base_path or DEFAULT_RAW_PATH
	name = url.digest()
	hashlib.md5( url.raw.encode() ).digest().hex()
	cachedResponse = base_path / name
	if not cachedResponse.exists():
		return Result.failure( FileNotFoundError( "Cached Response does not exist for url ", url.raw ) )
	try:
		with open( str( cachedResponse ), "rb" ) as file:
			res = pickle.load( file )
			return Result.ok( res )

	except Exception as e:
		return Result.failure( e )


def _pickle_to( base_path: pathlib.Path, filename: String, obj: Any ):
	base_path.mkdir( parents = True, exist_ok = True )
	filename = base_path / filename
	with open( str( filename ), "wb" ) as file:
		pickle.dump( obj, file )
		print( "Pickled!" )


def save_articles_response( info: ResponseInfo, base_path: pathlib.Path = None ) -> None:
	print( "Persisting Data" )
	base_path = base_path or DEFAULT_RAW_PATH
	name = hashlib.md5( info.url.raw.encode() ).digest().hex()
	_pickle_to( base_path, name, info )


def save_article_content( content: PageInfo, base_path: pathlib.Path = None ) -> None:
	print( "Persisting Processed" )

	base_path = base_path or DEFAULT_PROCESSED_PATH
	name = hashlib.md5( content.url.raw.encode() ).digest().hex()
	_pickle_to( base_path, name, content )


def save_errors( ex: PageException ) -> None:
	print( "Persisting Errors" )
	name = str( random.randint( 1, 9999999 ) )
	_pickle_to( DEFAULT_FAIL_PATH, name, {
			"message": ex.args, } )
