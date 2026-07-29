"""
Quick test script for the experimental Gemini pipeline.
Run this to verify the pipeline works before wiring into the main app.

Usage:
    py experimental_gemini_pipeline/test_quick.py
"""

import sys
import os
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experimental_gemini_pipeline.gemini_client import GeminiClientManager
from experimental_gemini_pipeline.pdf_processor import crop_pdf_by_normalized_box

# -- ENV DIAGNOSTIC --
import os
from pathlib import Path as _P
from dotenv import load_dotenv as _ld
_env = _P(__file__).resolve().parent.parent / ".env"
_ld(dotenv_path=_env, encoding="utf-8-sig", override=True)
_key = os.getenv("PRIMARY_GEMINI_API_KEY", "")
print(f"[ENV] .env path   : {_env}")
print(f"[ENV] .env exists : {_env.exists()}")
print(f"[ENV] API key     : {'SET (' + _key[:8] + '...)' if _key else 'NOT FOUND - check .env file'}")
print()

# ----------------------------------------------------------------
# CONFIG - edit these before running
# ----------------------------------------------------------------
PDF_PATH = str(Path(__file__).resolve().parent.parent / "tests" / "samples" / "report6_manjit_singh.pdf")

QUESTIONS = [
    "What is the patient name?",
    "What is the hemoglobin level?",
    "What is the HbA1c value?",
    "What are the ECG findings?",
]
# ----------------------------------------------------------------

def run_test(question: str, output_dir: Path):
    print(f"\n{'='*60}")
    print(f"QUESTION : {question}")
    print(f"{'='*60}")

    manager = GeminiClientManager()
    result = manager.extract_bounding_box(PDF_PATH, question)

    print(f"[PAGE]       : {result.page_number}")
    print(f"[BOX_2D]     : {result.box_2d}  (ymin, xmin, ymax, xmax  — 0-1000 scale)")
    print(f"[ANSWER_TEXT]: {result.answer_text}")
    print(f"[LABEL]      : {result.label}")

    # Crop the region from the PDF
    slug = question[:30].replace(" ", "_").replace("?", "").lower()
    out_path = str(output_dir / f"crop_{slug}.png")

    crop_pdf_by_normalized_box(
        pdf_path=PDF_PATH,
        page_number=result.page_number,
        box_2d=result.box_2d,
        output_path=out_path,
    )
    print(f"[CROP]       : {out_path}")

if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent / "crops"
    output_dir.mkdir(exist_ok=True)

    print(f"\nPDF : {PDF_PATH}")
    print(f"Crops will be saved to: {output_dir}\n")

    passed = 0
    failed = 0

    for q in QUESTIONS:
        try:
            run_test(q, output_dir)
            passed += 1
        except Exception as e:
            print(f"[ERROR]   : {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed | {failed} failed out of {len(QUESTIONS)} questions")
    print(f"{'='*60}\n")
