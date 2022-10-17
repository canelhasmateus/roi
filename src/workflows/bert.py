import spacy
from bertopic import BERTopic

from roi_web.processing import load_processed

docs = [ i.text for i in load_processed() ]
nlp = spacy.load('en_core_web_md', exclude=['tagger', 'parser', 'ner', 'attribute_ruler', 'lemmatizer'])

topic_model = BERTopic(embedding_model=nlp, nr_topics=10)
topics, probs = topic_model.fit_transform(docs)

fig = topic_model.visualize_topics()
fig.show()