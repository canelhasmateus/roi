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


from src.processing.web.domain import ResponseInfo, UClean, Url, PageInfo
from src.processing.web.logic import default_url_parser, default_fetcher, default_content_parser
from src.processing.web.persistence import save_articles_response, read_articles_tsv, save_article_content, read_articles_response


@task
def readData() -> List[ Url[ UClean ] ]:

	result = [ ]
	parse = default_url_parser()
	for i, line in enumerate( read_articles_tsv( ) ):
		if i != 0:
			time, kind, url = line.split( "\t" )
			parse( url ).map( result.append )
	return result




@task
def fetchResponse( url: Url[ ... ] ) -> ResponseInfo:

	cached = read_articles_response( url )
	return cached.orElse( lambda x : default_fetcher()( url ).unwrap())

@task
def persistRaw( info: ResponseInfo ) -> None:
	save_articles_response( info )

@task
def parseContent( content: ResponseInfo ) -> PageInfo:
	parser = default_content_parser()
	return parser( content ).unwrap()

@task
def persistContent( content: PageInfo ) -> None:
	save_article_content( content)

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
