import json
import random
import subprocess
import urllib
import urllib.parse

from roi_web import PageContent
from roi_web.processing import load_processed


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

    with open( r"C:\Users\Mateus\OneDrive\gnosis\akti\src\assets\queue.json", "w" ) as f:
        json.dump( previews, f, indent=2 )
    with open( r"C:\Users\Mateus\OneDrive\gnosis\akti\src\assets\tool.json", "w" ) as f:
        json.dump( sidebar, f, indent=2 )

    process = subprocess.run( r"cd C:\Users\Mateus\OneDrive\gnosis\akti && npm run build", shell=True )


if __name__ == "__main__":
    main()
