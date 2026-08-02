try:
    from .gemini_client import GeminiClientManager, clean_extracted_value
    from .pdf_processor import crop_pdf_by_normalized_box
except ImportError:
    from gemini_client import GeminiClientManager, clean_extracted_value
    from pdf_processor import crop_pdf_by_normalized_box


def run_pipeline(pdf_file: str, user_question: str, output_image: str = "extracted_snippet.png"):
    """
    Full pipeline: Gemini visual grounding -> crop.
    Processes ALL results returned by Gemini.
    Only produces cropped images (no bounding box overlay — that is test-only).
    """
    manager = GeminiClientManager()

    print(f"Processing: {pdf_file}")
    print(f"Question: {user_question}\n")

    # Step 1: Gemini visual grounding (ALL results)
    grounding_result = manager.extract_bounding_boxes(pdf_file, user_question)

    if not grounding_result.results:
        print("No results found for this question.")
        return

    for idx, grounding in enumerate(grounding_result.results):
        result_num = idx + 1
        clean_answer = clean_extracted_value(grounding.answer_text, user_question)

        print(f"--- Result #{result_num} ---")
        print(f"  Page:   {grounding.page_number}")
        print(f"  BBox:   {grounding.box_2d}  [ymin, xmin, ymax, xmax] (0-1000)")
        print(f"  Label:  {grounding.label}")
        print(f"  Answer: {clean_answer}\n")

        # Step 2: Crop with answer_text and label for accurate multi-line refinement
        base, ext = output_image.rsplit(".", 1) if "." in output_image else (output_image, "png")
        crop_path = f"{base}_r{result_num}.{ext}" if len(grounding_result.results) > 1 else output_image

        crop_pdf_by_normalized_box(
            pdf_path=pdf_file,
            page_number=grounding.page_number,
            box_2d=grounding.box_2d,
            output_path=crop_path,
            answer_text=grounding.answer_text,
            label=grounding.label or "",
        )
        print(f"  Crop Image: {crop_path}\n")

    print(f"{len(grounding_result.results)} result(s) processed.")


def process_query(pdf_path: str, question: str, output_crop_path: str = None) -> dict:
    """
    Helper wrapper for process_query compatibility.
    Uses extract_bounding_boxes (all results) and passes answer_text/label
    to crop for multi-line refinement.
    Only returns crop_path — no bounding box overlay (frontend shows crop only).
    """
    out = output_crop_path or "crop_output.png"
    manager = GeminiClientManager()
    try:
        gbl = manager.extract_bounding_boxes(pdf_path, question)

        if not gbl.results:
            return {"result": {"found": False, "error": "No matching information found."}, "crop_path": None}

        gb = gbl.results[0]
        crop_path = crop_pdf_by_normalized_box(
            pdf_path, gb.page_number, gb.box_2d, out,
            answer_text=gb.answer_text, label=gb.label or ""
        )
        ans = clean_extracted_value(gb.answer_text, question)

        results_list = []
        for g in gbl.results:
            clean_val = clean_extracted_value(g.answer_text, question)
            results_list.append({
                "page_number": g.page_number,
                "page": g.page_number,
                "box_2d": g.box_2d,
                "bounding_box": g.box_2d,
                "matched_text": clean_val,
                "answer": clean_val,
                "label": g.label,
                "confidence": 0.99,
            })

        return {
            "result": {
                "found": True,
                "page": gb.page_number,
                "page_number": gb.page_number,
                "bounding_box": gb.box_2d,
                "box_2d": gb.box_2d,
                "matched_text": ans,
                "answer": ans,
                "confidence": 0.99,
                "results": results_list,
            },
            "crop_path": crop_path
        }
    except Exception as e:
        return {"result": {"found": False, "error": str(e)}, "crop_path": None}


if __name__ == "__main__":
    pdf_path = "U100723465AD0.pdf"
    question = "what was latitude and longitude of patient, give coordinates for entire region so that I can extract that part"

    run_pipeline(pdf_path, question, "extracted_gps_snippet.png")
