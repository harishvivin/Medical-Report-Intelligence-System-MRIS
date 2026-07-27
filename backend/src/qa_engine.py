import re
from typing import Dict, Any, Optional
from pdf_reader import PDFReader
from document_index import DocumentIndex
from question_parser import QuestionParser
from text_search import TextSearchEngine
from cropper import ScreenshotCropper
from config import MIN_CONFIDENCE_SCORE
from logger import logger

NOT_FOUND_MESSAGE = "The uploaded report does not contain this information."

class QAEngine:
    def __init__(self, pdf_path: str, document_index: DocumentIndex):
        self.pdf_path = pdf_path
        self.index = document_index
        self.search_engine = TextSearchEngine(document_index)

    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Answers a user question based ONLY on the indexed PDF content.
        Returns:
            {
                "question": str,
                "answer": str,
                "page_number": Optional[int],
                "confidence": float,
                "snippet_url": Optional[str],
                "bounding_box": Optional[List[float]]
            }
        """
        parsed_q = QuestionParser.parse(question)
        logger.info(f"Parsed question intent: {parsed_q['intent']}, target entities: {parsed_q['target_entities']}")

        search_results = self.search_engine.search(parsed_q, top_k=3)

        if not search_results:
            logger.info("No matching text blocks found for query.")
            return {
                "question": question,
                "answer": NOT_FOUND_MESSAGE,
                "page_number": None,
                "confidence": 0.0,
                "snippet_url": None,
                "bounding_box": None
            }

        top_block, top_score = search_results[0]
        logger.info(f"Top match score: {top_score:.3f} for block page {top_block['page_number']}")

        # Enforce confidence threshold
        if top_score < MIN_CONFIDENCE_SCORE:
            logger.info(f"Top match score {top_score:.3f} below threshold {MIN_CONFIDENCE_SCORE}")
            return {
                "question": question,
                "answer": NOT_FOUND_MESSAGE,
                "page_number": None,
                "confidence": round(top_score, 2),
                "snippet_url": None,
                "bounding_box": None
            }

        # Format exact extracted answer string from matched text block
        extracted_answer = self._format_answer(top_block, parsed_q)

        # Generate screenshot crop with green highlight
        try:
            _, snippet_url = ScreenshotCropper.crop_and_highlight(
                pdf_path=self.pdf_path,
                page_index=top_block["page_index"],
                bounding_box=top_block["bounding_box"]
            )
        except Exception as e:
            logger.error(f"Error generating screenshot crop: {e}")
            snippet_url = None

        return {
            "question": question,
            "answer": extracted_answer,
            "page_number": top_block["page_number"],
            "confidence": round(top_score, 2),
            "snippet_url": snippet_url,
            "bounding_box": top_block["bounding_box"]
        }

    def _format_answer(self, block: Dict[str, Any], parsed_q: Dict[str, Any]) -> str:
        """Extracts the most relevant line or sentence from the block matching question keywords."""
        block_text = block["text"]
        lines = [l.strip() for l in block_text.split("\n") if l.strip()]

        keywords = parsed_q["keywords"]
        if not keywords or not lines:
            return block_text

        # Score lines inside the matching block
        scored_lines = []
        for line in lines:
            norm_line = line.lower()
            kw_matches = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', norm_line))
            
            # Penalize generic header lines
            penalty = 0
            if any(h in norm_line for h in ["report", "panel", "examination", "laboratory", "evaluation"]):
                penalty = 1.5

            has_value = 1 if any(char.isdigit() for char in line) or any(w in norm_line for w in ["impression", "rhythm", "reactive", "positive", "negative", "normal"]) else 0
            
            # Direct result line bonus (e.g. 'HIV 1 & 2 Antibodies Screen : Non-Reactive')
            direct_result_bonus = 2.0 if ":" in line and any(v in norm_line for v in ["non-reactive", "reactive", "positive", "negative", "normal", "high", "low", "g/dl", "mg/dl", "mmhg", "%"]) else 0.0

            # Target kw in line title bonus
            target_title_bonus = 2.0 if any(kw in norm_line and not norm_line.startswith("diagnosis") for kw in keywords) else 0.0

            line_score = (kw_matches * 2) + has_value + direct_result_bonus + target_title_bonus - penalty
            scored_lines.append((line, line_score))

        scored_lines.sort(key=lambda x: x[1], reverse=True)
        return scored_lines[0][0] if scored_lines else block_text
