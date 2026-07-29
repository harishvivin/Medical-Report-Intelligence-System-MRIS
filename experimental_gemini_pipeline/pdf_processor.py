import fitz  # PyMuPDF

def crop_pdf_by_normalized_box(pdf_path: str, page_number: int, box_2d: list, output_path: str) -> str:
    """
    Converts 0-1000 normalized coordinates [ymin, xmin, ymax, xmax] to actual pixels
    and crops that exact region from the PDF page using PyMuPDF at 2x resolution.
    """
    ymin_1000, xmin_1000, ymax_1000, xmax_1000 = box_2d

    doc = fitz.open(pdf_path)
    page_idx = max(0, min(page_number - 1, len(doc) - 1))
    page = doc[page_idx]
    w, h = page.rect.width, page.rect.height

    left   = (xmin_1000 / 1000.0) * w
    top    = (ymin_1000 / 1000.0) * h
    right  = (xmax_1000 / 1000.0) * w
    bottom = (ymax_1000 / 1000.0) * h

    crop_rect = fitz.Rect(left, top, right, bottom)
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=crop_rect)
    pix.save(output_path)
    doc.close()

    print(f"[CROP] Saved: {output_path}")
    return output_path
