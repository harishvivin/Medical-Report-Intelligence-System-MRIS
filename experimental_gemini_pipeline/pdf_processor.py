import fitz  # PyMuPDF
from PIL import Image

def crop_pdf_by_normalized_box(pdf_path: str, page_number: int, box_2d: list, output_path: str) -> str:
    """
    Converts 0-1000 normalized coordinates [ymin, xmin, ymax, xmax] to actual pixels
    and crops the exact row with tight vertical boundaries to prevent bleeding into adjacent rows.

    Extends horizontally to capture full row context (labels + values).
    """
    ymin_1000, xmin_1000, ymax_1000, xmax_1000 = box_2d

    doc = fitz.open(pdf_path)
    page_idx = max(0, min(page_number - 1, len(doc) - 1))
    page = doc[page_idx]
    w, h = page.rect.width, page.rect.height

    # Convert 0-1000 normalized coordinates to actual page pixels
    ymin_px = (ymin_1000 / 1000.0) * h
    xmin_px = (xmin_1000 / 1000.0) * w
    ymax_px = (ymax_1000 / 1000.0) * h
    xmax_px = (xmax_1000 / 1000.0) * w

    # ── Precision Row Padding ──────────────────────────────────────────────────
    # Horizontal (X): Extend 25% of page width left & right to capture full row context.
    # Vertical (Y): Use tight 2.0pt padding to NEVER bleed into adjacent rows above/below.
    pad_x = 0.25 * w
    pad_y = 2.0  # Tight 2pt vertical padding prevents capturing adjacent rows

    left   = max(0.0, xmin_px - pad_x)
    right  = min(w,   xmax_px + pad_x)
    top    = max(0.0, ymin_px - pad_y)
    bottom = min(h,   ymax_px + pad_y)

    # ── Enforce Minimum Readable Width ────────────────────────────────────────
    # Ensure crop width is at least 350pt so the full table row (label + value) is visible.
    MIN_WIDTH = min(350.0, w)
    current_w = right - left
    if current_w < MIN_WIDTH:
        needed = (MIN_WIDTH - current_w) / 2.0
        left  = max(0.0, left - needed)
        right = min(w,   right + needed)

    # ── Execute High-Resolution Crop (2x DPI matrix for crisp text) ────────────
    crop_rect = fitz.Rect(left, top, right, bottom)
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=crop_rect)
    pix.save(output_path)
    doc.close()

    print(f"[CROP SUCCESS] Saved row crop: {output_path} | Size: {right-left:.0f}x{bottom-top:.0f}pt")
    return output_path
