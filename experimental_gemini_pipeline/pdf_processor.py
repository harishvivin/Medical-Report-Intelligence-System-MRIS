import fitz  # PyMuPDF
from typing import Tuple, List, Optional

def refine_box_with_pymupdf(
    page: fitz.Page,
    box_2d: list,
    answer_text: str = "",
    label: str = ""
) -> Tuple[list, list]:
    """
    Refines 0-1000 normalized coordinates [ymin, xmin, ymax, xmax] using PyMuPDF word/line
    level text analysis. Matches the exact line containing answer_text or label on the page
    closest to Gemini's estimated y-center.

    Returns:
        (refined_box_2d_1000, refined_pt_bbox_points)
    """
    w, h = page.rect.width, page.rect.height
    ymin_1000, xmin_1000, ymax_1000, xmax_1000 = box_2d

    g_ymin = (ymin_1000 / 1000.0) * h
    g_ymax = (ymax_1000 / 1000.0) * h
    g_ycenter = (g_ymin + g_ymax) / 2.0

    words = page.get_text("words")
    if not words:
        pt_bbox = [
            round((xmin_1000 / 1000.0) * w, 2),
            round((ymin_1000 / 1000.0) * h, 2),
            round((xmax_1000 / 1000.0) * w, 2),
            round((ymax_1000 / 1000.0) * h, 2),
        ]
        return box_2d, pt_bbox

    # Group words into line objects
    lines_dict = {}
    for x0, y0, x1, y1, word, block_no, line_no, _ in words:
        key = (block_no, line_no)
        lines_dict.setdefault(key, []).append((x0, y0, x1, y1, word))

    lines = []
    for key, l_words in lines_dict.items():
        lx0 = min(w[0] for w in l_words)
        ly0 = min(w[1] for w in l_words)
        lx1 = max(w[2] for w in l_words)
        ly1 = max(w[3] for w in l_words)
        ltext = " ".join(w[4] for w in l_words)
        lines.append({
            "x0": lx0, "y0": ly0, "x1": lx1, "y1": ly1,
            "text": ltext, "ycenter": (ly0 + ly1) / 2.0
        })

    target_ans = (answer_text or "").strip().lower()
    clean_num = "".join(c for c in target_ans if c.isdigit())
    target_lbl = (label or "").strip().lower()

    best_line = None
    min_dist = float("inf")

    # Priority 1: Line containing BOTH label and answer_text / number
    if target_lbl and (target_ans or clean_num):
        for line in lines:
            l_text = line["text"].lower()
            lbl_match = any(word in l_text for word in target_lbl.split() if len(word) > 2)
            ans_match = (target_ans in l_text) or (clean_num and len(clean_num) >= 2 and clean_num in l_text)
            if lbl_match and ans_match:
                dist = abs(line["ycenter"] - g_ycenter)
                if dist < min_dist:
                    min_dist = dist
                    best_line = line

    # Priority 2: Line containing answer_text or clean_num
    if not best_line and (target_ans or clean_num):
        for line in lines:
            l_text = line["text"].lower()
            match = False
            if target_ans and len(target_ans) >= 2 and target_ans in l_text:
                match = True
            elif clean_num and len(clean_num) >= 2 and clean_num in l_text:
                match = True

            if match:
                dist = abs(line["ycenter"] - g_ycenter)
                if dist < min_dist:
                    min_dist = dist
                    best_line = line

    # Priority 3: Line containing label context near g_ycenter
    if not best_line and target_lbl:
        for line in lines:
            l_text = line["text"].lower()
            if any(word in l_text for word in target_lbl.split() if len(word) > 2):
                dist = abs(line["ycenter"] - g_ycenter)
                if dist < min_dist:
                    min_dist = dist
                    best_line = line

    # If matching line found within 120pt (~15% page height) of Gemini center
    if best_line and min_dist < 120.0:
        new_ymin = max(0.0, best_line["y0"] - 2.0)
        new_ymax = min(h, best_line["y1"] + 2.0)

        # Extend x-bounds slightly if line spans across row
        new_xmin = min((xmin_1000 / 1000.0) * w, best_line["x0"])
        new_xmax = max((xmax_1000 / 1000.0) * w, best_line["x1"])

        ref_ymin_1000 = int(round((new_ymin / h) * 1000.0))
        ref_ymax_1000 = int(round((new_ymax / h) * 1000.0))
        ref_xmin_1000 = int(round((new_xmin / w) * 1000.0))
        ref_xmax_1000 = int(round((new_xmax / w) * 1000.0))

        ref_box_2d = [ref_ymin_1000, ref_xmin_1000, ref_ymax_1000, ref_xmax_1000]
        pt_bbox = [round(new_xmin, 2), round(new_ymin, 2), round(new_xmax, 2), round(new_ymax, 2)]
        return ref_box_2d, pt_bbox

    # Fallback to unrefined Gemini coordinates
    pt_bbox = [
        round((xmin_1000 / 1000.0) * w, 2),
        round((ymin_1000 / 1000.0) * h, 2),
        round((xmax_1000 / 1000.0) * w, 2),
        round((ymax_1000 / 1000.0) * h, 2),
    ]
    return box_2d, pt_bbox

def crop_pdf_by_normalized_box(
    pdf_path: str,
    page_number: int,
    box_2d: list,
    output_path: str,
    answer_text: str = "",
    label: str = ""
) -> Tuple[list, list]:
    """
    Converts 0-1000 normalized coordinates [ymin, xmin, ymax, xmax] to actual pixels
    and crops the exact row with tight vertical boundaries to prevent bleeding into adjacent rows.

    Uses PyMuPDF word analysis to refine row alignment matching answer_text or label.
    Returns:
        (refined_box_2d, refined_pt_bbox)
    """
    doc = fitz.open(pdf_path)
    page_idx = max(0, min(page_number - 1, len(doc) - 1))
    page = doc[page_idx]
    w, h = page.rect.width, page.rect.height

    # Refine bounding box with exact text line coordinates if text match exists
    refined_box_2d, pt_bbox = refine_box_with_pymupdf(page, box_2d, answer_text, label)

    ymin_1000, xmin_1000, ymax_1000, xmax_1000 = refined_box_2d

    # Convert 0-1000 normalized coordinates to actual page pixels
    ymin_px = (ymin_1000 / 1000.0) * h
    xmin_px = (xmin_1000 / 1000.0) * w
    ymax_px = (ymax_1000 / 1000.0) * h
    xmax_px = (xmax_1000 / 1000.0) * w

    # ── Precision Row Padding ──────────────────────────────────────────────────
    # Horizontal (X): Extend 25% of page width left & right to capture full row context.
    # Vertical (Y): 6pt top padding / 4pt bottom padding for clean row crop.
    pad_x = 0.25 * w
    pad_y_top = 6.0
    pad_y_bottom = 4.0

    left   = max(0.0, xmin_px - pad_x)
    right  = min(w,   xmax_px + pad_x)
    top    = max(0.0, ymin_px - pad_y_top)
    bottom = min(h,   ymax_px + pad_y_bottom)

    # ── Enforce Minimum Readable Width ────────────────────────────────────────
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
    return refined_box_2d, pt_bbox
