import os
import uuid
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from pathlib import Path
from typing import List, Dict, Any, Tuple
from config import CROPS_DIR, CROP_DPI_SCALE
from logger import logger

class ScreenshotCropper:
    @staticmethod
    def crop_and_highlight(
        pdf_path: str,
        page_index: int,
        bounding_box: List[float],
        output_filename: str = None
    ) -> Tuple[str, str]:
        """
        Renders the PDF page at scale factor, crops target bounding box with padding,
        draws a sharp green highlight rectangle around the answer region,
        and saves as PNG in CROPS_DIR.
        
        Returns:
            (absolute_crop_file_path, relative_url_path)
        """
        if not output_filename:
            output_filename = f"crop_{uuid.uuid4().hex[:12]}.png"

        target_file_path = CROPS_DIR / output_filename

        doc = fitz.open(pdf_path)
        page = doc[page_index]
        page_rect = page.rect  # (0, 0, width, height) in PDF points

        x0, y0, x1, y1 = bounding_box

        # Render high-res page pixmap
        scale = CROP_DPI_SCALE
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Scale PDF points to pixmap image pixels
        px0 = x0 * scale
        py0 = y0 * scale
        px1 = x1 * scale
        py1 = y1 * scale

        # Add context padding around target box (extend horizontally, keep vertical tight)
        padding_x = 50 * scale
        padding_y = 2 * scale

        crop_x0 = max(0, px0 - padding_x)
        crop_y0 = max(0, py0 - padding_y)
        crop_x1 = min(img.width, px1 + padding_x)
        crop_y1 = min(img.height, py1 + padding_y)

        # Ensure minimum horizontal crop width for full row readability
        if (crop_x1 - crop_x0) < 300:
            margin = (300 - (crop_x1 - crop_x0)) / 2
            crop_x0 = max(0, crop_x0 - margin)
            crop_x1 = min(img.width, crop_x1 + margin)

        cropped_img = img.crop((crop_x0, crop_y0, crop_x1, crop_y1)).convert("RGBA")

        # Create overlay for green rectangle drawing
        overlay = Image.new("RGBA", cropped_img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Target box relative to crop image coordinates
        rel_x0 = px0 - crop_x0
        rel_y0 = py0 - crop_y0
        rel_x1 = px1 - crop_x0
        rel_y1 = py1 - crop_y0

        # Draw semi-transparent green highlight fill + solid green border (#10B981)
        fill_color = (16, 185, 129, 45)      # Emerald green ~18% alpha
        border_color = (16, 185, 129, 255)   # Solid emerald green
        line_width = int(3 * scale)

        draw.rectangle([rel_x0, rel_y0, rel_x1, rel_y1], fill=fill_color, outline=border_color, width=line_width)

        # Composite overlay onto cropped image
        final_img = Image.alpha_composite(cropped_img, overlay).convert("RGB")
        final_img.save(str(target_file_path), format="PNG")

        doc.close()
        logger.info(f"Saved crop screenshot to '{target_file_path}'")

        relative_url = f"/api/crops/{output_filename}"
        return str(target_file_path), relative_url
