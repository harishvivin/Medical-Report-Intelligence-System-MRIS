import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
            print("[INFO] Attempting visual grounding with Primary API Key...")
            client = self._get_client(self.primary_key)
            return self._call_gemini(client, pdf_path, prompt)
        except Exception as e:
            print(f"[WARNING] Primary API Key failed: {e}")
            if self.fallback_key and self.fallback_key != self.primary_key:
                print("[RETRY] Switching to Fallback API Key...")
                client = self._get_client(self.fallback_key)
                return self._call_gemini(client, pdf_path, prompt)
            else:
                raise RuntimeError("Primary API key failed and no fallback key provided.") from e

    def _build_prompt(self, user_question: str) -> str:
        return f"""Analyze the provided PDF document. Locate the exact region/snippet that answers or contains the visual information for the following query:

USER QUESTION: "{user_question}"

INSTRUCTIONS:
1. Identify the 1-based page number where the relevant information is visible.
2. Locate the precise bounding box enclosing ONLY the section that answers the question.
3. Return the coordinates as "box_2d": [ymin, xmin, ymax, xmax].
4. Scale all coordinates as integers between 0 and 1000 (where 0,0 is Top-Left and 1000,1000 is Bottom-Right).

Respond strictly using the required JSON schema."""

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
