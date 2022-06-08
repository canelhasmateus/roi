import os

import apache_beam as beam
from apache_beam.io.textio import ReadFromText

from src.processing.web.domain import TabSeparated, Url, UClean, ResponseInfo, PageInfo
from src.processing.web.logic import default_url_parser, default_fetcher, default_content_parser
from src.processing.web.persistence import read_articles_response, save_articles_response, save_article_content, save_errors
from src.utils.monad import Result


def parse_url( line: TabSeparated ) -> Result[ Url[ UClean ] ]:
	parser = default_url_parser()
	return parser( line )


def fetch_response( url: Url ) -> Result[ ResponseInfo ]:
	fetcher = default_fetcher()

	cached = read_articles_response( url )
	if cached.is_success():
		print( "Cached!" )
		return cached

	print( "Fetching from web." )
	return fetcher( url )


def persistRaw( info: Result[ ResponseInfo ] ) -> None:
	(info
	 .map( save_articles_response )
	 .recover( save_errors )
	 )


def parseResponse( content: ResponseInfo ) -> Result[ PageInfo ]:
	print( "Processing content!" )
	parser = default_content_parser()
	return parser( content )


def persistProcessed( content: Result[ PageInfo ] ) -> None:
	(content
	 .map( save_article_content )
	 .recover( save_errors ))



if __name__ == '__main__':
	base_source = os.environ.get( "GNOSIS_WEB_STREAM", "" )
	with beam.Pipeline( options = None ) as p:
		raw = (p
		       | "Load Data" >> ReadFromText( base_source, skip_header_lines = 1 )
		       | "Parse Url" >> beam.Map( lambda x: parse_url( x ) )
		       | "Fetch Response" >> beam.Map( lambda x: x.flatMap( fetch_response ) )
		       )
		# raw | "Persist Raw" >> beam.FlatMap( lambda x: persistRaw( x ) )

		(raw
		 | "Process Raw" >> beam.Map( lambda x: x.flatMap( parseResponse ) )
		 | "Persist Processed" >> beam.Map( lambda x: persistProcessed( x ) )
		 )
