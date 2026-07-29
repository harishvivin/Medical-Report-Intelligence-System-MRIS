"""
PDF Crop Pipeline Package
Native box_2d Gemini Visual Grounding & PyMuPDF Cropping Engine
"""

from .gemini_client import GeminiClientManager, GroundingBox
from .pdf_processor import crop_pdf_by_normalized_box
from .main import run_pipeline

__all__ = [
    "GeminiClientManager",
    "GroundingBox",
    "crop_pdf_by_normalized_box",
    "run_pipeline",
]
