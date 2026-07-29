"""
Test Suite for Experimental Gemini Pipeline.
Tests:
- Key failover mechanism (Primary -> Fallback retry)
- Prompt generation with f-strings
- PyMuPDF coordinate cropping & PNG generation
- Medical questions processing across sample medical PDFs:
  (Patient Name, Hospital Name, Creatinine, HbA1c, Hemoglobin, Blood Pressure, Diagnosis, ECG, HIV, Summary)
- Verification of page, bounding box, crop, and JSON structure.
"""

import os
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import experimental pipeline modules
from experimental_gemini_pipeline.config import CROPS_DIR
from experimental_gemini_pipeline.prompt_builder import build_prompt
from experimental_gemini_pipeline.coordinate_cropper import crop_pdf_region
from experimental_gemini_pipeline.gemini_client import locate_answer_in_pdf
from experimental_gemini_pipeline.main import process_query

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "tests" / "samples"


class TestExperimentalGeminiPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Generate sample PDFs if not present
        if not (SAMPLES_DIR / "report1_blood_work.pdf").exists():
            try:
                from tests.generate_sample_reports import generate_pdf_reports
                generate_pdf_reports()
            except Exception as e:
                print(f"Sample PDF setup warning: {e}")

        cls.sample_pdf = str(SAMPLES_DIR / "report1_blood_work.pdf")
        cls.test_questions = [
            "Patient Name",
            "Hospital Name",
            "Creatinine",
            "HbA1c",
            "Hemoglobin",
            "Blood Pressure",
            "Diagnosis",
            "ECG",
            "HIV",
            "Summary"
        ]

    def test_01_prompt_builder(self):
        """Verify prompt builder produces correct f-string prompt demanding JSON."""
        question = "What is the Hemoglobin level?"
        prompt = build_prompt(question)
        self.assertIn(question, prompt)
        self.assertIn("Return ONLY JSON", prompt)
        self.assertIn("bounding_box", prompt)
        self.assertIn("Never hallucinate.", prompt)

    def test_02_coordinate_cropper_pymupdf(self):
        """Verify PyMuPDF coordinate cropper creates a valid PNG file from coordinates."""
        if not Path(self.sample_pdf).exists():
            self.skipTest(f"Sample PDF {self.sample_pdf} not found.")

        bbox = {"x1": 100, "y1": 200, "x2": 500, "y2": 400}
        crop_path = crop_pdf_region(
            pdf_path=self.sample_pdf,
            page_num=1,
            bbox=bbox,
            padding_points=5.0
        )
        
        self.assertTrue(Path(crop_path).exists())
        self.assertTrue(Path(crop_path).stat().st_size > 0)
        self.assertTrue(crop_path.endswith(".png"))

    @patch("experimental_gemini_pipeline.gemini_client._call_gemini_single_key")
    def test_03_api_key_primary_success(self, mock_call):
        """Verify transparent usage of primary API key when primary key succeeds."""
        mock_response = json.dumps({
            "found": True,
            "page": 1,
            "bounding_box": {"x1": 100, "y1": 150, "x2": 600, "y2": 300},
            "matched_text": "Hemoglobin : 14.8 g/dL",
            "confidence": 0.99
        })
        mock_call.return_value = mock_response

        with patch("experimental_gemini_pipeline.gemini_client.GEMINI_API_KEY_PRIMARY", "PRIMARY_KEY_123"), \
             patch("experimental_gemini_pipeline.gemini_client.GEMINI_API_KEY_FALLBACK", "FALLBACK_KEY_456"):

            res = locate_answer_in_pdf(self.sample_pdf, "Hemoglobin")
            self.assertTrue(res["found"])
            self.assertEqual(res["page"], 1)
            self.assertEqual(res["api_key_used"], "PRIMARY")
            self.assertEqual(mock_call.call_count, 1)

    @patch("experimental_gemini_pipeline.gemini_client._call_gemini_single_key")
    def test_04_api_key_transparent_fallback_retry(self, mock_call):
        """Verify transparent failover retry to fallback API key when primary key raises an exception."""
        mock_success_response = json.dumps({
            "found": True,
            "page": 1,
            "bounding_box": {"x1": 120, "y1": 180, "x2": 620, "y2": 320},
            "matched_text": "Hemoglobin : 14.8 g/dL",
            "confidence": 0.99
        })

        # First call (Primary key) raises Exception (e.g. rate limit / quota exceeded), second call (Fallback key) succeeds
        mock_call.side_effect = [
            RuntimeError("Rate limit exceeded 429"),
            mock_success_response
        ]

        with patch("experimental_gemini_pipeline.gemini_client.GEMINI_API_KEY_PRIMARY", "PRIMARY_KEY_EXPIRED"), \
             patch("experimental_gemini_pipeline.gemini_client.GEMINI_API_KEY_FALLBACK", "FALLBACK_KEY_VALID"):

            res = locate_answer_in_pdf(self.sample_pdf, "Hemoglobin")
            self.assertTrue(res["found"])
            self.assertEqual(res["api_key_used"], "FALLBACK")
            self.assertEqual(mock_call.call_count, 2)

    @patch("experimental_gemini_pipeline.gemini_client._call_gemini_single_key")
    def test_05_medical_questions_verification(self, mock_call):
        """Verify pipeline handles all required medical questions and generates correct PNG crops & JSON."""
        mock_response = json.dumps({
            "found": True,
            "page": 1,
            "bounding_box": {"x1": 200, "y1": 250, "x2": 700, "y2": 350},
            "matched_text": "Sample Value",
            "confidence": 0.98
        })
        mock_call.return_value = mock_response

        with patch("experimental_gemini_pipeline.gemini_client.GEMINI_API_KEY_PRIMARY", "KEY_TEST"):
            for question in self.test_questions:
                res = process_query(self.sample_pdf, question)
                result_json = res["result"]
                crop_path = res["crop_path"]

                # Verify JSON structure
                self.assertIn("found", result_json)
                self.assertIn("page", result_json)
                self.assertIn("bounding_box", result_json)
                self.assertIn("matched_text", result_json)
                self.assertIn("confidence", result_json)

                # Verify Bounding Box
                bbox = result_json["bounding_box"]
                self.assertIn("x1", bbox)
                self.assertIn("y1", bbox)
                self.assertIn("x2", bbox)
                self.assertIn("y2", bbox)

                # Verify Crop file exists
                if result_json.get("found"):
                    self.assertIsNotNone(crop_path)
                    self.assertTrue(Path(crop_path).exists())


if __name__ == "__main__":
    unittest.main()
