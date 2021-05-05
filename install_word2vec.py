import gensim.downloader as api
import pickle
model = api.load('word2vec-google-news-300')
pickle.dump(model, open("static/word2vec_model", "wb"))
