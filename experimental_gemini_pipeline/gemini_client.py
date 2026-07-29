import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Schema aligned with Gemini's native visual grounding box_2d
class GroundingBox(BaseModel):
    page_number: int = Field(description="1-based index of the PDF page containing the answer")
    box_2d: List[int] = Field(description="[ymin, xmin, ymax, xmax] normalized strictly to 0-1000")
    label: Optional[str] = Field(description="Brief description of the highlighted region")

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

    def extract_bounding_box(self, pdf_path: str, user_question: str) -> GroundingBox:
        """
        Sends PDF and question to Gemini Flash.
        Tries PRIMARY_GEMINI_API_KEY, falls back to FALLBACK_GEMINI_API_KEY on error.
        """
        prompt = self._build_prompt(user_question)

        try:
            print("🟢 Attempting visual grounding with Primary API Key...")
            client = self._get_client(self.primary_key)
            return self._call_gemini(client, pdf_path, prompt)
        except Exception as e:
            print(f"⚠️ Primary API Key failed: {e}")
            if self.fallback_key and self.fallback_key != self.primary_key:
                print("🔄 Switching to Fallback API Key...")
                client = self._get_client(self.fallback_key)
                return self._call_gemini(client, pdf_path, prompt)
            else:
                raise RuntimeError("Primary API key failed and no distinct fallback key provided.") from e

    def _build_prompt(self, user_question: str) -> str:
        return f'Look through the entire PDF and find the part that answers this question: "{user_question}". Return the page number and the bounding box coordinates [ymin, xmin, ymax, xmax] (0-1000 scale) of exactly that section.'

    def _call_gemini(self, client: genai.Client, pdf_path: str, prompt: str) -> GroundingBox:
        # Upload PDF file to Gemini Files API
        uploaded_file = client.files.upload(file=pdf_path)

        try:
            # Call Gemini with structured output enforcement
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GroundingBox,
                    temperature=0.0  # Low temperature prevents spatial hallucination
                )
            )

            result = GroundingBox.model_validate_json(response.text)
            return result
        finally:
            # Cleanup remote file
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass


# Backward compatibility helper for existing pipeline imports
def locate_answer_in_pdf(pdf_path: str, question: str) -> dict:
    manager = GeminiClientManager()
    try:
        gb = manager.extract_bounding_box(pdf_path, question)
        return {
            "found": True,
            "page_number": gb.page_number,
            "page": gb.page_number,
            "box_2d": gb.box_2d,
            "bounding_box": gb.box_2d,
            "label": gb.label,
            "answer": gb.label,
            "confidence": 0.99
        }
    except Exception as e:
        return {"found": False, "error": str(e)}
