"""
Coordinate Cropper Module for Experimental Gemini Pipeline.
Uses PyMuPDF (fitz) to extract high-resolution image crops from PDF coordinates.
Strictly avoids OpenCV, OCR, or OS screenshots.
"""

from pathlib import Path
from typing import Union, List, Dict, Any
import fitz  # PyMuPDF
from .config import CROPS_DIR


def crop_pdf_region(
    pdf_path: str,
    page_num: int,
    bbox: Union[List[float], Dict[str, float]],
    output_path: str = None,
    dpi: int = 200,
    padding_points: float = 10.0
) -> str:
    """
    Crop a specific bounding box region from a PDF page and save as PNG.

    Args:
        pdf_path: Path to the input PDF file.
        page_num: Page number (1-based index).
        bbox: Bounding box as either:
              - list: [ymin, xmin, ymax, xmax] (normalized 0-1000 scale)
              - dict: {'x1', 'y1', 'x2', 'y2'} or {'ymin', 'xmin', 'ymax', 'xmax'}
        output_path: Destination path for the PNG crop. If None, saves in CROPS_DIR.
        dpi: Resolution for the output PNG crop (default 200 DPI).
        padding_points: Margins to add around bounding box in PDF points (default 10pt).

    Returns:
        Absolute file path string of the saved PNG crop.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    doc = fitz.open(str(pdf_file))
    
    total_pages = len(doc)
    page_idx = max(0, min(page_num - 1 if page_num >= 1 else 0, total_pages - 1))
    page = doc[page_idx]
    
    page_width = page.rect.width
    page_height = page.rect.height

    # Parse bbox formats
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        # Format: [ymin, xmin, ymax, xmax]
        ymin, xmin, ymax, xmax = [float(v) for v in bbox]
        # Check scale (0-1 float vs 0-1000 int)
        max_val = max(abs(ymin), abs(xmin), abs(ymax), abs(xmax))
        if max_val <= 1.0 and max_val > 0:
            px1 = xmin * page_width
            py1 = ymin * page_height
            px2 = xmax * page_width
            py2 = ymax * page_height
        elif max_val <= 1000.0:
            px1 = (xmin / 1000.0) * page_width
            py1 = (ymin / 1000.0) * page_height
            px2 = (xmax / 1000.0) * page_width
            py2 = (ymax / 1000.0) * page_height
        else:
            px1, py1, px2, py2 = xmin, ymin, xmax, ymax
    elif isinstance(bbox, dict):
        if "box_2d" in bbox and isinstance(bbox["box_2d"], (list, tuple)):
            return crop_pdf_region(pdf_path, page_num, bbox["box_2d"], output_path, dpi, padding_points)
        x1 = float(bbox.get("x1", bbox.get("xmin", 0)))
        y1 = float(bbox.get("y1", bbox.get("ymin", 0)))
        x2 = float(bbox.get("x2", bbox.get("xmax", 1000)))
        y2 = float(bbox.get("y2", bbox.get("ymax", 1000)))
        max_val = max(abs(x1), abs(y1), abs(x2), abs(y2))
        if max_val <= 1.0 and max_val > 0:
            px1, py1, px2, py2 = x1 * page_width, y1 * page_height, x2 * page_width, y2 * page_height
        elif max_val <= 1000.0:
            px1, py1, px2, py2 = (x1 / 1000.0) * page_width, (y1 / 1000.0) * page_height, (x2 / 1000.0) * page_width, (y2 / 1000.0) * page_height
        else:
            px1, py1, px2, py2 = x1, y1, x2, y2
    else:
        px1, py1, px2, py2 = 0, 0, page_width, page_height

    # Ensure min < max
    if px1 > px2:
        px1, px2 = px2, px1
    if py1 > py2:
        py1, py2 = py2, py1

    # Apply padding
    px1 = max(0.0, px1 - padding_points)
    py1 = max(0.0, py1 - padding_points)
    px2 = min(page_width, px2 + padding_points)
    py2 = min(page_height, py2 + padding_points)

    crop_rect = fitz.Rect(px1, py1, px2, py2)

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, clip=crop_rect)

    if not output_path:
        stem = pdf_file.stem
        filename = f"crop_{stem}_p{page_idx + 1}_{int(px1)}_{int(py1)}.png"
        output_path = str(CROPS_DIR / filename)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_file))
    
    doc.close()
    return str(out_file.resolve())
