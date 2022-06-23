import os

import apache_beam as beam
from apache_beam import ParDo, DoFn
from apache_beam.io.textio import ReadFromText
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.testing.test_pipeline import TestPipeline

from roi_utils import Result
from roi_web import baseParseUrl, fetchResponseBase, baseProcessResponse, basePersistProcessed, persistResponseBase, UrlEvent, WebArchive


class WebFetcher( DoFn ):

	async def process( self, element : Result[ UrlEvent ], *args, **kwargs ) -> Result[ WebArchive ]:

		...

	def setup(self):
		...

	def teardown( self ):
		...

	def finish_bundle(self):
		...

	def start_bundle(self):
		...


async def main():
	base_source = os.environ.get( "GNOSIS_WEB_STREAM", "" )
	opts = PipelineOptions()
	with TestPipeline() as p:
		raw = (p
		       | "Load Data" >> ReadFromText( base_source, skip_header_lines = 1 )
		       | "Parse Url" >> beam.Map( lambda x: baseParseUrl( x ) )
		       | "Fetch Response" >> beam.Map( lambda x: x.flatMap( fetchResponseBase ) )
		       )
		raw | "Persist Raw" >> beam.FlatMap( lambda x: persistResponseBase( x ) )

		# (raw
		#  | "Process Raw" >> beam.Map( lambda x: x.flatMap( baseProcessResponse ) )
		#  | "Persist Processed" >> beam.Map( lambda x: basePersistProcessed( x ) )
		#  )


if __name__ == '__main__':
	import asyncio
	asyncio.run( main() )
