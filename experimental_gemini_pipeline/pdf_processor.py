from PIL import Image
import fitz  # PyMuPDF

def crop_pdf_by_normalized_box(pdf_path: str, page_number: int, box_2d: list[int], output_path: str) -> str:
    """
    Converts 0-1000 normalized coordinates [ymin, xmin, ymax, xmax] to actual pixels/points and crops the page.
    Uses PyMuPDF (fitz) for vector precision rendering with pdf2image fallback.
    """
    ymin_1000, xmin_1000, ymax_1000, xmax_1000 = box_2d

    try:
        # PyMuPDF vector rendering
        doc = fitz.open(pdf_path)
        page_idx = max(0, min(page_number - 1, len(doc) - 1))
        page = doc[page_idx]
        w, h = page.rect.width, page.rect.height

        left = (xmin_1000 / 1000.0) * w
        top = (ymin_1000 / 1000.0) * h
        right = (xmax_1000 / 1000.0) * w
        bottom = (ymax_1000 / 1000.0) * h

        crop_rect = fitz.Rect(left, top, right, bottom)
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=crop_rect)
        pix.save(output_path)
        doc.close()
        print(f"✅ Extracted snippet saved to: {output_path}")
        return output_path
    except Exception:
        # Fallback to pdf2image
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
            if not pages:
                raise ValueError(f"Could not render page {page_number} from PDF.")

            page_img = pages[0]
            img_width, img_height = page_img.size

            left = int((xmin_1000 / 1000.0) * img_width)
            top = int((ymin_1000 / 1000.0) * img_height)
            right = int((xmax_1000 / 1000.0) * img_width)
            bottom = int((ymax_1000 / 1000.0) * img_height)

            cropped_img = page_img.crop((left, top, right, bottom))
            cropped_img.save(output_path)
            
            print(f"✅ Extracted snippet saved to: {output_path}")
            return output_path
        except Exception as err:
            raise err
