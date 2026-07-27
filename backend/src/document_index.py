import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from logger import logger

class DocumentIndex:
    def __init__(self, blocks: List[Dict[str, Any]]):
        self.blocks = blocks
        self.corpus = [b["normalized_text"] for b in self.blocks]
        
        # Configure TF-IDF with word & n-gram capabilities for short medical terms (e.g., HbA1c, WBC, HIV, ECG)
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            token_pattern=r'(?u)\b[\w\.-]+\b',  # Include dots/dashes in tokens for medical values like HbA1c, 140/90, 4.5
            lowercase=True
        )

        if self.corpus:
            try:
                self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
                logger.info(f"Built TF-IDF matrix with shape: {self.tfidf_matrix.shape}")
            except Exception as e:
                logger.warning(f"Error fitting TF-IDF matrix: {e}. Defaulting to empty index.")
                self.tfidf_matrix = None
        else:
            self.tfidf_matrix = None

    def transform_query(self, query: str):
        if self.vectorizer is None or self.tfidf_matrix is None or self.tfidf_matrix.shape[0] == 0:
            return None
        try:
            return self.vectorizer.transform([query])
        except Exception as e:
            logger.error(f"Error transforming query for TF-IDF: {e}")
            return None

    def get_block(self, index: int) -> Dict[str, Any]:
        return self.blocks[index]

    def __len__(self):
        return len(self.blocks)
