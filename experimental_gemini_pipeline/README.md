# Experimental Gemini PDF Localization Pipeline

An isolated, lightweight, pure-Gemini experimental pipeline for visual answer localization and coordinate cropping on PDF medical reports.

> **IMPORTANT**: This pipeline operates independently inside `experimental_gemini_pipeline/`. It does **not** modify or interfere with the existing backend, FastAPI server, or frontend application.

---

## 🎯 Architecture & Objective

This solution completely eliminates traditional object detection models (YOLO, Grounding DINO, SAM, OpenCV object detectors).

```
User Uploads PDF
       ↓
Python Prompt Builder (f-string JSON specification)
       ↓
Gemini API (Flash-Lite Model, Temperature = 0.0)
[Primary Key -> Transparent Failover -> Fallback Key]
       ↓
Gemini Identifies Page Number + Normalized Bounding Box (0-1000 scale)
       ↓
PyMuPDF (fitz) Coordinate Cropper
       ↓
High-Resolution Output PNG Crop + Structured JSON Response
```

### Key Highlights:
1. **Zero Object Detector Dependencies**: No YOLO, Grounding DINO, SAM, OpenCV, or OCR models used.
2. **Pure Gemini Multimodal Intelligence**: Gemini Flash-Lite model is responsible strictly for locating answers directly within the uploaded PDF without using external medical knowledge.
3. **Dual API Key Failover**: Supports `GEMINI_API_KEY_PRIMARY` and `GEMINI_API_KEY_FALLBACK`. If any API error occurs (rate limits, quota exceeded, timeouts, transient network issues), retry occurs transparently with the fallback key.
4. **PyMuPDF Coordinate Cropper**: Precision sub-rectangle PNG rendering from normalized coordinates, strictly avoiding screenshots, OpenCV, or OCR.

---

## 📁 File Structure

```
experimental_gemini_pipeline/
├── __init__.py           # Package initialization
├── config.py             # Configuration for API keys, model, temperature, output paths
├── prompt_builder.py     # Prompt generation using Python f-strings
├── gemini_client.py       # Gemini API client with Primary -> Fallback failover workflow
├── coordinate_cropper.py # PyMuPDF coordinate scaling and PNG sub-rectangle rendering
├── main.py               # Main CLI runner for processing queries against a PDF
├── test_pipeline.py      # Automated unit & integration test suite
└── README.md             # Documentation
```

---

## ⚙️ Configuration & Environment Variables

Set the environment variables before running:

```bash
# Primary API Key
export GEMINI_API_KEY_PRIMARY="your_primary_gemini_api_key"

# Fallback API Key (Transparent Failover)
export GEMINI_API_KEY_FALLBACK="your_fallback_gemini_api_key"

# Optional Model Override (Defaults to gemini-2.5-flash-lite)
export GEMINI_MODEL="gemini-2.5-flash-lite"
```

---

## 🚀 CLI Usage

Run a query against a PDF report:

```bash
py experimental_gemini_pipeline/main.py --pdf "tests/samples/report1_blood_work.pdf" --question "What is the Hemoglobin level?"
```

### Output JSON Format:

```json
{
  "found": true,
  "page": 1,
  "bounding_box": {
    "x1": 150,
    "y1": 220,
    "x2": 650,
    "y2": 320
  },
  "matched_text": "Hemoglobin : 14.8 g/dL (Reference Range: 13.5 - 17.5 g/dL)",
  "confidence": 0.99,
  "api_key_used": "PRIMARY",
  "crop_path": "c:/Users/.../experimental_gemini_pipeline/crops/crop_report1_blood_work_p1_150_220.png"
}
```

If the answer is missing from the document:

```json
{
  "found": false
}
```

---

## 🧪 Testing

Run the automated test harness covering all required medical questions (*Patient Name, Hospital Name, Creatinine, HbA1c, Hemoglobin, Blood Pressure, Diagnosis, ECG, HIV, Summary*):

```bash
py -m unittest experimental_gemini_pipeline/test_pipeline.py
```
