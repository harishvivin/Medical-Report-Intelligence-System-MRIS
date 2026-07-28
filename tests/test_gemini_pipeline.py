import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "backend"))
sys.path.append(str(BASE_DIR / "backend" / "src"))
sys.path.append(str(BASE_DIR / "tests"))

from document_index import DocumentIndex
from pdf_reader import PDFReader
from qa_engine import QAEngine
from text_search import TextSearchEngine
from generate_sample_reports import generate_pdf_reports, SAMPLES_DIR

class TestGeminiPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generate_pdf_reports()
        cls.pdf1 = str(SAMPLES_DIR / "report1_blood_work.pdf")

    def test_search_pages(self):
        reader = PDFReader(self.pdf1)
        entries = reader.extract_all_text_blocks()
        doc_index = DocumentIndex(entries)
        search_engine = TextSearchEngine(doc_index)

        pages = search_engine.search_pages({"normalized_question": "hemoglobin", "keywords": ["hemoglobin"], "target_entities": ["hemoglobin"]}, top_k=5)
        self.assertEqual(pages, [1])
        reader.close()

    @patch("qa_engine.GeminiClient")
    def test_qa_engine_with_gemini_response(self, MockGeminiClient):
        mock_client = MockGeminiClient.return_value
        mock_client.is_available.return_value = True
        mock_client.extract_answer.return_value = {
            "found": True,
            "answer": "14.8 g/dL",
            "matched_line": "Hemoglobin : 14.8 g/dL (Reference Range: 13.5 - 17.5 g/dL)",
            "page": 1,
            "confidence": 0.99
        }

        reader = PDFReader(self.pdf1)
        entries = reader.extract_all_text_blocks()
        doc_index = DocumentIndex(entries)

        qa = QAEngine(self.pdf1, doc_index)
        res = qa.answer_question("What is the Hemoglobin?")

        self.assertEqual(res["answer"], "14.8 g/dL")
        self.assertEqual(res["page_number"], 1)
        self.assertEqual(res["confidence"], 0.99)
        self.assertIsNotNone(res["bounding_box"])
        self.assertIsNotNone(res["snippet_url"])

    @patch("qa_engine.GeminiClient")
    def test_qa_engine_not_found_with_gemini(self, MockGeminiClient):
        mock_client = MockGeminiClient.return_value
        mock_client.is_available.return_value = True
        mock_client.extract_answer.return_value = {
            "found": False,
            "answer": "The uploaded report does not contain this information.",
            "matched_line": None,
            "page": None,
            "confidence": 0.0
        }

        reader = PDFReader(self.pdf1)
        entries = reader.extract_all_text_blocks()
        doc_index = DocumentIndex(entries)

        qa = QAEngine(self.pdf1, doc_index)
        res = qa.answer_question("What is the brain MRI result?")

        self.assertEqual(res["answer"], "The uploaded report does not contain this information.")
        self.assertIsNone(res["page_number"])
        self.assertIsNone(res["bounding_box"])

if __name__ == "__main__":
    unittest.main()
