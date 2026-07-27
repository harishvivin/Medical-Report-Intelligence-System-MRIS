import sys
import unittest
from pathlib import Path

# Add backend and src to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "backend"))
sys.path.append(str(BASE_DIR / "backend" / "src"))
sys.path.append(str(BASE_DIR / "tests"))

from fastapi.testclient import TestClient
from app import app
from generate_sample_reports import generate_pdf_reports, SAMPLES_DIR

class TestMedicalReportExtractAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n--- Generating 5 Sample Medical Reports ---")
        generate_pdf_reports()
        cls.client = TestClient(app)

    def test_01_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_02_blood_work_report(self):
        pdf_path = SAMPLES_DIR / "report1_blood_work.pdf"
        with open(pdf_path, "rb") as f:
            resp = self.client.post("/api/process", files={"file": ("report1_blood_work.pdf", f, "application/pdf")})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        doc_id = data["document_id"]

        # Q&A Tests: Patient Name, Hospital, Hemoglobin, Diagnosis
        q1 = self.client.post("/api/qa/ask", json={"document_id": doc_id, "question": "What is the patient name?"})
        self.assertEqual(q1.status_code, 200)
        self.assertIn("John Doe", q1.json()["answer"])

        q2 = self.client.post("/api/qa/ask", json={"document_id": doc_id, "question": "What is the Hemoglobin level?"})
        self.assertEqual(q2.status_code, 200)
        self.assertIn("14.8", q2.json()["answer"])
        self.assertIsNotNone(q2.json()["snippet_url"])

        # Check Crop Endpoint
        snippet_url = q2.json()["snippet_url"]
        crop_resp = self.client.get(snippet_url)
        self.assertEqual(crop_resp.status_code, 200)
        self.assertEqual(crop_resp.headers["content-type"], "image/png")

        # Summary Test
        sum_resp = self.client.post("/api/summary", json={"document_id": doc_id})
        self.assertEqual(sum_resp.status_code, 200)
        summary = sum_resp.json()["summary"]
        self.assertIn("John Doe", summary["patient_info"]["name"])
        self.assertIn("METRO DIAGNOSTIC", summary["hospital"])

    def test_03_renal_panel_report(self):
        pdf_path = SAMPLES_DIR / "report2_renal_panel.pdf"
        with open(pdf_path, "rb") as f:
            resp = self.client.post("/api/process", files={"file": ("report2_renal_panel.pdf", f, "application/pdf")})
        self.assertEqual(resp.status_code, 200)
        doc_id = resp.json()["document_id"]

        # Q&A: Creatinine
        q = self.client.post("/api/qa/ask", json={"document_id": doc_id, "question": "What is the Serum Creatinine?"})
        self.assertEqual(q.status_code, 200)
        self.assertIn("1.8", q.json()["answer"])

        # Summary Test
        sum_resp = self.client.post("/api/summary", json={"document_id": doc_id})
        self.assertEqual(sum_resp.status_code, 200)
        self.assertIn("Sarah Jenkins", sum_resp.json()["summary"]["patient_info"]["name"])

    def test_04_diabetes_thyroid_report(self):
        pdf_path = SAMPLES_DIR / "report3_diabetes_thyroid.pdf"
        with open(pdf_path, "rb") as f:
            resp = self.client.post("/api/process", files={"file": ("report3_diabetes_thyroid.pdf", f, "application/pdf")})
        self.assertEqual(resp.status_code, 200)
        doc_id = resp.json()["document_id"]

        # Q&A: HbA1c
        q = self.client.post("/api/qa/ask", json={"document_id": doc_id, "question": "What is the HbA1c level?"})
        self.assertEqual(q.status_code, 200)
        self.assertIn("7.2", q.json()["answer"])

    def test_05_cardiology_ecg_report(self):
        pdf_path = SAMPLES_DIR / "report4_cardiology_ecg.pdf"
        with open(pdf_path, "rb") as f:
            resp = self.client.post("/api/process", files={"file": ("report4_cardiology_ecg.pdf", f, "application/pdf")})
        self.assertEqual(resp.status_code, 200)
        doc_id = resp.json()["document_id"]

        # Q&A: Blood Pressure & ECG
        q1 = self.client.post("/api/qa/ask", json={"document_id": doc_id, "question": "What is the Blood Pressure reading?"})
        self.assertEqual(q1.status_code, 200)
        self.assertIn("140/90", q1.json()["answer"])

        q2 = self.client.post("/api/qa/ask", json={"document_id": doc_id, "question": "What are the ECG findings?"})
        self.assertEqual(q2.status_code, 200)
        self.assertIn("Sinus Rhythm", q2.json()["answer"])

    def test_06_infectious_serology_report(self):
        pdf_path = SAMPLES_DIR / "report5_infectious_serology.pdf"
        with open(pdf_path, "rb") as f:
            resp = self.client.post("/api/process", files={"file": ("report5_infectious_serology.pdf", f, "application/pdf")})
        self.assertEqual(resp.status_code, 200)
        doc_id = resp.json()["document_id"]

        # Q&A: HIV
        q = self.client.post("/api/qa/ask", json={"document_id": doc_id, "question": "What is the HIV status?"})
        self.assertEqual(q.status_code, 200)
        self.assertIn("Non-Reactive", q.json()["answer"])

    def test_07_negative_query_zero_hallucination(self):
        pdf_path = SAMPLES_DIR / "report1_blood_work.pdf"
        with open(pdf_path, "rb") as f:
            resp = self.client.post("/api/process", files={"file": ("report1_blood_work.pdf", f, "application/pdf")})
        doc_id = resp.json()["document_id"]

        # Ask about non-existent term (e.g. Chemotherapy history or Brain MRI)
        q = self.client.post("/api/qa/ask", json={"document_id": doc_id, "question": "What is the brain MRI radiologist opinion?"})
        self.assertEqual(q.status_code, 200)
        self.assertEqual(q.json()["answer"], "The uploaded report does not contain this information.")

    def test_08_abnormal_values_query(self):
        pdf_path = SAMPLES_DIR / "report2_renal_panel.pdf"
        with open(pdf_path, "rb") as f:
            resp = self.client.post("/api/process", files={"file": ("report2_renal_panel.pdf", f, "application/pdf")})
        doc_id = resp.json()["document_id"]

        # Ask "Are there any high or low abnormal values?"
        q = self.client.post("/api/qa/ask", json={"document_id": doc_id, "question": "Are there any high or low abnormal values?"})
        self.assertEqual(q.status_code, 200)
        res = q.json()
        self.assertGreaterEqual(res["confidence"], 0.95)
        self.assertIn("1.8", res["answer"])
        self.assertIsNotNone(res["bounding_box"])
        self.assertIsNotNone(res["snippet_url"])
        self.assertGreater(res["bounding_box"][2] - res["bounding_box"][0], 350)

if __name__ == "__main__":
    unittest.main()
