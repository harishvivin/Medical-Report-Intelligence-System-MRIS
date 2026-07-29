"""
Coordinate Cropper Module for Experimental Gemini Pipeline.
Uses PyMuPDF (fitz) to extract high-resolution image crops from PDF coordinates.
Strictly avoids OpenCV, OCR, or OS screenshots.
"""

from pathlib import Path
import fitz  # PyMuPDF
from .config import CROPS_DIR


def crop_pdf_region(
    pdf_path: str,
    page_num: int,
    bbox: dict,
    output_path: str = None,
    dpi: int = 200,
    padding_points: float = 10.0
) -> str:
    """
    Crop a specific bounding box region from a PDF page and save as PNG.

    Args:
        pdf_path: Path to the input PDF file.
        page_num: Page number (1-based index).
        bbox: Dictionary with keys 'x1', 'y1', 'x2', 'y2' representing coordinates.
              Accepts 0-1000 normalized scale or 0.0-1.0 float normalized scale.
        output_path: Destination path for the PNG crop. If None, saves in CROPS_DIR.
        dpi: Resolution for the output PNG crop (default 200 DPI for high clarity).
        padding_points: Margins to add around bounding box in PDF points (default 10pt).

    Returns:
        Absolute file path string of the saved PNG crop.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    doc = fitz.open(str(pdf_file))
    
    # Handle page index (1-based to 0-based conversion)
    total_pages = len(doc)
    page_idx = max(0, min(page_num - 1 if page_num >= 1 else 0, total_pages - 1))
    page = doc[page_idx]
    
    page_width = page.rect.width
    page_height = page.rect.height

    # Raw coordinates
    x1 = float(bbox.get("x1", 0))
    y1 = float(bbox.get("y1", 0))
    x2 = float(bbox.get("x2", 1000))
    y2 = float(bbox.get("y2", 1000))

    # Detect scale (0-1000 scale vs 0.0-1.0 float scale vs actual points)
    max_val = max(abs(x1), abs(y1), abs(x2), abs(y2))
    
    if max_val <= 1.0 and max_val > 0:
        # 0.0 - 1.0 float scale
        px1 = x1 * page_width
        py1 = y1 * page_height
        px2 = x2 * page_width
        py2 = y2 * page_height
    elif max_val <= 1000.0:
        # 0 - 1000 normalized scale (Standard Gemini visual output format)
        px1 = (x1 / 1000.0) * page_width
        py1 = (y1 / 1000.0) * page_height
        px2 = (x2 / 1000.0) * page_width
        py2 = (y2 / 1000.0) * page_height
    else:
        # Direct point coordinates
        px1, py1, px2, py2 = x1, y1, x2, y2

    # Ensure x1 < x2 and y1 < y2
    if px1 > px2:
        px1, px2 = px2, px1
    if py1 > py2:
        py1, py2 = py2, py1

    # Apply padding
    px1 = max(0.0, px1 - padding_points)
    py1 = max(0.0, py1 - padding_points)
    px2 = min(page_width, px2 + padding_points)
    py2 = min(page_height, py2 + padding_points)

    # Define PyMuPDF bounding rectangle
    crop_rect = fitz.Rect(px1, py1, px2, py2)

    # Render clip region to pixmap using matrix scaling for DPI
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, clip=crop_rect)

    # Determine destination output path
    if not output_path:
        stem = pdf_file.stem
        filename = f"crop_{stem}_p{page_idx + 1}_{int(px1)}_{int(py1)}.png"
        output_path = str(CROPS_DIR / filename)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_file))
    
    doc.close()
    return str(out_file.resolve())
