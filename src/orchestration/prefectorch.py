from __future__ import annotations

import os
import time
from typing import List

from prefect import task, Flow
from prefect.engine.signals import SKIP

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
def checkDone( url: Url[ UClean ] ) -> Url[ UClean ]:

	processed = check_articles_processed( WEB_CONTENT_FILEPATH, url )
	if processed:
		raise SKIP( "Already fetched this url" )

	return url

@task
def fetchResponse( url: Url[ ... ] ) -> ResponseInfo:
	fetch_url = default_fetcher()
	return fetch_url( url ).unwrap()

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
	pending = checkDone.map( data )

	infos = fetchResponse.map( pending )
	persistRaw.map( infos )

	processed = parseContent.map( infos )
	persistContent.map( processed )

finish_planning = time.time()
flow.run()
finish = time.time()
