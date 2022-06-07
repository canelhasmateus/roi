import hashlib
import pathlib
from typing import Iterable
import pickle
from src.processing.web.domain import TabSeparated, Url, ResponseInfo, PageInfo


def read_articles_tsv( filepath ) -> Iterable[ TabSeparated ]:
	with open( filepath, "r" ) as file:
		for content in file.readlines():
			yield content


def check_articles_processed( base_path, url: Url[ ... ] ) -> bool:

	if filename.exists():
		return True
	return False


def save_articles_response( base_path, info: ResponseInfo ) -> None:
	url = info.url
	name = hashlib.md5( url.raw.encode() ).digest().hex()
	filename = pathlib.Path( base_path ) / "raw" / name
	if not filename.exists():
		filename.parent.mkdir( parents = True , exist_ok = True)
		with open( str( filename ), "wb" ) as file:
			pickle.dump( info, file )

def save_article_content( base_path, content : PageInfo ) -> None:
	url = content.url
	name = hashlib.md5( url.raw.encode() ).digest().hex()
	filename = pathlib.Path( base_path ) / "content" / name
	filename.parent.mkdir( parents = True , exist_ok = True)
	with open( str( filename ), "wb" ) as file:
		pickle.dump( content, file )

