import os
import json
import re
from typing import Dict, Any, List, Optional
from logger import logger

# Try importing official Google GenAI SDKs
GENAI_SDK_AVAILABLE = False
GENAI_LEGACY_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False

try:
    import google.generativeai as legacy_genai
    GENAI_LEGACY_AVAILABLE = True
except ImportError:
    GENAI_LEGACY_AVAILABLE = False

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.client = None
        self.legacy_model = None

        if self.api_key:
            if GENAI_SDK_AVAILABLE:
                try:
                    self.client = genai.Client(api_key=self.api_key)
                    logger.info("Initialized Google GenAI Client (official SDK).")
                except Exception as e:
                    logger.warning(f"Failed to initialize google-genai Client: {e}")

            if not self.client and GENAI_LEGACY_AVAILABLE:
                try:
                    legacy_genai.configure(api_key=self.api_key)
                    self.legacy_model = legacy_genai.GenerativeModel("gemini-1.5-flash")
                    logger.info("Initialized Google GenerativeAI Client (legacy SDK).")
                except Exception as e:
                    logger.warning(f"Failed to initialize legacy google-generativeai Client: {e}")
        else:
            logger.info("GEMINI_API_KEY not set. Gemini API will run in fallback mode.")

    def is_available(self) -> bool:
        return bool(self.api_key and (self.client or self.legacy_model))

    def extract_answer(self, question: str, pages_context: Any) -> Optional[Dict[str, Any]]:
        """
        Sends complete page text context + user question to Gemini API.
        Returns structured JSON dict:
        {
          "found": bool,
          "answer": str,
          "matched_line": str,
          "page": int,
          "confidence": float
        }
        """
        if not self.is_available() or not pages_context:
            return None

        # Format complete page context string
        formatted_pages = []
        if isinstance(pages_context, dict):
            for page_num in sorted(pages_context.keys()):
                txt = pages_context[page_num]
                formatted_pages.append(f"=== PAGE {page_num} ===\n{txt}\n")
        elif isinstance(pages_context, list):
            # Group blocks by page number
            page_dict: Dict[int, List[str]] = {}
            for b in pages_context:
                p_num = b.get("page_number", 1)
                txt = b.get("full_row_text") or b.get("text", "")
                if txt:
                    page_dict.setdefault(p_num, []).append(txt)
            for page_num in sorted(page_dict.keys()):
                txt = "\n".join(page_dict[page_num])
                formatted_pages.append(f"=== PAGE {page_num} ===\n{txt}\n")

        full_context_str = "\n".join(formatted_pages)

        system_prompt = (
            "You are an exact medical report understanding AI.\n"
            "Analyze the provided COMPLETE PAGE TEXTS and answer the user's question accurately.\n\n"
            "STRICT RULES:\n"
            "1. Base your answer ONLY on the supplied page texts. Do NOT guess, do NOT infer, and do NOT use medical knowledge.\n"
            "2. Search ONLY inside the supplied page text.\n"
            "3. If the answer exists in the text:\n"
            "   - 'found': true\n"
            "   - 'answer': Extract the concise answer string (e.g. '13.8 g/dL', 'John Doe', '1.8 mg/dL', 'Sinus Rhythm', 'Non-Reactive').\n"
            "   - 'matched_line': Extract the EXACT complete row/line from the page text containing the answer (e.g. 'Hemoglobin : 13.8 g/dL (Reference Range: 13.5 - 17.5 g/dL)'). "
            "This 'matched_line' MUST be copied EXACTLY character-for-character from the supplied PDF text. Never paraphrase, never shorten, and never modify punctuation.\n"
            "   - 'page': Integer page number where the line was found.\n"
            "   - 'confidence': Float confidence score between 0.0 and 1.0 (e.g. 0.99).\n"
            "4. If the requested information does NOT exist in the provided text, return:\n"
            "   'found': false,\n"
            "   'answer': 'The uploaded report does not contain this information.',\n"
            "   'matched_line': null,\n"
            "   'page': null,\n"
            "   'confidence': 0.0.\n\n"
            "RETURN ONLY A VALID JSON OBJECT using this exact schema:\n"
            "{\n"
            '  "found": true,\n'
            '  "answer": "13.8 g/dL",\n'
            '  "matched_line": "Hemoglobin : 13.8 g/dL",\n'
            '  "page": 4,\n'
            '  "confidence": 0.99\n'
            "}"
        )

        user_content = f"COMPLETE PAGE TEXTS:\n{full_context_str}\n\nUSER QUESTION: {question}"

        raw_response = self._generate_text(system_prompt, user_content)
        if not raw_response:
            return None

        try:
            clean_json = re.sub(r'^```(?:json)?\s*', '', raw_response.strip(), flags=re.MULTILINE)
            clean_json = re.sub(r'\s*```$', '', clean_json, flags=re.MULTILINE).strip()

            parsed = json.loads(clean_json)
            if isinstance(parsed, dict):
                matched_line = parsed.get("matched_line") or parsed.get("matched_text")
                return {
                    "found": bool(parsed.get("found", True)),
                    "answer": str(parsed.get("answer", "")).strip(),
                    "matched_line": matched_line,
                    "matched_text": matched_line,
                    "page": parsed.get("page"),
                    "confidence": float(parsed.get("confidence", 0.98))
                }
        except Exception as e:
            logger.error(f"Error parsing Gemini response JSON: {e}. Raw response: {raw_response[:200]}")

        return None

    def generate_summary(self, full_text: str) -> Optional[Dict[str, Any]]:
        """
        Uses Gemini to generate a structured medical report summary JSON.
        """
        if not self.is_available() or not full_text:
            return None

        system_prompt = (
            "You are an expert medical report summarization system.\n"
            "Extract structured summary data from the provided report text.\n\n"
            "RETURN ONLY A VALID JSON OBJECT matching this schema:\n"
            "{\n"
            '  "patient_info": {\n'
            '    "name": "Patient Name",\n'
            '    "age": "Age Yrs",\n'
            '    "gender": "Male/Female",\n'
            '    "ref_doctor": "Doctor Name",\n'
            '    "date": "Report Date"\n'
            '  },\n'
            '  "hospital": "Hospital / Lab Name",\n'
            '  "tests_performed": ["Complete Blood Count (CBC)", "Renal Function Test (KFT)"],\n'
            '  "important_findings": [\n'
            '    {"parameter": "Hemoglobin", "value": "14.5 g/dL", "reference_range": "13.0 - 17.0", "status": "Normal"}\n'
            '  ],\n'
            '  "abnormal_values": [\n'
            '    {"parameter": "Creatinine", "value": "1.8 mg/dL", "reference_range": "0.6 - 1.2", "status": "Abnormal"}\n'
            '  ],\n'
            '  "recommendations": ["Follow up with physician"]\n'
            "}"
        )

        raw_response = self._generate_text(system_prompt, f"MEDICAL REPORT TEXT:\n{full_text[:4000]}")
        if not raw_response:
            return None

        try:
            clean_json = re.sub(r'^```(?:json)?\s*', '', raw_response.strip(), flags=re.MULTILINE)
            clean_json = re.sub(r'\s*```$', '', clean_json, flags=re.MULTILINE).strip()
            parsed = json.loads(clean_json)
            if isinstance(parsed, dict):
                return parsed
        except Exception as e:
            logger.error(f"Error parsing Gemini summary JSON: {e}")

        return None

    def _generate_text(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        # 1. Try official SDK
        if self.client:
            try:
                # Try gemini-2.5-flash or gemini-1.5-flash
                for model_id in ["gemini-2.5-flash", "gemini-1.5-flash"]:
                    try:
                        res = self.client.models.generate_content(
                            model=model_id,
                            contents=f"{system_prompt}\n\n{user_prompt}",
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.0
                            )
                        )
                        if res and res.text:
                            return res.text
                    except Exception as e:
                        logger.debug(f"Gemini model {model_id} call failed: {e}")
            except Exception as e:
                logger.error(f"Error executing Gemini client call: {e}")

        # 2. Try legacy SDK
        if self.legacy_model:
            try:
                res = self.legacy_model.generate_content(
                    f"{system_prompt}\n\n{user_prompt}",
                    generation_config={"temperature": 0.0, "response_mime_type": "application/json"}
                )
                if res and res.text:
                    return res.text
            except Exception as e:
                logger.error(f"Error executing legacy Gemini call: {e}")

        return None
