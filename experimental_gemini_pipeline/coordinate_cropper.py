"""
Coordinate Cropper Module.
Wrapper for pdf_processor.crop_pdf_by_normalized_box.
"""

from typing import Union, List, Dict, Any
from .pdf_processor import crop_pdf_by_normalized_box

def crop_pdf_region(
    pdf_path: str,
    page_num: int,
    bbox: Union[List[int], Dict[str, float]],
    output_path: str = None,
    dpi: int = 200,
    padding_points: float = 10.0
) -> str:
    if isinstance(bbox, dict):
        if "box_2d" in bbox and isinstance(bbox["box_2d"], (list, tuple)):
            box_2d = [int(v) for v in bbox["box_2d"]]
        else:
            x1 = int(bbox.get("x1", bbox.get("xmin", 0)))
            y1 = int(bbox.get("y1", bbox.get("ymin", 0)))
            x2 = int(bbox.get("x2", bbox.get("xmax", 1000)))
            y2 = int(bbox.get("y2", bbox.get("ymax", 1000)))
            box_2d = [y1, x1, y2, x2]
    else:
        box_2d = [int(v) for v in bbox]

    out = output_path or "crop_output.png"
    return crop_pdf_by_normalized_box(pdf_path, page_num, box_2d, out)
