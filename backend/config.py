import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent

# Uploads & Crops directories
UPLOAD_DIR = BACKEND_DIR / "uploads"
CROPS_DIR = BACKEND_DIR / "crops"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CROPS_DIR.mkdir(parents=True, exist_ok=True)

# Server Config
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Question Answering Thresholds
MIN_CONFIDENCE_SCORE = 0.12
CROP_DPI_SCALE = 2.0  # Pixmap zoom scale (approx 144-200 DPI)
MAX_FILE_SIZE_MB = 25
