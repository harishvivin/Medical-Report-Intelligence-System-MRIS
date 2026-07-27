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
        Extracts text blocks from all pages with page_number, bounding_box, text, normalized_text.
        bounding_box format: [x0, y0, x1, y1]
        """
        extracted_blocks = []
        block_id_counter = 0

        for page_idx in range(self.page_count):
            page = self.doc[page_idx]
            page_num = page_idx + 1

            # Get text dict from PyMuPDF which includes granular blocks, lines, spans
            page_dict = page.get_text("dict")
            blocks = page_dict.get("blocks", [])

            for b in blocks:
                # Type 0 is text block, Type 1 is image block
                if b.get("type", 0) != 0:
                    continue

                block_bbox = list(b.get("bbox", [0, 0, 0, 0]))
                lines = b.get("lines", [])
                
                block_text_lines = []
                spans_info = []

                for l in lines:
                    line_text = ""
                    for s in l.get("spans", []):
                        span_text = s.get("text", "")
                        if span_text:
                            line_text += span_text + " "
                            spans_info.append({
                                "text": span_text,
                                "bbox": list(s.get("bbox", [0, 0, 0, 0]))
                            })
                    if line_text.strip():
                        block_text_lines.append(line_text.strip())

                full_block_text = "\n".join(block_text_lines).strip()
                if not full_block_text:
                    continue

                extracted_blocks.append({
                    "id": block_id_counter,
                    "page_number": page_num,
                    "page_index": page_idx,
                    "bounding_box": [round(c, 2) for c in block_bbox],
                    "text": full_block_text,
                    "normalized_text": normalize_text(full_block_text),
                    "spans": spans_info
                })
                block_id_counter += 1

        logger.info(f"Extracted {len(extracted_blocks)} text blocks from PDF.")
        return extracted_blocks

    def get_page_pixmap(self, page_index: int, scale: float = 2.0) -> fitz.Pixmap:
        """Returns PyMuPDF pixmap rendered at specified scale factor."""
        page = self.doc[page_index]
        matrix = fitz.Matrix(scale, scale)
        return page.get_pixmap(matrix=matrix, alpha=False)

    def close(self):
        if self.doc:
            self.doc.close()
