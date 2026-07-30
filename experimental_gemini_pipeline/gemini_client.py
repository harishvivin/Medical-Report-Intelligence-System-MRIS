import os
import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, encoding="utf-8-sig", override=True)


# Schema — each individual answer found in the document
class GroundingBox(BaseModel):
    page_number: int = Field(description="1-based index of the PDF page containing this answer")
    box_2d: List[int] = Field(description="[ymin, xmin, ymax, xmax] normalized strictly to 0-1000")
    answer_text: str = Field(description="The exact value or text that directly answers the question (e.g. '13.8 g/dL', 'Manjit Singh', 'Normal sinus rhythm')")
    label: Optional[str] = Field(default=None, description="Brief description of the highlighted region (e.g. 'Hemoglobin value', 'Patient Name')")

# Wrapper schema — Gemini MUST return ALL matches, not just one
class GroundingBoxList(BaseModel):
    results: List[GroundingBox] = Field(description="A list of ALL answers found in the document. Each entry is a separate answer on a separate location/page.")

class GeminiClientManager:
    def __init__(self):
        self.primary_key = (
            os.getenv("PRIMARY_GEMINI_API_KEY") or 
            os.getenv("GEMINI_API_KEY_PRIMARY") or 
            os.getenv("GEMINI_API_KEY", "")
        )
        self.fallback_key = (
            os.getenv("FALLBACK_GEMINI_API_KEY") or 
            os.getenv("GEMINI_API_KEY_FALLBACK", "")
        )

    def _get_client(self, api_key: str) -> genai.Client:
        return genai.Client(api_key=api_key)

    def extract_bounding_boxes(self, pdf_path: str, user_question: str) -> GroundingBoxList:
        """
        Sends PDF and question to Gemini Flash.
        Returns ALL matching answers as a list.
        Tries PRIMARY_GEMINI_API_KEY, falls back to FALLBACK_GEMINI_API_KEY on error.
        """
        prompt = self._build_prompt(user_question)

        try:
            print("[PRIMARY] Attempting visual grounding with Primary API Key...")
            client = self._get_client(self.primary_key)
            return self._call_gemini(client, pdf_path, prompt)
        except Exception as e:
            print(f"[WARN] Primary API Key failed: {e}")
            if self.fallback_key and self.fallback_key != self.primary_key:
                print("[FALLBACK] Switching to Fallback API Key...")
                client = self._get_client(self.fallback_key)
                return self._call_gemini(client, pdf_path, prompt)
            else:
                raise RuntimeError("Primary API key failed and no distinct fallback key provided.") from e

    def _build_prompt(self, user_question: str) -> str:
        return (
            f'Look through the ENTIRE PDF document and find ALL parts that answer this question: "{user_question}". '
            f'There may be multiple answers on different pages (e.g. multiple patients, siblings, or repeated fields). '
            f'For EACH answer found, return the page number, the exact answer_text (the precise value e.g. "13.8 g/dL", "Male", "25 years"), '
            f'a short label describing the context (e.g. "Sister 1 - Age", "Brother - Gender"), '
            f'and the bounding box [ymin, xmin, ymax, xmax] (0-1000 scale). '
            f'IMPORTANT: The bounding box MUST be drawn widely to include the entire row with both the label and value. '
            f'Return ALL results you find, not just the first one.'
        )

    def _call_gemini(self, client: genai.Client, pdf_path: str, prompt: str) -> GroundingBoxList:
        # Upload PDF file to Gemini Files API
        uploaded_file = client.files.upload(file=pdf_path)

        try:
            # Call Gemini with structured output — returns a LIST of results
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GroundingBoxList,
                    temperature=0.0
                )
            )

            result = GroundingBoxList.model_validate_json(response.text)
            return result
        finally:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass


# Backward compatibility helper — now returns a LIST of result dicts
def locate_answer_in_pdf(pdf_path: str, question: str) -> dict:
    manager = GeminiClientManager()
    try:
        gbl = manager.extract_bounding_boxes(pdf_path, question)
        if not gbl.results:
            return {"found": False, "results": [], "error": "No matching information found in the document."}

        results = []
        for gb in gbl.results:
            results.append({
                "page_number": gb.page_number,
                "page": gb.page_number,
                "box_2d": gb.box_2d,
                "bounding_box": gb.box_2d,
                "answer": gb.answer_text,
                "matched_text": gb.answer_text,
                "label": gb.label,
                "confidence": 0.99,
            })

        return {"found": True, "results": results}
    except Exception as e:
        return {"found": False, "results": [], "error": str(e)}
