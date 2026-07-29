import os
from pathlib import Path

# Load environment variables from .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent

# API Key Configuration
GEMINI_API_KEY_PRIMARY = os.getenv("GEMINI_API_KEY_PRIMARY", os.getenv("GEMINI_API_KEY", ""))
GEMINI_API_KEY_FALLBACK = os.getenv("GEMINI_API_KEY_FALLBACK", os.getenv("GEMINI_API_KEY_PRIMARY", os.getenv("GEMINI_API_KEY", "")))

# Model Settings
# Use Flash-Lite model as requested
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
FALLBACK_MODEL_NAME = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.0-flash-lite")

TEMPERATURE = 0.0

# Output Crops Directory
CROPS_DIR = BASE_DIR / "crops"
CROPS_DIR.mkdir(parents=True, exist_ok=True)
