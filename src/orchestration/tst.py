import lxml.etree
import os
import pathlib
import pickle
import time
import re

import requests

WEB_PROCESSED_PATH = os.environ.get( "GNOSIS_PROCESSED_PATH", "" )
DEFAULT_PROCESSED_PATH = pathlib.Path( WEB_PROCESSED_PATH ) / "raw"

for file in DEFAULT_PROCESSED_PATH.glob("*"):

	filepath = str( file )
	obj = pickle.load( open( filepath , "rb"))
	if 'youtube' in obj.url.raw:

		id = re.search(  r"v=([a-zA-Z0-9]+(?=\b|&))", obj.url.query ).groups()
		response = requests.get( "https://youtubetranscript.com/" , params = { "server_vid" : id})
		root = lxml.etree.fromstring( obj.content.decode())
		text = " ".join( root.itertext() )
		if text == 'Error: transcripts disabled for that video':
			continue

		time.sleep( 1 )




