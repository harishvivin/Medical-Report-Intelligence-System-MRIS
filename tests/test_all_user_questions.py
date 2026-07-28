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
from question_parser import QuestionParser
from generate_sample_reports import generate_pdf_reports, SAMPLES_DIR

USER_QUESTION_SUITE = [
    # Basic Information
    "What is the patient's name?",
    "What is the patient's age?",
    "What is the patient's gender?",
    "What is the hospital name?",
    "What is the report date?",
    "What is the application number?",
    "What is the MER number?",
    "What is the HSP code?",
    "What is the service type?",
    "What tests were performed?",

    # CBC
    "What is the haemoglobin value?",
    "What is the total leukocyte count?",
    "What is the platelet count?",
    "What is the RBC count?",
    "What is the MCV value?",
    "What is the MCH value?",
    "What is the MCHC value?",
    "What is the ESR value?",
    "What is the neutrophil percentage?",
    "What is the lymphocyte percentage?",

    # Kidney Function
    "What is the serum creatinine level?",
    "What is the blood urea nitrogen (BUN) value?",
    "Is the creatinine value normal?",

    # Diabetes
    "What is the HbA1c value?",
    "Is the patient diabetic based on the HbA1c result?",

    # Liver Function
    "What is the total bilirubin value?",
    "What is the direct bilirubin value?",
    "What is the indirect bilirubin value?",
    "What is the SGOT (AST) value?",
    "What is the SGPT (ALT) value?",
    "What is the alkaline phosphatase value?",
    "What is the GGT value?",

    # Lipid Profile
    "What is the total cholesterol value?",
    "What is the triglyceride level?",
    "What is the HDL cholesterol value?",
    "What is the LDL cholesterol value?",
    "What is the VLDL cholesterol value?",

    # Infectious Diseases
    "What is the HIV test result?",
    "What is the HBsAg test result?",
    "Is the HIV test positive or negative?",

    # Urine Analysis
    "What is the urine colour?",
    "What is the urine pH?",
    "Is urine protein present?",
    "Is urine sugar present?",
    "What is the specific gravity?",
    "Are pus cells present?",
    "Are epithelial cells present?",
    "Are RBCs present in urine?",

    # ECG
    "What is the ECG interpretation?",
    "Is the ECG normal?",

    # General Questions
    "Summarize this medical report.",
    "What are the abnormal values in this report?",
    "List all normal laboratory values.",
    "Which tests indicate kidney function?",
    "Which tests indicate liver function?",
    "Which tests indicate diabetes?",
    "Which tests indicate infection?",
    "What are the important findings in this report?",
    "Is there any value outside the reference range?",
    "Give a complete summary of the patient's health."
]

class TestAllUserQuestions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generate_pdf_reports()
        cls.pdf_blood = str(SAMPLES_DIR / "report1_blood_work.pdf")
        cls.pdf_renal = str(SAMPLES_DIR / "report2_renal_panel.pdf")

    def test_question_parser_entity_extraction(self):
        for q in USER_QUESTION_SUITE:
            parsed = QuestionParser.parse(q)
            self.assertIsNotNone(parsed["intent"])
            self.assertIsNotNone(parsed["normalized_question"])

    @patch("qa_engine.GeminiClient")
    def test_qa_engine_handles_all_questions_with_gemini(self, MockGeminiClient):
        mock_client = MockGeminiClient.return_value
        mock_client.is_available.return_value = True
        
        # Mock responses for Gemini based on query
        def mock_extract(q, context):
            if "name" in q.lower():
                return {
                    "found": True,
                    "answer": "John Doe",
                    "matched_line": "Patient Name: John Doe",
                    "page": 1,
                    "confidence": 0.99
                }
            elif "haemoglobin" in q.lower() or "hemoglobin" in q.lower():
                return {
                    "found": True,
                    "answer": "14.8 g/dL",
                    "matched_line": "Hemoglobin : 14.8 g/dL (Reference Range: 13.5 - 17.5 g/dL)",
                    "page": 1,
                    "confidence": 0.99
                }
            elif "creatinine" in q.lower():
                return {
                    "found": True,
                    "answer": "1.8 mg/dL (High)",
                    "matched_line": "Serum Creatinine : 1.8 mg/dL (Reference Range: 0.6 - 1.2 mg/dL) [High]",
                    "page": 1,
                    "confidence": 0.99
                }
            elif "summarize" in q.lower() or "health" in q.lower():
                return {
                    "found": True,
                    "answer": "Patient John Doe presented normal hematology profile with Hemoglobin 14.8 g/dL.",
                    "matched_line": "Diagnosis / Impression: Normal Hematology Profile.",
                    "page": 1,
                    "confidence": 0.99
                }
            else:
                return {
                    "found": False,
                    "answer": "The uploaded report does not contain this information.",
                    "matched_line": None,
                    "page": None,
                    "confidence": 0.0
                }

        mock_client.extract_answer.side_effect = mock_extract

        reader = PDFReader(self.pdf_blood)
        entries = reader.extract_all_text_blocks()
        doc_index = DocumentIndex(entries)
        qa = QAEngine(self.pdf_blood, doc_index)

        for q in USER_QUESTION_SUITE:
            res = qa.answer_question(q)
            self.assertIn("answer", res)
            self.assertIn("confidence", res)
            self.assertIn("question", res)
        
        reader.close()

if __name__ == "__main__":
    unittest.main()
