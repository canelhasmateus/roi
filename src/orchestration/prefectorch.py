from __future__ import annotations

import hashlib
import os
import pathlib
import pickle
import time
from typing import List

from prefect import task, Flow
from prefect.engine.signals import SKIP
from prefect.executors import LocalDaskExecutor

from src.persistence.filesystem import read_articles_tsv, check_articles_processed, save_articles_response, save_article_content
from src.processing.web.domain import ResponseInfo, UClean, Url, PageInfo
from src.processing.web.logic import default_url_parser, default_fetcher, default_content_parser

WEB_STREAM_FILEPATH = os.environ[ "GNOSIS_WEB_STREAM" ]
WEB_CONTENT_FILEPATH = os.environ[ "GNOSIS_RESPONSE_PATH" ]
@task
def readData() -> List[ Url[ UClean ] ]:

	result = [ ]
	parse = default_url_parser()
	for i, line in enumerate( read_articles_tsv( WEB_STREAM_FILEPATH ) ):
		if i != 0:
			time, kind, url = line.split( "\t" )
			parse( url ).map( result.append )
	return result




@task
def fetchResponse( url: Url[ ... ] ) -> ResponseInfo:

	fetch_url = default_fetcher()
	name = hashlib.md5( url.raw.encode() ).digest().hex()
	cached_file = pathlib.Path( WEB_CONTENT_FILEPATH ) / "raw" / name
	if cached_file.exists():
		with open( str( cached_file) , "rb") as file:
			res = pickle.load( file )
	else:
		res = fetch_url( url ).unwrap()
	return res

@task
def persistRaw( info: ResponseInfo ) -> None:
	save_articles_response( WEB_CONTENT_FILEPATH, info )

@task
def parseContent( content: ResponseInfo ) -> PageInfo:
	parser = default_content_parser()
	return parser( content ).unwrap()



@task
def persistContent( content: PageInfo ) -> None:
	save_article_content( WEB_CONTENT_FILEPATH , content)

with Flow( "Hello-Flow" ) as flow:

	data = readData()
	infos = fetchResponse.map( data )
	persistRaw.map( infos )

	processed = parseContent.map( infos )
	persistContent.map( processed )

finish_planning = time.time()
flow.executor = LocalDaskExecutor( scheduler = "threads" , num_workers = 5)
flow.run()
finish = time.time()
