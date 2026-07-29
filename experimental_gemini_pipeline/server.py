"""
Standalone FastAPI backend server for Medical Report Extract AI.
Uses the Gemini multimodal pipeline to find answers in PDFs and return
bounding box coordinates + crop image snippets.
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env from project root
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_ROOT / ".env", encoding="utf-8-sig", override=True)

from gemini_client import GeminiClientManager, locate_answer_in_pdf
from pdf_processor import crop_pdf_by_normalized_box

# ── Directories ──────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
CROPS_DIR  = BASE_DIR / "crops"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CROPS_DIR.mkdir(parents=True, exist_ok=True)

# ── In-memory session store ──────────────────────────────────
# document_id → { pdf_path, filename, page_count }
SESSIONS: dict = {}

# ── FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title="Medical Report Extract AI",
    description="Gemini multimodal PDF Q&A with visual bounding box crop extraction.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve crops as static files
app.mount("/api/crops", StaticFiles(directory=str(CROPS_DIR)), name="crops")

# ── Models ───────────────────────────────────────────────────
class AskRequest(BaseModel):
    document_id: str
    question: str

# ── Routes ───────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "service": "Medical Report Extract AI - Gemini Pipeline Backend"}


@app.post("/api/process")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF and create a session."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    document_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / document_id
    session_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = session_dir / file.filename

    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Count pages using PyMuPDF
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
    except Exception:
        page_count = 1

    SESSIONS[document_id] = {
        "pdf_path": str(pdf_path),
        "filename": file.filename,
        "page_count": page_count,
    }

    return {
        "document_id": document_id,
        "filename": file.filename,
        "page_count": page_count,
        "status": "ready"
    }


@app.post("/api/qa/ask")
async def ask_question(req: AskRequest):
    """Ask a question about an uploaded PDF."""
    session = SESSIONS.get(req.document_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document session not found. Please upload the PDF again.")

    pdf_path = session["pdf_path"]

    # Call the Gemini pipeline
    result = locate_answer_in_pdf(pdf_path, req.question)

    if not result.get("found"):
        return {
            "question": req.question,
            "answer": "The uploaded report does not contain this information.",
            "page_number": None,
            "confidence": 0.0,
            "snippet_url": None,
            "bounding_box": None,
        }

    page_number = result.get("page_number", 1)
    box_2d = result.get("box_2d")
    answer_text = result.get("answer", result.get("label", ""))

    # Generate crop image
    snippet_url = None
    if box_2d and len(box_2d) == 4:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_idx = min(page_number - 1, len(doc) - 1)
            page = doc[page_idx]
            w, h = page.rect.width, page.rect.height
            doc.close()

            ymin, xmin, ymax, xmax = [float(v) for v in box_2d]
            pt_bbox = [
                round((xmin / 1000.0) * w, 2),
                round((ymin / 1000.0) * h, 2),
                round((xmax / 1000.0) * w, 2),
                round((ymax / 1000.0) * h, 2),
            ]

            crop_filename = f"{req.document_id}_p{page_number}_{uuid.uuid4().hex[:8]}.png"
            crop_path = str(CROPS_DIR / crop_filename)
            crop_pdf_by_normalized_box(pdf_path, page_number, box_2d, crop_path)
            snippet_url = f"/api/crops/{crop_filename}"
        except Exception as e:
            print(f"[CROP ERROR] {e}")
            pt_bbox = None
    else:
        pt_bbox = None

    return {
        "question": req.question,
        "answer": answer_text,
        "page_number": page_number,
        "confidence": result.get("confidence", 0.99),
        "snippet_url": snippet_url,
        "bounding_box": pt_bbox,
    }


@app.post("/api/summary")
async def get_summary(req: AskRequest):
    """Generate a basic summary by querying key fields."""
    session = SESSIONS.get(req.document_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document session not found.")

    # Minimal summary via Gemini
    pdf_path = session["pdf_path"]
    manager = GeminiClientManager()

    summary_fields = ["patient name", "age", "gender", "referring doctor", "report date", "hospital name"]
    patient_info = {}
    for field in summary_fields:
        try:
            res = locate_answer_in_pdf(pdf_path, f"What is the {field}?")
            if res.get("found"):
                patient_info[field.replace(" ", "_")] = res.get("answer", "")
        except Exception:
            pass

    return {
        "document_id": req.document_id,
        "filename": session["filename"],
        "page_count": session["page_count"],
        "patient_info": patient_info,
        "summary": f"Medical report for {patient_info.get('patient_name', 'patient')} processed successfully.",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
