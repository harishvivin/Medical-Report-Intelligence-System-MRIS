import sys
import unittest
import fitz
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "backend"))
sys.path.append(str(BASE_DIR / "backend" / "src"))
sys.path.append(str(BASE_DIR / "tests"))

from pdf_reader import PDFReader
from document_index import DocumentIndex
from text_search import TextSearchEngine
from qa_engine import QAEngine

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
MANJIT_PDF_PATH = SAMPLES_DIR / "report6_manjit_singh.pdf"

def generate_manjit_pdf():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    
    # Page 1: Header & Patient Details
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text((50, 50), "JEEVANDEEP DIAGNOSTIC & POLYCLINIC", fontsize=16, color=(0.06, 0.72, 0.50))
    page1.insert_text((50, 80), "Patient Name: MANJIT SINGH", fontsize=11)
    page1.insert_text((50, 100), "Age / Gender: 57 Yrs / Male", fontsize=11)
    page1.insert_text((350, 80), "Referred By: TATA AIA", fontsize=11)
    page1.insert_text((350, 100), "Date: 17/07/2026", fontsize=11)
    page1.insert_text((50, 130), "Application No: U100723465AD0 | MER No: TALIC-4689616 | HSP Code: HSP009783", fontsize=10)
    page1.insert_text((50, 150), "Service Type: Home Visit", fontsize=10)
    page1.insert_text((50, 180), "VITALS & PHYSICAL MEASUREMENTS", fontsize=13, color=(0.05, 0.50, 0.60))
    page1.insert_text((50, 205), "Blood Pressure : 125/81 mmHg (Pulse: 92 / minute)", fontsize=11)
    page1.insert_text((50, 225), "Height : 177 cm | Weight : 103.95 kg | Abdomen Girth : 110 cm", fontsize=11)
    page1.insert_text((50, 255), "CARDIOLOGY EXAMINATION & ECG REPORT", fontsize=13, color=(0.05, 0.50, 0.60))
    page1.insert_text((50, 280), "ECG Impression : ECG within normal limit (Heart Rate: 69 BPM, Sinus Rhythm)", fontsize=11)
    
    # Page 2: Complete Blood Count (CBC)
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 50), "JEEVANDEEP DIAGNOSTIC & POLYCLINIC", fontsize=16, color=(0.06, 0.72, 0.50))
    page2.insert_text((50, 80), "Patient Name: MANJIT SINGH | Date: 17/07/2026", fontsize=11)
    page2.insert_text((50, 110), "COMPLETE BLOOD COUNT (CBC)", fontsize=13, color=(0.05, 0.50, 0.60))
    page2.insert_text((50, 140), "HAEMOGLOBIN : 14.92 g/dL (Reference Range: 14 - 16 g/dL)", fontsize=11)
    page2.insert_text((50, 165), "TOTAL LEUCOCYTE COUNT (WBC) : 7,900 /cu.mm (Reference Range: 4,000 - 11,000 /cu.mm)", fontsize=11)
    page2.insert_text((50, 190), "PLATELET COUNT : 2,90,000 /cu.mm (Reference Range: 1,50,000 - 4,50,000 /cu.mm)", fontsize=11)
    page2.insert_text((50, 215), "RED BLOOD CORPUSCLES (RBC) : 5.88 mill/cu.mm (Reference Range: 4.5 - 6.5)", fontsize=11)
    page2.insert_text((50, 240), "PACKED CELL VOLUME (PCV) : 38.21 % (Reference Range: 34 - 46 %)", fontsize=11)
    page2.insert_text((50, 265), "MEAN CORPUSCLES VOLUME (MCV) : 84.52 fl (Reference Range: 78 - 92 fl)", fontsize=11)
    page2.insert_text((50, 290), "ERYTHROCYTE SEDIMENTATION RATE (ESR) : 14 mm/hr (Reference Range: 00 - 15 mm/hr)", fontsize=11)
    page2.insert_text((50, 315), "Neutrophil : 63 % | Lymphocytes : 28 %", fontsize=11)

    # Page 3: Diabetes, Kidney, Liver, Lipid & Serology
    page3 = doc.new_page(width=595, height=842)
    page3.insert_text((50, 50), "JEEVANDEEP DIAGNOSTIC & POLYCLINIC", fontsize=16, color=(0.06, 0.72, 0.50))
    page3.insert_text((50, 80), "GLYCATED HAEMOGLOBIN (HbA1c) : 5.1 % (Reference Range: 4.0 - 5.9 %)", fontsize=11)
    page3.insert_text((50, 105), "RANDOM BLOOD SUGAR : 112.12 mg/dL (Reference Range: 70 - 140 mg/dL)", fontsize=11)
    page3.insert_text((50, 130), "BLOOD UREA NITROGEN (BUN) : 18.10 mg/dL (Reference Range: 06 - 24 mg/dL)", fontsize=11)
    page3.insert_text((50, 155), "SERUM CREATININE : 0.88 mg/dL (Reference Range: 0.7 - 1.4 mg/dL)", fontsize=11)
    page3.insert_text((50, 180), "REPORT ON THE ESTIMATION OF VIRAL SEROLOGY", fontsize=13, color=(0.05, 0.50, 0.60))
    page3.insert_text((50, 205), "Hepatitis B Surface Antigen (HBsAg) : NON REACTIVE", fontsize=11)
    page3.insert_text((50, 230), "HIV 1 & 2 ANTIBODIES SCREENING TEST : NEGATIVE", fontsize=11)
    page3.insert_text((50, 255), "COTININE TEST (Urine) : NEGATIVE", fontsize=11)
    page3.insert_text((50, 280), "LIVER FUNCTION TEST (LFT)", fontsize=13, color=(0.05, 0.50, 0.60))
    page3.insert_text((50, 305), "TOTAL BILIRUBIN : 0.73 mg/dL | SGPT (ALT) : 23.24 U/L | SGOT (AST) : 24.72 U/L | ALKALINE PHOSPHATASE : 121.0 U/L", fontsize=10)
    page3.insert_text((50, 335), "LIPID PROFILE", fontsize=13, color=(0.05, 0.50, 0.60))
    page3.insert_text((50, 360), "Cholesterol Total : 158 mg/dL | Triglycerides : 140 mg/dL | HDL : 39.95 mg/dL | LDL : 89.65 mg/dL", fontsize=10)
    page3.insert_text((50, 390), "URINE ROUTINE & MICROSCOPIC EXAMINATION", fontsize=13, color=(0.05, 0.50, 0.60))
    page3.insert_text((50, 415), "Colour : YELLOW | Reaction : ACIDIC (6.2) | Protein : ABSENT | Sugar : ABSENT | Pus Cells : 02-03 / HPF", fontsize=10)

    doc.save(str(MANJIT_PDF_PATH))
    doc.close()
    return str(MANJIT_PDF_PATH)

class TestManjitSinghReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pdf_path = generate_manjit_pdf()
        reader = PDFReader(pdf_path)
        entries = reader.extract_all_text_blocks()
        cls.doc_index = DocumentIndex(entries)
        cls.qa_engine = QAEngine(pdf_path, cls.doc_index)

    def test_01_patient_metadata(self):
        res = self.qa_engine.answer_question("What is the patient name?")
        self.assertIn("MANJIT SINGH", res["answer"])

        res2 = self.qa_engine.answer_question("What is the patient age and gender?")
        self.assertIn("57", res2["answer"])

        res3 = self.qa_engine.answer_question("What is the hospital name?")
        self.assertIn("JEEVANDEEP", res3["answer"])

    def test_02_ecg_and_vitals(self):
        res = self.qa_engine.answer_question("What are the ECG findings?")
        self.assertIn("ECG within normal limit", res["answer"])

        res2 = self.qa_engine.answer_question("What is the blood pressure reading?")
        self.assertIn("125/81", res2["answer"])

    def test_03_cbc_parameters(self):
        res = self.qa_engine.answer_question("What is the haemoglobin value?")
        self.assertIn("14.92", res["answer"])

        res2 = self.qa_engine.answer_question("What is the total leukocyte count?")
        self.assertIn("7,900", res2["answer"])

        res3 = self.qa_engine.answer_question("What is the platelet count?")
        self.assertIn("2,90,000", res3["answer"])

    def test_04_diabetes_and_kft(self):
        res = self.qa_engine.answer_question("What is the HbA1c value?")
        self.assertIn("5.1", res["answer"])

        res2 = self.qa_engine.answer_question("What is the serum creatinine level?")
        self.assertIn("0.88", res2["answer"])

        res3 = self.qa_engine.answer_question("What is the blood urea nitrogen (BUN) value?")
        self.assertIn("18.10", res3["answer"])

    def test_05_serology_and_cotinine(self):
        res = self.qa_engine.answer_question("What is the HIV test status?")
        self.assertIn("NEGATIVE", res["answer"])

        res2 = self.qa_engine.answer_question("What is the Cotinine test result?")
        self.assertIn("NEGATIVE", res2["answer"])

if __name__ == "__main__":
    unittest.main()
