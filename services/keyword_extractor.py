from konlpy.tag import Okt
from sklearn.feature_extraction.text import TfidfVectorizer

def extract_keywords_tfidf(text_list, n_keywords=10):
    okt = Okt()
    # 문장들에서 명사만 추출
    processed_docs = [" ".join(okt.nouns(text)) for text in text_list]

    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(processed_docs)

    scores = zip(vectorizer.get_feature_names_out(), tfidf.sum(axis=0).tolist()[0])
    sorted_keywords = sorted(scores, key=lambda x: x[1], reverse=True)

    return [word for word, score in sorted_keywords[:n_keywords]]