import os

import apache_beam as beam
from apache_beam.io.textio import ReadFromText
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.runners.interactive.interactive_runner import InteractiveRunner
from apache_beam.testing.test_pipeline import TestPipeline

from src.processing.web.processing import parseUrl, fetchResponse, parseResponse, persistProcessed

if __name__ == '__main__':
	base_source = os.environ.get( "GNOSIS_WEB_STREAM", "" )
	opts = PipelineOptions()
	with TestPipeline( runner = InteractiveRunner(), options = None ) as p:
		raw = (p
		       | "Load Data" >> ReadFromText( base_source, skip_header_lines = 1 )
		       | "Parse Url" >> beam.Map( lambda x: parseUrl( x ) )
		       | "Fetch Response" >> beam.Map( lambda x: x.flatMap( fetchResponse ) )
		       )
		# raw | "Persist Raw" >> beam.FlatMap( lambda x: persistRaw( x ) )

		(raw
		 | "Process Raw" >> beam.Map( lambda x: x.flatMap( parseResponse ) )
		 | "Persist Processed" >> beam.Map( lambda x: persistProcessed( x ) )
		 )
