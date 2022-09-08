import json
import os
import pathlib
import random
import subprocess
import time
import urllib
import urllib.parse

import boto3 as boto3

from roi_web import PageContent
from roi_web.processing import load_processed


def create_invalidation( distribution_id ):
    cf = boto3.client( 'cloudfront' )
    reference = str( time.time() ).replace( ".", "" )
    res = cf.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            'Paths': {
                'Quantity': 1,
                'Items': [
                    '/*'
                ]
            },
            'CallerReference': reference
        }
    )
    invalidation_id = res[ 'Invalidation' ][ 'Id' ]
    print( f"invalidationId = {invalidation_id}" )


def upload_file( file, bucket, object_name ):
    # Upload the file
    s3_client = boto3.client( 's3' )
    response = s3_client.upload_fileobj( file, bucket, object_name,
                                         ExtraArgs={
                                             'ContentType': 'text/html'
                                         } )


def asdict( content: PageContent ):
    dic = content.dict()
    hostname = urllib.parse.urlparse( content.url ).hostname
    author = content.author or hostname or content.url

    dic[ "domain" ] = hostname
    dic[ "author" ] = author
    del dic[ "text" ]
    del dic[ "tags" ]
    del dic[ "categories" ]
    del dic[ "comments" ]
    del dic[ "neighbors" ]

    return dic


def main():
    queue = [ ]
    tool = [ ]
    for el in load_processed():
        d = asdict( el )
        match el.visit_kind:
            case "Tool":
                tool.append( d )
            case "Queue":
                queue.append( d )

    previews = random.choices( queue, k=50 )
    sidebar = random.choices( tool, k=20 )

    akti_distribution = os.environ[ "AKTI_DISTRIBUTION" ]
    akti_bucket = os.environ[ "AKTI_BUCKET" ]
    akti_path = pathlib.Path( os.environ[ "AKTI_PATH" ] )

    with open( akti_path / "src/assets/queue.json", "w" ) as f:
        json.dump( previews, f, indent=2 )

    with open( akti_path / "src/assets/tool.json", "w" ) as f:
        json.dump( sidebar, f, indent=2 )

    process = subprocess.run( rf"cd {akti_path} && npm run build", shell=True )
    with open( akti_path / r"dist/index.html", "rb" ) as dist:
        upload_file( dist, akti_bucket, "index.html" )

        create_invalidation( akti_distribution )


if __name__ == "__main__":
    main()
