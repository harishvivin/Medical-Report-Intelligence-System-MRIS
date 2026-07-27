import os
import sys
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Add src folder to Python path
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from config import UPLOAD_DIR, CROPS_DIR, PORT, HOST
from logger import logger
from pdf_reader import PDFReader
from document_index import DocumentIndex
from qa_engine import QAEngine
from summary_engine import SummaryEngine

app = FastAPI(
    title="Medical Report Extract AI API",
    description="Production-ready medical report PDF extraction, QA, screenshot cropping & summarization engine.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory storage for active document sessions
# Store: document_id -> { "pdf_path": str, "reader": PDFReader, "index": DocumentIndex, "qa_engine": QAEngine }
DOC_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Pydantic schemas
class AskQuestionRequest(BaseModel):
    document_id: str
    question: str

class SummaryRequest(BaseModel):
    document_id: str

@app.get("/health")
def health_check():
    return {"status": "healthy", "sessions_active": len(DOC_SESSIONS)}

@app.post("/api/process")
async def process_document(file: UploadFile = File(...)):
    """
    Processes an uploaded PDF file:
    - Extracts all pages and text blocks with bounding boxes via PyMuPDF.
    - Constructs TF-IDF index.
    - Stores active session under document_id.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    pdf_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"

    try:
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Saved uploaded PDF to '{pdf_path}'")

        # Parse PDF and extract blocks
        reader = PDFReader(str(pdf_path))
        blocks = reader.extract_all_text_blocks()
        doc_index = DocumentIndex(blocks)
        qa_engine = QAEngine(str(pdf_path), doc_index)

        # Store session
        DOC_SESSIONS[doc_id] = {
            "pdf_path": str(pdf_path),
            "filename": file.filename,
            "reader": reader,
            "blocks": blocks,
            "index": doc_index,
            "qa_engine": qa_engine
        }

        pages_summary = []
        for page_idx in range(reader.page_count):
            page_blocks = [b for b in blocks if b["page_index"] == page_idx]
            pages_summary.append({
                "page_number": page_idx + 1,
                "block_count": len(page_blocks)
            })

        return {
            "success": True,
            "document_id": doc_id,
            "page_count": reader.page_count,
            "pages": pages_summary,
            "filename": file.filename
        }

    except Exception as e:
        logger.error(f"Error processing PDF upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF report: {str(e)}")

@app.post("/api/qa/ask")
async def ask_question(request: AskQuestionRequest):
    """
    Retrieves answers ONLY from the uploaded PDF document.
    Returns exact answer string, page number, confidence, bounding box, and cropped screenshot URL.
    """
    session = DOC_SESSIONS.get(request.document_id)
    if not session:
        raise HTTPException(status_code=44, detail="Document session not found. Please upload a PDF first.")

    qa_engine: QAEngine = session["qa_engine"]
    result = qa_engine.answer_question(request.question)
    return result

@app.post("/api/summary")
async def get_summary(request: SummaryRequest):
    """
    Generates structured summary including Patient Info, Hospital, Tests, Findings, Abnormal Values, and Recommendations.
    """
    session = DOC_SESSIONS.get(request.document_id)
    if not session:
        raise HTTPException(status_code=404, detail="Document session not found. Please upload a PDF first.")

    blocks = session["blocks"]
    summary_engine = SummaryEngine(blocks)
    summary = summary_engine.generate_summary()

    return {"summary": summary}

@app.get("/api/crops/{crop_id}")
async def serve_crop(crop_id: str):
    """Serves cropped screenshot PNG files."""
    crop_path = CROPS_DIR / crop_id
    if not crop_path.exists():
        raise HTTPException(status_code=404, detail="Crop screenshot image not found.")
    return FileResponse(str(crop_path), media_type="image/png")

# Static frontend mount for single deployment on Render
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info(f"Mounted production frontend static build from '{frontend_dist}'")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)
