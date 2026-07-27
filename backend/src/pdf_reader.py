import fitz  # PyMuPDF
import re
from typing import List, Dict, Any, Tuple
from logger import logger

def normalize_text(text: str) -> str:
    """Normalize text for consistent searching: lowercasing, removing extra whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

class PDFReader:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.page_count = len(self.doc)
        logger.info(f"Loaded PDF '{pdf_path}' with {self.page_count} page(s).")

    def extract_all_text_blocks(self) -> List[Dict[str, Any]]:
        """
        Extracts text blocks, visual horizontal rows, and key-value segments from all pages.
        Each entry has page_number, page_index, bounding_box [x0, y0, x1, y1], text, normalized_text, and type.
        """
        extracted_entries = []
        entry_id_counter = 0

        for page_idx in range(self.page_count):
            page = self.doc[page_idx]
            page_num = page_idx + 1

            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])

            lines_with_bbox = []

            for b in blocks:
                if b.get("type", 0) != 0:
                    continue

                block_bbox = list(b.get("bbox", [0, 0, 0, 0]))
                lines = b.get("lines", [])
                
                block_text_lines = []

                for l in lines:
                    line_text = ""
                    for s in l.get("spans", []):
                        span_text = s.get("text", "")
                        if span_text:
                            line_text += span_text + " "

                    line_str = line_text.strip()
                    if line_str:
                        l_bbox = list(l.get("bbox", [0, 0, 0, 0]))
                        block_text_lines.append(line_str)
                        lines_with_bbox.append({
                            "text": line_str,
                            "bbox": l_bbox,
                            "y_mid": (l_bbox[1] + l_bbox[3]) / 2.0
                        })

                full_block_text = "\n".join(block_text_lines).strip()
                if full_block_text:
                    extracted_entries.append({
                        "id": entry_id_counter,
                        "page_number": page_num,
                        "page_index": page_idx,
                        "bounding_box": [round(c, 2) for c in block_bbox],
                        "text": full_block_text,
                        "normalized_text": normalize_text(full_block_text),
                        "type": "block"
                    })
                    entry_id_counter += 1

            # Extract Aligned Horizontal Visual Rows & Key-Value Segments across columns
            lines_with_bbox.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
            grouped_rows = []
            for line in lines_with_bbox:
                matched_group = None
                for group in grouped_rows:
                    avg_y = sum(item["y_mid"] for item in group) / len(group)
                    if abs(line["y_mid"] - avg_y) <= 6.0:
                        matched_group = group
                        break

                if matched_group:
                    matched_group.append(line)
                else:
                    grouped_rows.append([line])

            for group in grouped_rows:
                group.sort(key=lambda item: item["bbox"][0])
                
                full_row_text = " ".join([item["text"] for item in group]).strip()
                full_row_text = re.sub(r'\s+:\s+', ' : ', full_row_text)

                row_min_x = min(item["bbox"][0] for item in group)
                row_min_y = min(item["bbox"][1] for item in group)
                row_max_x = max(item["bbox"][2] for item in group)
                row_max_y = max(item["bbox"][3] for item in group)
                parent_row_bbox = [round(row_min_x, 2), round(row_min_y, 2), round(row_max_x, 2), round(row_max_y, 2)]

                # Split row into key-value segments if there are horizontal column gaps (>22pt)
                current_seg = [group[0]]
                row_segments = []

                for i in range(1, len(group)):
                    prev_item = group[i-1]
                    curr_item = group[i]
                    gap = curr_item["bbox"][0] - prev_item["bbox"][2]

                    if gap > 22.0 or (prev_item["text"] == ":" and gap > 5.0):
                        row_segments.append(current_seg)
                        current_seg = [curr_item]
                    else:
                        current_seg.append(curr_item)

                if current_seg:
                    row_segments.append(current_seg)

                # Store segments if row had multiple columns
                if len(row_segments) > 1:
                    for seg in row_segments:
                        seg_text = " ".join([item["text"] for item in seg]).strip()
                        seg_text = re.sub(r'\s+:\s+', ' : ', seg_text)
                        if len(seg_text) >= 2:
                            min_x = min(item["bbox"][0] for item in seg)
                            min_y = min(item["bbox"][1] for item in seg)
                            max_x = max(item["bbox"][2] for item in seg)
                            max_y = max(item["bbox"][3] for item in seg)

                            extracted_entries.append({
                                "id": entry_id_counter,
                                "page_number": page_num,
                                "page_index": page_idx,
                                "bounding_box": [round(min_x, 2), round(min_y, 2), round(max_x, 2), round(max_y, 2)],
                                "parent_row_bbox": parent_row_bbox,
                                "full_row_text": full_row_text,
                                "text": seg_text,
                                "normalized_text": normalize_text(seg_text),
                                "type": "segment"
                            })
                            entry_id_counter += 1

                # Store merged visual row
                if full_row_text:
                    extracted_entries.append({
                        "id": entry_id_counter,
                        "page_number": page_num,
                        "page_index": page_idx,
                        "bounding_box": parent_row_bbox,
                        "parent_row_bbox": parent_row_bbox,
                        "full_row_text": full_row_text,
                        "text": full_row_text,
                        "normalized_text": normalize_text(full_row_text),
                        "type": "row"
                    })
                    entry_id_counter += 1

        logger.info(f"Extracted {len(extracted_entries)} text entries (blocks, rows & segments) from PDF.")
        return extracted_entries

    def get_page_pixmap(self, page_index: int, scale: float = 2.5) -> fitz.Pixmap:
        """Returns PyMuPDF pixmap rendered at specified scale factor."""
        page = self.doc[page_index]
        matrix = fitz.Matrix(scale, scale)
        return page.get_pixmap(matrix=matrix, alpha=False)

    def close(self):
        if self.doc:
            self.doc.close()

