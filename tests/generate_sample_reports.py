import fitz  # PyMuPDF
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

REPORTS_DATA = [
    {
        "filename": "report1_blood_work.pdf",
        "title": "METRO DIAGNOSTIC LABORATORY",
        "patient": "Patient Name: John Doe",
        "age_gender": "Age / Gender: 45 Yrs / Male",
        "doctor": "Referred By: Dr. Alex Turner, MD",
        "date": "Date: 12/05/2025",
        "content": [
            "COMPLETE BLOOD COUNT (CBC) REPORT",
            "--------------------------------------------------",
            "Hemoglobin : 14.8 g/dL (Reference Range: 13.5 - 17.5 g/dL)",
            "RBC Count : 5.1 mill/uL (Reference Range: 4.5 - 5.9 mill/uL)",
            "WBC Count : 7200 /uL (Reference Range: 4000 - 11000 /uL)",
            "Platelets : 250000 /uL (Reference Range: 150000 - 450000 /uL)",
            "--------------------------------------------------",
            "Diagnosis / Impression: Normal Hematology Profile.",
            "Advised Clinical Correlation and Routine Annual Checkup."
        ]
    },
    {
        "filename": "report2_renal_panel.pdf",
        "title": "CITY CARE HOSPITAL & RENAL CENTER",
        "patient": "Patient Name: Sarah Jenkins",
        "age_gender": "Age / Gender: 52 Yrs / Female",
        "doctor": "Referred By: Dr. Rachel Green",
        "date": "Date: 18/06/2025",
        "content": [
            "RENAL FUNCTION TEST (KFT)",
            "--------------------------------------------------",
            "Serum Creatinine : 1.8 mg/dL (Reference Range: 0.6 - 1.2 mg/dL) [High]",
            "Blood Urea : 45 mg/dL (Reference Range: 15 - 40 mg/dL) [High]",
            "Uric Acid : 6.5 mg/dL (Reference Range: 2.5 - 6.0 mg/dL)",
            "Sodium : 138 mEq/L (Reference Range: 135 - 145 mEq/L)",
            "Potassium : 4.2 mEq/L (Reference Range: 3.5 - 5.0 mEq/L)",
            "--------------------------------------------------",
            "Diagnosis / Impression: Moderate Elevation in Creatinine & Blood Urea.",
            "Recommendation: Advised Nephrology Consult and Hydration."
        ]
    },
    {
        "filename": "report3_diabetes_thyroid.pdf",
        "title": "APOLLO HEALTH DIAGNOSTICS",
        "patient": "Patient Name: Robert Smith",
        "age_gender": "Age / Gender: 38 Yrs / Male",
        "doctor": "Referred By: Dr. Mark Vance",
        "date": "Date: 20/07/2025",
        "content": [
            "GLYCEMIC & THYROID EVALUATION",
            "--------------------------------------------------",
            "HbA1c (Glycated Hemoglobin) : 7.2 % (Reference Range: < 5.7 %) [High]",
            "Fasting Blood Glucose : 140 mg/dL (Reference Range: 70 - 99 mg/dL) [High]",
            "TSH (Thyroid Stimulating Hormone) : 2.5 uIU/mL (Reference Range: 0.4 - 4.2 uIU/mL)",
            "Total T3 : 1.2 ng/mL (Reference Range: 0.8 - 2.0 ng/mL)",
            "--------------------------------------------------",
            "Diagnosis / Impression: Type 2 Diabetes Mellitus with Normal Thyroid.",
            "Advised Dietary Control and Endocrine Follow-up."
        ]
    },
    {
        "filename": "report4_cardiology_ecg.pdf",
        "title": "ST. JUDE HEART INSTITUTE",
        "patient": "Patient Name: Emily Davis",
        "age_gender": "Age / Gender: 61 Yrs / Female",
        "doctor": "Referred By: Dr. Jonathan Ross, FACC",
        "date": "Date: 04/08/2025",
        "content": [
            "CARDIOLOGY EXAMINATION & ECG REPORT",
            "--------------------------------------------------",
            "Blood Pressure : 140/90 mmHg (Normal Range: < 120/80 mmHg) [High]",
            "Resting Heart Rate : 78 bpm (Normal Range: 60 - 100 bpm)",
            "ECG Impression : Sinus Rhythm with Non-Specific ST Segment Changes",
            "Ejection Fraction : 58 % (Normal Range: > 50 %)",
            "--------------------------------------------------",
            "Diagnosis / Impression: Mild Stage 1 Hypertension and Non-Specific ECG ST Changes.",
            "Recommendation: Advised 24-hr Holter Monitoring and Antihypertensive Therapy."
        ]
    },
    {
        "filename": "report5_infectious_serology.pdf",
        "title": "GLOBAL DIAGNOSTICS & PATHOLOGY",
        "patient": "Patient Name: Michael Brown",
        "age_gender": "Age / Gender: 29 Yrs / Male",
        "doctor": "Referred By: Dr. Lisa Kudrow",
        "date": "Date: 15/09/2025",
        "content": [
            "INFECTIOUS DISEASE SEROLOGY PANEL",
            "--------------------------------------------------",
            "HIV 1 & 2 Antibodies Screen : Non-Reactive (Reference: Non-Reactive)",
            "HBsAg (Hepatitis B Surface Antigen) : Negative",
            "HCV Antibodies : Negative",
            "VDRL / Syphilis Screen : Non-Reactive",
            "--------------------------------------------------",
            "Diagnosis / Impression: Serology Screening Negative for HIV 1&2 and Hepatitis.",
            "Report Status: Cleared for Routine Pre-Employment Health Check."
        ]
    }
]

def generate_pdf_reports():
    generated_paths = []
    for rep in REPORTS_DATA:
        doc = fitz.open()
        page = doc.new_page(width=595, height=842) # Standard A4 page size
        
        # Header Styling
        page.insert_text((50, 60), rep["title"], fontsize=18, color=(0.06, 0.72, 0.50)) # Emerald green
        page.insert_text((50, 95), rep["patient"], fontsize=11, color=(0.1, 0.1, 0.1))
        page.insert_text((50, 115), rep["age_gender"], fontsize=11, color=(0.1, 0.1, 0.1))
        page.insert_text((350, 95), rep["doctor"], fontsize=11, color=(0.1, 0.1, 0.1))
        page.insert_text((350, 115), rep["date"], fontsize=11, color=(0.1, 0.1, 0.1))

        # Divider line
        page.draw_line((50, 135), (545, 135), color=(0.8, 0.8, 0.8), width=1)

        # Body Content Lines
        y_cursor = 170
        for line in rep["content"]:
            if "REPORT" in line or "PANEL" in line or "EVALUATION" in line:
                page.insert_text((50, y_cursor), line, fontsize=13, color=(0.05, 0.50, 0.60))
            elif "[High]" in line or "Abnormal" in line:
                page.insert_text((50, y_cursor), line, fontsize=11, color=(0.85, 0.20, 0.20)) # Red highlight text
            else:
                page.insert_text((50, y_cursor), line, fontsize=11, color=(0.2, 0.2, 0.2))
            y_cursor += 24

        out_path = SAMPLES_DIR / rep["filename"]
        if not out_path.exists():
            try:
                doc.save(str(out_path))
            except Exception as e:
                pass
        doc.close()
        generated_paths.append(str(out_path))
        print(f"Generated sample PDF: {out_path}")

    return generated_paths

if __name__ == "__main__":
    generate_pdf_reports()
