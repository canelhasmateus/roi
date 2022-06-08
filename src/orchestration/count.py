import os
from typing import Iterable

from apache_beam.io.textio import ReadFromText
import apache_beam as beam

from src.processing.web.domain import String, TabSeparated, Url, UClean, ResponseInfo, PageInfo
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


def parseResponse( content: ResponseInfo ) -> PageInfo:
	parser = default_content_parser()
	return parser( content ).orElse( None )


def persistProcessed( content: PageInfo ) -> None:
	save_article_content( content )


if __name__ == '__main__':
	base_source = os.environ.get( "GNOSIS_WEB_STREAM", "" )
	with beam.Pipeline( options = None ) as p:
		raw = (p
		       | "Load Data" >> ReadFromText( base_source, skip_header_lines = 1 )
		       | "Parse Url" >> beam.Map( lambda x: parse_url( x ) )
		       | "Parse domain" >> beam.Map( lambda x: (x.map( lambda y : ".".join(y.hostname.split(".")[-2:])).orElse( None ) , x))
		       | "Count" >> beam.combiners.Count.PerKey(  )

		       | beam.Map( print )
		       )


# (raw
#  | "Process Raw" >> beam.FlatMap( lambda x: parseResponse( x ) )
#  | "Persist Processed" >> beam.FlatMap( lambda x: persistProcessed( x ) )
#  )
