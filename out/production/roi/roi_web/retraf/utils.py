# pylint:disable-msg=E0611,I1101
"""
Module bundling functions related to HTML and text processing.
"""

## This file is available from https://github.com/adbar/trafilatura
## under GNU GPL v3 license

# import csv
import logging
import re
from gzip import decompress
from html import unescape

from unicodedata import normalize

# CChardet is faster and can be more accurate
try:
    from cchardet import detect as cchardet_detect
except ImportError:
    cchardet_detect = None

from lxml.html import HtmlElement, HTMLParser, fromstring
# from lxml.html.soupparser import fromstring as fromsoup

# response types
from urllib3.response import HTTPResponse

LOGGER = logging.getLogger( __name__ )

UNICODE_ALIASES = {'utf-8', 'utf_8'}

# note: htmldate could use HTML comments
# huge_tree=True, remove_blank_text=True
HTML_PARSER = HTMLParser( collect_ids=False, default_doctype=False, encoding='utf-8', remove_comments=True, remove_pis=True )

SPACES_TABLE = {
    c: ' ' for c in ('\u00A0', '\u1680', '\u2000', '\u2001', '\u2002', '\u2003',
                     '\u2004', '\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200a', '\u2028',
                     '\u2029', '\u202F', '\u205F', '\u3000')
}

NO_TAG_SPACE = re.compile( r'(?<![p{P}>])\n' )
SPACE_TRIMMING = re.compile( r'\s+', flags=re.UNICODE | re.MULTILINE )

# Regex to check image file extensions
IMAGE_EXTENSION = re.compile( r'[^\s]+\.(avif|bmp|gif|hei[cf]|jpe?g|png|webp)(\b|$)' )

AUTHOR_PREFIX = re.compile( r'^([a-zäöüß]+(ed|t))? ?(written by|words by|words|by|von) ', flags=re.IGNORECASE )
AUTHOR_REMOVE_NUMBERS = re.compile( r'\d.+?$' )
AUTHOR_TWITTER = re.compile( r'@[\w]+' )
AUTHOR_REPLACE_JOIN = re.compile( r'[._+]' )
AUTHOR_REMOVE_NICKNAME = re.compile( r'["‘({\[’\'][^"]+?[‘’"\')\]}]' )
AUTHOR_REMOVE_SPECIAL = re.compile( r'[^\w]+$|[:()?*$#!%/<>{}~]' )
AUTHOR_REMOVE_PREPOSITION = re.compile( r'\b\s+(am|on|for|at|in|to|from|of|via|with|—|-)\s+(.*)', flags=re.IGNORECASE )
AUTHOR_EMAIL = re.compile( r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b' )
AUTHOR_SPLIT = re.compile( r'/|;|,|\||&|(?:^|\W)[u|a]nd(?:$|\W)', flags=re.IGNORECASE )
AUTHOR_EMOJI_REMOVE = re.compile(
    "["u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF" u"\U0001F680-\U0001F6FF" u"\U0001F1E0-\U0001F1FF"
    u"\U00002500-\U00002BEF" u"\U00002702-\U000027B0" u"\U000024C2-\U0001F251"
    u"\U0001f926-\U0001f937" u"\U00010000-\U0010ffff" u"\u2640-\u2642" u"\u2600-\u2B55" u"\u200d"
    u"\u23cf" u"\u23e9" u"\u231a" u"\ufe0f" u"\u3030" "]+", flags=re.UNICODE )

CLEAN_META_TAGS = re.compile( r'["\']' )


def handle_gz_file( filecontent ):
    """Tell if a file's magic number corresponds to the GZip format
       and try to decode it"""
    # source: https://stackoverflow.com/questions/3703276/how-to-tell-if-a-file-is-gzip-compressed
    if isinstance( filecontent, bytes ) and filecontent[ :2 ] == b'\x1f\x8b':
        # decode GZipped data
        try:
            filecontent = decompress( filecontent )
        except (EOFError, OSError):
            logging.warning( 'invalid GZ file' )
    return filecontent



def remove_control_characters( string ):
    '''Prevent non-printable and XML invalid character errors'''
    return ''.join( [ c for c in string if c.isprintable() or c.isspace() ] )


def normalize_unicode( string, unicodeform='NFC' ):
    'Normalize the given string to the specified unicode format.'
    return normalize( unicodeform, string )



def line_processing( line ):
    '''Remove HTML space entities, then discard incompatible unicode
       and invalid XML characters on line level'''
    # spacing HTML entities: https://www.w3.org/MarkUp/html-spec/html-spec_13.html
    line = line.replace( '&#13;', '\r' ).replace( '&#10;', '\n' ).replace( '&nbsp;', '\u00A0' )
    # remove non-printable chars and normalize space characters
    line = trim( remove_control_characters( line.translate( SPACES_TABLE ) ) )
    # prune empty lines
    if re.match( r'\s*$', line ):
        line = None
    return line


def sanitize( text ):
    '''Convert text and discard incompatible and invalid characters'''
    try:
        # returnlines = []
        # for line in text.splitlines():
        #    returnlines.append(line_processing(line))
        # return '\n'.join(list(filter(None.__ne__, returnlines)))
        return '\n'.join( [ l for l in (line_processing( l ) for l in text.splitlines()) if l is not None ] )
        # return '\n'.join([l for l in map(line_processing, text.splitlines()) if l is not None])
    except AttributeError:
        return None


def trim( string ):
    '''Remove unnecessary spaces within a text string'''
    try:
        # remove newlines that are not related to punctuation or markup + proper trimming
        return SPACE_TRIMMING.sub( r' ', NO_TAG_SPACE.sub( r' ', string ) ).strip( ' \t\n\r\v' )
    except TypeError:
        return None


def normalize_tags( tags ):
    '''Remove special characters of tags'''
    tags = CLEAN_META_TAGS.sub( r'', trim( unescape( tags ) ) )
    tags = list( filter( None, tags.split( ", " ) ) )
    return ", ".join( tags )


def is_image_file( imagesrc ):
    '''Check if the observed string corresponds to a valid image extension,
       return False otherwise'''
    return bool( imagesrc is not None and IMAGE_EXTENSION.search( imagesrc ) )


def filter_urls( linklist, urlfilter ):
    'Return a list of links corresponding to the given substring pattern.'
    if urlfilter is None:
        return sorted( set( linklist ) )
    # filter links
    newlist = [ l for l in linklist if urlfilter in l ]
    # feedburner option
    if not newlist:
        newlist = [ l for l in linklist if urlfilter in l or 'feedburner' in l or 'feedproxy' in l ]
    return sorted( set( newlist ) )


def normalize_authors( current_authors, author_string ):
    '''Normalize author info to focus on author names only'''
    new_authors = [ ]
    if author_string.lower().startswith( 'http' ) or AUTHOR_EMAIL.match( author_string ):
        return current_authors
    if current_authors is not None:
        new_authors = current_authors.split( '; ' )
    # fix to code with unicode
    if '\\u' in author_string:
        author_string = author_string.encode().decode( 'unicode_escape' )
    # fix html entities
    if '&#' in author_string or '&amp;' in author_string:
        author_string = unescape( author_string )
    # examine names
    for author in AUTHOR_SPLIT.split( author_string ):
        author = trim( author )
        author = AUTHOR_EMOJI_REMOVE.sub( '', author )
        # remove @username
        author = AUTHOR_TWITTER.sub( '', author )
        # replace special characters with space
        author = trim( AUTHOR_REPLACE_JOIN.sub( ' ', author ) )
        author = AUTHOR_REMOVE_NICKNAME.sub( '', author )
        # remove special characters
        author = AUTHOR_REMOVE_SPECIAL.sub( '', author )
        author = AUTHOR_PREFIX.sub( '', author )
        author = AUTHOR_REMOVE_NUMBERS.sub( '', author )
        author = AUTHOR_REMOVE_PREPOSITION.sub( '', author )
        # skip empty or improbably long strings
        if len( author ) == 0 or (
                # simple heuristics, regex or vowel tests also possible
                ' ' not in author and '-' not in author and len( author ) >= 50
        ):
            continue
        # title case
        if not author[ 0 ].isupper() or sum( 1 for c in author if c.isupper() ) < 1:
            author = author.title()
        # safety checks
        if author not in new_authors and (len( new_authors ) == 0 or all( new_author not in author for new_author in new_authors )):
            new_authors.append( author )
    if len( new_authors ) == 0:
        return current_authors
    return '; '.join( new_authors ).strip( '; ' )


# todo: document and check this function
def check_authors( authors , *args):
    return [ author for author in authors.split( '; ' ) ]


def uniquify_list( l ):
    """
    Remove duplicates from a list while keeping order in an efficient way.
    Dictionaries preserve insertion order since Python 3.6.

    https://www.peterbe.com/plog/fastest-way-to-uniquify-a-list-in-python-3.6
    """
    return list( dict.fromkeys( l ) )
