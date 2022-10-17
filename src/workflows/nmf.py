import pyLDAvis
from matplotlib import pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer

from roi_web.processing import load_processed
from sklearn.decomposition import NMF


data_words = [ i.text for i in load_processed() ]
tfidf_vect = TfidfVectorizer( max_df=0.8, min_df=2, stop_words='english' , ngram_range=(1,2))
doc_term_matrix = tfidf_vect.fit_transform( data_words )

nmf = NMF(n_components=10 , random_state=42)
nmf.fit(doc_term_matrix )

for i,topic in enumerate(nmf.components_):
    print(f'Top 10 words for topic #{i}:')
    print([tfidf_vect.get_feature_names()[i] for i in topic.argsort()[-10:]]) 
    print('\n')


plt.scatter( nmf[ : , 0]
             ,
             nmf.components_[ : , 1]
             )
plt.show()