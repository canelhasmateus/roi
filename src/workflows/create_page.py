import json
import os
import pathlib
import random
import subprocess
import time
import urllib
import urllib.parse
from typing import Iterable, Dict, List

import boto3 as boto3

from roi_web import PageContent
from roi_web.processing import load_processed


def append( l , v ):
    l.append( v )
    return l
def write_to( path ):
    return open( path ,  "w")

def read_from( path ):
    return open( path, "rb")

def dump_json( f, content : List[ Dict ]):
    if not content:
        raise Exception(f"Writing to { f.name }, but content was empty. ")

    json.dump( content, f, indent=2 )
    print(f"Wrote { len(content) } content entries to { f.name }.")


def partition_by( itr, key_fn, value_fn = lambda x : x ):
    res = {}
    for el in itr:
        key        = key_fn( el )
        value      = value_fn( el )
        partition  = res.get( key, [ ] )
        res[ key ] = append( partition, value )

    return res
def content_key( content: PageContent):
    return content.visit_kind
def content_dict( content: PageContent ):
    hostname = urllib.parse.urlparse( content.url ).hostname,

    return {
        "url"       : content.url,
        "visit_date": content.visit_date,
        "visit_kind": content.visit_kind,
        "title"     : content.title,
        "duration"  : content.duration,
        "date"      : content.date,
        "image"     : content.image,
        "domain"    : hostname,
        "author"    : content.author or hostname or content.url
    }


def invalidate( distribution_id ):
    reference = str( time.time() ).replace( ".", "" )

    cf  = boto3.client( 'cloudfront' )
    res = cf.create_invalidation( DistributionId=distribution_id,
                                  InvalidationBatch={
                                      'CallerReference': reference,
                                      'Paths': {
                                          'Quantity': 1,
                                          'Items': [ '/*' ]
                                      }
                                  })

    return res[ 'Invalidation' ][ 'Id' ]


def upload_file( file, bucket, object_name ):
    print("Uploading site HTML to S3.")

    s3_client = boto3.client( 's3' )
    return s3_client.upload_fileobj( file,
                                     bucket,
                                     object_name,
                                     ExtraArgs={'ContentType': 'text/html'} )


def main():
    partitions = partition_by( load_processed(), content_key, content_dict )
    to_read    = random.choices( partitions[ "Queue" ], k=50 )
    to_use     = random.choices( partitions[ "Tool" ], k=20 )

    akti_path  = pathlib.Path( os.environ[ "AKTI_PATH" ] )
    assets     = akti_path / "src/assets"

    with write_to( assets  / "tool.json" ) as tools:
        dump_json( tools, to_use )

    with write_to( assets  / "queue.json" ) as previews:
        dump_json( previews, to_read )

    subprocess.run( rf"cd {akti_path} && npm run build", shell=True )
    with read_from( akti_path / "dist/index.html" ) as dist:

        akti_distribution = os.environ[ "AKTI_DISTRIBUTION" ]
        akti_bucket       = os.environ[ "AKTI_BUCKET" ]
        invalidation_id   = invalidate( akti_distribution )

        upload_file( dist, akti_bucket, "index.html" )
        print( f"invalidationId = { invalidation_id }" )



if __name__ == "__main__":
    main()
