import spacy
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import RegexpTokenizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation


from stop_words import get_stop_words

from roi_web.processing import load_processed

data_words = [ i.text for i in load_processed() ]
count_vect = CountVectorizer( max_df=0.8, min_df=2, stop_words='english' , lowercase = True, )
doc_term_matrix = count_vect.fit_transform( data_words )


LDA = LatentDirichletAllocation(n_components=5, random_state=42)
LDA.fit(doc_term_matrix)

for i,topic in enumerate(LDA.components_):
    print(f'Top 10 words for topic #{i}:')
    print([count_vect.get_feature_names()[i] for i in topic.argsort()[-10:]])
    print('\n')
