from gemini_client import GeminiClientManager
from pdf_processor import crop_pdf_by_normalized_box

def run_pipeline(pdf_file: str, user_question: str, output_image: str = "extracted_snippet.png"):
    manager = GeminiClientManager()
    
    print(f"📄 Processing: {pdf_file}")
    print(f"❓ Prompt Question: {user_question}\n")
    
    # Step 1: Gemini visual grounding
    grounding = manager.extract_bounding_box(pdf_file, user_question)
    
    print(f"📍 Detected Page: {grounding.page_number}")
    print(f"🎯 Coordinates [ymin, xmin, ymax, xmax]: {grounding.box_2d}")
    print(f"🏷️ Label: {grounding.label}\n")

    # Step 2: Extract & Crop
    crop_pdf_by_normalized_box(
        pdf_path=pdf_file,
        page_number=grounding.page_number,
        box_2d=grounding.box_2d,
        output_path=output_image
    )

def process_query(pdf_path: str, question: str, output_crop_path: str = None) -> dict:
    """Helper wrapper for process_query compatibility."""
    out = output_crop_path or "crop_output.png"
    manager = GeminiClientManager()
    try:
        gb = manager.extract_bounding_box(pdf_path, question)
        crop_path = crop_pdf_by_normalized_box(pdf_path, gb.page_number, gb.box_2d, out)
        return {
            "result": {
                "found": True,
                "page": gb.page_number,
                "page_number": gb.page_number,
                "bounding_box": gb.box_2d,
                "box_2d": gb.box_2d,
                "matched_text": gb.label,
                "answer": gb.label,
                "confidence": 0.99
            },
            "crop_path": crop_path
        }
    except Exception as e:
        return {"result": {"found": False, "error": str(e)}, "crop_path": None}

if __name__ == "__main__":
    pdf_path = "U100723465AD0.pdf"
    question = "what was latitude and longitude of patient, give coordinates for entire region so that I can extract that part"
    
    run_pipeline(pdf_path, question, "extracted_gps_snippet.png")
