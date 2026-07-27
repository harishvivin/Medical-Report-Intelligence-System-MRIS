import numpy as np
import re
from typing import List, Dict, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from document_index import DocumentIndex
from logger import logger

class TextSearchEngine:
    def __init__(self, index: DocumentIndex):
        self.index = index

    def search(self, question_parsed: Dict[str, Any], top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        """
        Searches indexed document blocks using TF-IDF cosine similarity, keyword overlap,
        and entity boosting.
        Returns sorted list of tuples: (block_dict, composite_score)
        """
        if not self.index.blocks:
            return []

        norm_q = question_parsed["normalized_question"]
        keywords = question_parsed["keywords"]
        target_entities = question_parsed["target_entities"]

        # 1. Compute TF-IDF Cosine Similarity
        query_vec = self.index.transform_query(norm_q)
        tfidf_scores = np.zeros(len(self.index.blocks))
        
        if query_vec is not None and self.index.tfidf_matrix is not None:
            sim_matrix = cosine_similarity(query_vec, self.index.tfidf_matrix)
            tfidf_scores = sim_matrix.flatten()

        # 2. Hybrid Scoring per Entry
        results = []
        for i, block in enumerate(self.index.blocks):
            block_text_norm = block["normalized_text"]
            base_tfidf = float(tfidf_scores[i])
            entry_type = block.get("type", "block")

            # Keyword Overlap Score
            kw_match_count = 0
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, block_text_norm):
                    kw_match_count += 1
            
            kw_overlap_score = (kw_match_count / max(1, len(keywords))) if keywords else 0.0

            # Entity Match Bonus - ONLY apply if there is actual keyword overlap or TF-IDF relevance
            entity_bonus = 0.0
            if target_entities and (base_tfidf > 0.05 or kw_overlap_score > 0.2):
                for entity in target_entities:
                    if entity in block_text_norm or any(re.search(r'\b' + re.escape(kw) + r'\b', block_text_norm) for kw in keywords):
                        entity_bonus += 0.25

            # Precision Entry Type Boost (Row/Segment level gives exact bounding box crops!)
            type_boost = 0.15 if entry_type in ["segment", "row"] else 0.0

            # Check for header penalty vs finding boost
            header_penalty = 0.0
            finding_boost = 0.0

            if any(h in block_text_norm for h in ["report", "examination", "laboratory", "evaluation", "department"]):
                if not any(v in block_text_norm for v in ["impression", "rhythm", "g/dl", "mg/dl", "mmhg", "bpm", "%", "normal", "high", "low"]):
                    header_penalty = 0.20

            if any(v in block_text_norm for v in ["impression", "sinus rhythm", "rhythm", "st segment", "g/dl", "mg/dl", "mmhg", "bpm", "hba1c", "non-reactive", "reactive", "positive", "negative"]):
                finding_boost = 0.15

            # If user provided specific keywords and NONE matched, suppress match
            if keywords and kw_match_count == 0 and base_tfidf < 0.12:
                composite_score = 0.0
            else:
                composite_score = (0.45 * base_tfidf) + (0.40 * kw_overlap_score) + entity_bonus + type_boost + finding_boost - header_penalty

            composite_score = min(1.0, max(0.0, composite_score))

            if composite_score > 0.05:
                results.append((block, composite_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
