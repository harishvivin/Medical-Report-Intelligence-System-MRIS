"""
Main Pipeline Runner for Experimental Gemini Pipeline.
Processes user question for a PDF report:
1. Calls Gemini API to get answer visual coordinates (bounding box + page).
2. Uses PyMuPDF coordinate cropper to generate PNG crop.
3. Returns formatted result.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from .gemini_client import locate_answer_in_pdf
from .coordinate_cropper import crop_pdf_region


def process_query(pdf_path: str, question: str, output_crop_path: str = None) -> Dict[str, Any]:
    """
    Executes end-to-end experimental pipeline for a given PDF and question.

    Args:
        pdf_path: Path to input PDF file.
        question: User query string.
        output_crop_path: Optional custom path for output PNG crop.

    Returns:
        Dictionary containing:
        - "result": Gemini JSON output (found, page, bounding_box, matched_text, confidence)
        - "crop_path": Path to saved PNG crop image if found, else None
    """
    print(f"\n==================================================")
    print(f"Processing PDF: {pdf_path}")
    print(f"Question:       {question}")
    print(f"==================================================")

    # Step 1: Locate answer using Gemini API (Flash-Lite, temp=0.0)
    result = locate_answer_in_pdf(pdf_path, question)
    
    crop_path = None
    
    # Step 2: If found, extract sub-rectangle PNG crop using PyMuPDF
    if result.get("found") is True and "bounding_box" in result:
        page_num = result.get("page", 1)
        bbox = result.get("bounding_box", {})
        
        try:
            crop_path = crop_pdf_region(
                pdf_path=pdf_path,
                page_num=page_num,
                bbox=bbox,
                output_path=output_crop_path
            )
            result["crop_path"] = crop_path
            print(f"[SUCCESS] Crop successfully generated: {crop_path}")
        except Exception as e:
            print(f"[ERROR] Failed to generate crop: {e}")
            result["crop_error"] = str(e)
    else:
        print(f"[INFO] Answer not found or no bounding box returned.")

    print(f"\nPipeline Result JSON:")
    print(json.dumps(result, indent=2))
    
    return {
        "result": result,
        "crop_path": crop_path
    }


def main():
    parser = argparse.ArgumentParser(description="Experimental Gemini PDF Localization & Cropping Pipeline")
    parser.add_argument("--pdf", required=True, help="Path to input PDF report")
    parser.add_argument("--question", required=True, help="Question to query against the PDF")
    parser.add_argument("--output-crop", default=None, help="Optional output path for crop image")

    args = parser.parse_args()
    
    res = process_query(
        pdf_path=args.pdf,
        question=args.question,
        output_crop_path=args.output_crop
    )
    
    sys.exit(0 if res["result"].get("found") else 1)


if __name__ == "__main__":
    main()
