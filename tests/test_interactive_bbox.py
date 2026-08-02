"""
Interactive Bounding Box Test Script
=====================================
Hardcoded PDF input. Ask questions from the terminal.
The script will:
  1. Send the question + PDF to the Gemini visual grounding pipeline
  2. Draw the detected bounding box on the full-page render
  3. Save the annotated output image with bounding box overlay
  4. Save the cropped region as a separate image

Usage:
    py tests/test_interactive_bbox.py
"""

import os
import sys
import io
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime

# Fix Windows terminal encoding for Unicode characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# -- Resolve project root and add to sys.path --
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experimental_gemini_pipeline.gemini_client import GeminiClientManager, clean_extracted_value
from experimental_gemini_pipeline.pdf_processor import crop_pdf_by_normalized_box

# =============================================================================
# HARDCODED PDF PATH -- Change this to your target PDF
# =============================================================================
HARDCODED_PDF = r"C:\Users\haris\Downloads\U100723465AD0.pdf"

# Output directory for annotated images
OUTPUT_DIR = PROJECT_ROOT / "tests" / "bbox_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def render_page_with_bbox(
    pdf_path: str,
    page_number: int,
    box_2d: list,
    answer_text: str,
    label: str,
    output_path: str,
) -> str:
    """
    Renders the full PDF page as an image and draws a colored bounding box
    with a label overlay on top.

    Args:
        pdf_path: Path to the PDF file
        page_number: 1-based page number
        box_2d: [ymin, xmin, ymax, xmax] normalized to 0-1000
        answer_text: The extracted answer text
        label: The field label
        output_path: Where to save the annotated image

    Returns:
        The output path of the saved image
    """
    doc = fitz.open(pdf_path)
    page_idx = max(0, min(page_number - 1, len(doc) - 1))
    page = doc[page_idx]
    w, h = page.rect.width, page.rect.height

    # Convert 0-1000 normalized coordinates to actual page points
    ymin_1000, xmin_1000, ymax_1000, xmax_1000 = box_2d
    xmin_pt = (xmin_1000 / 1000.0) * w
    ymin_pt = (ymin_1000 / 1000.0) * h
    xmax_pt = (xmax_1000 / 1000.0) * w
    ymax_pt = (ymax_1000 / 1000.0) * h

    # Render the full page at 2x resolution for crisp output
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Scale bounding box coordinates to match the rendered image
    sx = pix.width / w
    sy = pix.height / h

    x0 = int(xmin_pt * sx)
    y0 = int(ymin_pt * sy)
    x1 = int(xmax_pt * sx)
    y1 = int(ymax_pt * sy)

    # -- Draw bounding box rectangle --
    # Use a bright red rectangle (RGB)
    bbox_color = (255, 40, 40)
    thickness = 3

    # Draw the rectangle by drawing 4 lines on the pixmap
    # Top edge
    for t in range(thickness):
        for px_x in range(max(0, x0), min(pix.width, x1)):
            _set_pixel(pix, px_x, max(0, y0 + t), bbox_color)
    # Bottom edge
    for t in range(thickness):
        for px_x in range(max(0, x0), min(pix.width, x1)):
            _set_pixel(pix, px_x, min(pix.height - 1, y1 - t), bbox_color)
    # Left edge
    for t in range(thickness):
        for px_y in range(max(0, y0), min(pix.height, y1)):
            _set_pixel(pix, max(0, x0 + t), px_y, bbox_color)
    # Right edge
    for t in range(thickness):
        for px_y in range(max(0, y0), min(pix.height, y1)):
            _set_pixel(pix, min(pix.width - 1, x1 - t), px_y, bbox_color)

    # -- Draw semi-transparent fill inside the bounding box --
    fill_color = (255, 80, 80)  # Light red tint
    alpha = 0.15  # 15% opacity overlay
    for py in range(max(0, y0 + thickness), min(pix.height, y1 - thickness)):
        for px_x in range(max(0, x0 + thickness), min(pix.width, x1 - thickness)):
            _blend_pixel(pix, px_x, py, fill_color, alpha)

    # -- Draw label background bar above the bounding box --
    label_text = f"{label}: {answer_text}" if label else answer_text
    bar_height = 28
    bar_y_start = max(0, y0 - bar_height)
    bar_y_end = y0
    label_bg_color = (220, 40, 40)

    for py in range(bar_y_start, bar_y_end):
        for px_x in range(max(0, x0), min(pix.width, x1)):
            _set_pixel(pix, px_x, py, label_bg_color)

    # Save the annotated image
    pix.save(output_path)
    doc.close()
    return output_path


def _set_pixel(pix, x: int, y: int, color: tuple):
    """Set a pixel color on a PyMuPDF Pixmap (RGB)."""
    if 0 <= x < pix.width and 0 <= y < pix.height:
        pix.set_pixel(x, y, color)


def _blend_pixel(pix, x: int, y: int, color: tuple, alpha: float):
    """Blend a color onto an existing pixel with transparency."""
    if 0 <= x < pix.width and 0 <= y < pix.height:
        existing = pix.pixel(x, y)  # returns (r, g, b) or (r, g, b, a)
        r = int(existing[0] * (1 - alpha) + color[0] * alpha)
        g = int(existing[1] * (1 - alpha) + color[1] * alpha)
        b = int(existing[2] * (1 - alpha) + color[2] * alpha)
        pix.set_pixel(x, y, (r, g, b))


def sanitize_filename(text: str, max_len: int = 40) -> str:
    """Convert text to a safe filename fragment."""
    safe = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in text)
    safe = safe.strip().replace(' ', '_')
    return safe[:max_len]


def run_interactive_session():
    """Main interactive loop: ask questions, get bounding boxes, save annotated images."""

    # -- Validate hardcoded PDF exists --
    if not Path(HARDCODED_PDF).exists():
        print(f"\n[ERROR] Hardcoded PDF not found at:")
        print(f"   {HARDCODED_PDF}")
        print(f"\n   Please update HARDCODED_PDF in this script to point to a valid PDF.")
        sys.exit(1)

    pdf_name = Path(HARDCODED_PDF).stem

    print("")
    print("=" * 70)
    print("  MEDICAL REPORT BOUNDING BOX ANALYZER")
    print("=" * 70)
    print(f"  PDF:    {HARDCODED_PDF}")
    print(f"  Output: {OUTPUT_DIR}")
    print("-" * 70)
    print("  Type your question and press Enter.")
    print("  Type 'quit' or 'exit' to stop.")
    print("")

    manager = GeminiClientManager()
    question_count = 0

    while True:
        try:
            question = input("[?] Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n[BYE] Session ended.")
            break

        if not question:
            print("   [WARN] Please enter a question.\n")
            continue

        if question.lower() in ("quit", "exit", "q"):
            print("\n[BYE] Session ended. Goodbye!")
            break

        question_count += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_q = sanitize_filename(question)

        print(f"\n{'-' * 60}")
        print(f"  Analyzing: \"{question}\"")
        print(f"{'-' * 60}")

        try:
            # -- Step 1: Gemini Visual Grounding --
            print("  [WAIT] Sending to Gemini for visual grounding...")
            grounding_result = manager.extract_bounding_boxes(HARDCODED_PDF, question)

            if not grounding_result.results:
                print("  [WARN] No results found for this question.\n")
                continue

            # -- Process each result --
            for idx, grounding in enumerate(grounding_result.results):
                result_num = idx + 1
                clean_answer = clean_extracted_value(grounding.answer_text, question)

                print(f"\n  --- Result #{result_num} ---")
                print(f"     Page:       {grounding.page_number}")
                print(f"     BBox:       {grounding.box_2d}  [ymin, xmin, ymax, xmax] (0-1000)")
                print(f"     Label:      {grounding.label}")
                print(f"     Answer:     {clean_answer}")

                # -- Step 2: Render full page with bounding box overlay --
                bbox_filename = f"{timestamp}_{pdf_name}_{safe_q}_r{result_num}_bbox.png"
                bbox_output = str(OUTPUT_DIR / bbox_filename)

                render_page_with_bbox(
                    pdf_path=HARDCODED_PDF,
                    page_number=grounding.page_number,
                    box_2d=grounding.box_2d,
                    answer_text=clean_answer,
                    label=grounding.label or "",
                    output_path=bbox_output,
                )
                print(f"     BBox Image: {bbox_filename}")

                # -- Step 3: Save cropped region --
                crop_filename = f"{timestamp}_{pdf_name}_{safe_q}_r{result_num}_crop.png"
                crop_output = str(OUTPUT_DIR / crop_filename)

                crop_pdf_by_normalized_box(
                    pdf_path=HARDCODED_PDF,
                    page_number=grounding.page_number,
                    box_2d=grounding.box_2d,
                    output_path=crop_output,
                    answer_text=grounding.answer_text,
                    label=grounding.label or "",
                )
                print(f"     Crop Image: {crop_filename}")

            print(f"\n  [OK] {len(grounding_result.results)} result(s) saved to: {OUTPUT_DIR}\n")

        except Exception as e:
            print(f"\n  [ERROR] {e}\n")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    run_interactive_session()
