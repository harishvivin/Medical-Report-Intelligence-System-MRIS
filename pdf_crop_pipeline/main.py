import shutil
from pathlib import Path

try:
    from .gemini_client import GeminiClientManager
    from .pdf_processor import crop_pdf_by_normalized_box
except ImportError:
    from gemini_client import GeminiClientManager
    from pdf_processor import crop_pdf_by_normalized_box

def run_pipeline(pdf_file: str, user_question: str, output_image: str = "extracted_snippet.png"):
    manager = GeminiClientManager()
    
    print(f"[PDF] Processing: {pdf_file}")
    print(f"[QUESTION] Query: {user_question}\n")
    
    # Step 1: Gemini visual grounding
    grounding = manager.extract_bounding_box(pdf_file, user_question)
    
    print(f"[PAGE] Detected Page: {grounding.page_number}")
    print(f"[COORDINATES] Coordinates [ymin, xmin, ymax, xmax]: {grounding.box_2d}")
    print(f"[LABEL] Label: {grounding.label}\n")

    # Step 2: Extract & Crop
    crop_pdf_by_normalized_box(
        pdf_path=pdf_file,
        page_number=grounding.page_number,
        box_2d=grounding.box_2d,
        output_path=output_image
    )

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    pdf_path = BASE_DIR / "U100723465AD0.pdf"
    
    if not pdf_path.exists():
        # Copy sample report report6_manjit_singh.pdf which contains Application No: U100723465AD0
        sample_pdf = BASE_DIR.parent / "tests" / "samples" / "report6_manjit_singh.pdf"
        if sample_pdf.exists():
            shutil.copy(sample_pdf, pdf_path)
            print(f"Copied sample PDF with Application No U100723465AD0 to {pdf_path}")

    question = "what was latitude and longitude of patient, give coordinates for entire region so that I can extract that part"
    
    run_pipeline(str(pdf_path), question, str(BASE_DIR / "extracted_gps_snippet.png"))
