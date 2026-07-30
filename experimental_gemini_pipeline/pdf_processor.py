import fitz  # PyMuPDF
from PIL import Image

def crop_pdf_by_normalized_box(pdf_path: str, page_number: int, box_2d: list, output_path: str) -> str:
    """
    Converts 0-1000 normalized coordinates [ymin, xmin, ymax, xmax] to actual pixels
    and crops the region with generous padding so the name, values, and context are clearly visible.

    Ensures proper width and height padding without forcing unnatural 90-degree text rotations.
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

    # ── Generous Padding to guarantee name, values & context are visible ───────
    # Add 15% page width padding to the left and right (captures labels + values)
    # Add 2.5% page height padding to top and bottom (captures full text height)
    pad_x = 0.15 * w
    pad_y = max(12.0, 0.025 * h)

    left   = max(0.0, xmin_px - pad_x)
    right  = min(w,   xmax_px + pad_x)
    top    = max(0.0, ymin_px - pad_y)
    bottom = min(h,   ymax_px + pad_y)

    # ── Enforce Minimum Readable Dimensions ───────────────────────────────────
    # Minimum crop width = 300pt (or full page if page is narrower)
    # Minimum crop height = 50pt
    MIN_WIDTH  = min(300.0, w)
    MIN_HEIGHT = min(50.0, h)

    current_w = right - left
    if current_w < MIN_WIDTH:
        needed = (MIN_WIDTH - current_w) / 2.0
        left  = max(0.0, left - needed)
        right = min(w,   right + needed)

    current_h = bottom - top
    if current_h < MIN_HEIGHT:
        needed = (MIN_HEIGHT - current_h) / 2.0
        top    = max(0.0, top - needed)
        bottom = min(h,   bottom + needed)

    # ── Execute High-Resolution Crop (2x DPI matrix for crisp text) ────────────
    crop_rect = fitz.Rect(left, top, right, bottom)
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=crop_rect)
    pix.save(output_path)
    doc.close()

    print(f"[CROP SUCCESS] Saved readable crop: {output_path} | Size: {right-left:.0f}x{bottom-top:.0f}pt")
    return output_path
