import gensim
from gensim import corpora, models
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import RegexpTokenizer
from stop_words import get_stop_words

from roi_web.processing import load_processed

en_stop = set( get_stop_words( 'en' ) )
tokenizer = RegexpTokenizer( r'\w+' )
p_stemmer = PorterStemmer()
texts = [ ]


for idx, el in enumerate( load_processed() ):
    tokens = tokenizer.tokenize( el.text.lower() )
    stemmed = [ p_stemmer.stem( i ) for i in tokens if not i in en_stop ]
    texts.append( stemmed )


dictionary = corpora.Dictionary( texts )

# convert tokenized documents into a document-term matrix
corpus = [ dictionary.doc2bow( text ) for text in texts ]

# generate LDA model
ldamodel = gensim.models.ldamodel.LdaModel( corpus, num_topics=10, id2word=dictionary, passes=20 )
print()
