"""
Functions related to content filtering, mostly duplicate detection and language
detection.
"""

import logging
import re

from base64 import b64encode
from hashlib import sha1

# language detection
try:
    import py3langid

    LANGID_FLAG = True
except ImportError:
    LANGID_FLAG = False

from .utils import trim

LOGGER = logging.getLogger( __name__ )

RE_HTML_LANG = re.compile( r'([a-z]{2})', re.I )

# Mostly filters for social media
RE_FILTER = re.compile( r'\W*(Drucken|E-?Mail|Facebook|Flipboard|Google|Instagram|'
                        'Linkedin|Mail|PDF|Pinterest|Pocket|Print|QQ|Reddit|Twitter|'
                        'WeChat|WeiBo|Whatsapp|Xing|Mehr zum Thema:?|More on this.{,8}$)$',
                        flags=re.IGNORECASE )


# COMMENTS_BLACKLIST = ('( Abmelden / Ändern )') # Fill in your details below|Trage deine Daten unten|Kommentar verfassen|Bitte logge dich|Hinterlasse einen Kommentar| to %s| mit %s)


def textfilter( element ):
    '''Filter out unwanted text'''
    # print('#', element.text)
    if element.text is None and element.tail is not None:
        testtext = element.tail
    else:
        testtext = element.text

    if text_chars_test( testtext ) is False:
        return True
    # to check: line len → continue if len(line) <= 5
    return any( RE_FILTER.match( line ) for line in testtext.splitlines() )


def text_chars_test( string ):
    '''Determine if a string is only composed of spaces and/or control characters'''
    # or not re.search(r'\w', string)
    # return string is not None and len(string) != 0 and not string.isspace()
    return string not in (None, '') and not string.isspace()


def content_fingerprint( string ):
    '''Calculate a hash value for meaningful bits of the content'''
    teststring = ' '.join( re.findall( r'\w{5,}', string.lower() ) )
    m = sha1()
    m.update( teststring.encode() )
    fingerprint = m.digest()
    return b64encode( fingerprint ).decode()
