from prefect import task, Flow, Task

from src.persistence.filesystem import read_articles_tsv
from src.processing.web.domain import ResponseInfo, String
from src.processing.web.logic import UrlParser, WebFetcher, ContentParser, default_url_parser, default_fetcher, default_response_parser


@task
def read_data():
	filepath = ""
	return read_articles_tsv( filepath )


@task
def fetchRaw( url: String ) -> ResponseInfo:
	parse_url = default_url_parser()
	fetch_url = default_fetcher()
	parse_response = default_response_parser()
	return (parse_url( url )
	        .flatMap( fetch_url )
	        .flatMap( parse_response )
	        .unwrap())


@task
def persistRaw( info: ResponseInfo ):
	print( "persistRaw" )


@task
def parseContent( content: ResponseInfo ):
	default_response_parser()
	parser = ContentParser()
	p = parser( content ).unwrap()
	print( p )
	return p


with Flow( "Hello-Flow" ) as flow:
	data = read_data()
	infos = fetchRaw.map( data )

	persistRaw.map( infos )
	parseContent.map( infos )

flow.run()
