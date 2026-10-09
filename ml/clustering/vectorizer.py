"""TF-IDF N-gram Text Vectorizer."""

from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from ml.clustering.normalizer import FailureTextNormalizer


class FailureVectorizer:
    def __init__(self, max_features: int = 1000):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=max_features,
            stop_words="english",
            lowercase=True,
        )

    def vectorize_failures(self, raw_failure_texts: List[str]):
        """Normalizes and vectorizes a list of raw failure text strings."""
        if not raw_failure_texts:
            return None

        normalized_texts = [FailureTextNormalizer.normalize_text(t) for t in raw_failure_texts]
        
        # Handle cases with very short or identical text
        try:
            matrix = self.vectorizer.fit_transform(normalized_texts)
            return matrix
        except Exception:
            return None
