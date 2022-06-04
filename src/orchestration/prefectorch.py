from prefect import task, Flow, Task

from src.processing.web.domain import PageInfo, String
from src.processing.web.logic import UrlParser, UrlFetcher, ContentParser


@task
def read_data( x ):
	return [
			"http://akira.ruc.dk/~keld/research/LKH/LKH-1.3/DOC/LKH_REPORT.pdf",
			"https://hirrolot.github.io/posts/rust-is-hard-or-the-misery-of-mainstream-programming.html"
	]


@task
def fetchRaw( url: String ):
	fetch = UrlFetcher()
	parse = UrlParser()
	return (parse( url )
	        .flatMap( fetch )
	        .unwrap())


@task
def persistRaw( info: PageInfo ):
	print( "persistRaw" )


@task
def parseContent( content: PageInfo ):
	parser = ContentParser()
	p = parser( content ).unwrap()
	print( p )
	return p


with Flow( "Hello-Flow" ) as flow:
	data = read_data( "" )
	infos = fetchRaw.map( data )

	persistRaw.map( infos )
	parseContent.map( infos )

flow.run()
