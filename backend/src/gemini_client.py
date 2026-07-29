import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from logger import logger

# Load .env from project root (utf-8-sig handles Windows BOM)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path, encoding="utf-8-sig", override=True)
except ImportError:
    pass

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
        # Accept PRIMARY_GEMINI_API_KEY (test pipeline key) or legacy GEMINI_API_KEY
        self.api_key = (
            api_key
            or os.environ.get("PRIMARY_GEMINI_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
        )
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

    def extract_answer(
        self, question: str, pages_context: Any, page_images: Optional[Dict[int, bytes]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Uses Gemini API (Multimodal Text & Vision) to analyze document content and extract exact answer.
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
            "You are an expert visual document layout analyzer and medical document intelligence system.\n"
            "Analyze the provided COMPLETE PAGE TEXTS AND/OR PAGE IMAGES and answer the user's question accurately.\n\n"
            "STRICT RULES:\n"
            "1. Base your answer strictly on the supplied page text or images (including tables, handwritten doctor notes, and ECG strips). Do NOT invent or hallucinate data.\n"
            "2. Understand all medical lab test categories (Basic Info, CBC, Kidney Function, Diabetes, Liver Function, Lipid Profile, Serology/Infectious Disease, Urine Analysis, ECG, Summaries).\n"
            "3. Identify the exact spatial bounding box of the region containing the answer on a 0 to 1000 normalized scale:\n"
            "   - ymin: Top edge (0 = top of page, 1000 = bottom of page)\n"
            "   - xmin: Left edge (0 = left of page, 1000 = right of page)\n"
            "   - ymax: Bottom edge (0 = top of page, 1000 = bottom of page)\n"
            "   - xmax: Right edge (0 = left of page, 1000 = right of page)\n"
            "4. If the user asks about specific test values, metadata (e.g. Patient Name, Age, Gender, Hospital, Application Number, MER Number, HSP Code, Service Type), or diagnostic findings:\n"
            "   - 'found': true\n"
            "   - 'answer': Concise and clear answer string with value, units, or clinical status.\n"
            "   - 'matched_line': Extract the EXACT complete row/line containing the target answer (e.g. 'Hemoglobin : 13.8 g/dL (Reference Range: 13.5 - 17.5 g/dL)'). Never paraphrase, never shorten, and never modify punctuation.\n"
            "   - 'page': 1-based integer page number where the information is located.\n"
            "   - 'confidence': Float confidence score between 0.0 and 1.0 (e.g. 0.99).\n"
            "   - 'ymin', 'xmin', 'ymax', 'xmax': Integers (0 to 1000) bounding the exact answer region tightly.\n"
            "5. If the requested parameter or test is NOT present anywhere in the supplied text or images, return:\n"
            "   'found': false,\n"
            "   'answer': 'The uploaded report does not contain this information.',\n"
            "   'matched_line': null,\n"
            "   'page': null,\n"
            "   'confidence': 0.0,\n"
            "   'ymin': null, 'xmin': null, 'ymax': null, 'xmax': null.\n\n"
            "RETURN ONLY A VALID JSON OBJECT using this exact schema:\n"
            "{\n"
            '  "found": true,\n'
            '  "answer": "13.8 g/dL",\n'
            '  "matched_line": "Hemoglobin : 13.8 g/dL",\n'
            '  "page": 1,\n'
            '  "confidence": 0.99,\n'
            '  "ymin": 160,\n'
            '  "xmin": 50,\n'
            '  "ymax": 200,\n'
            '  "xmax": 950\n'
            "}"
        )

        user_content = f"COMPLETE PAGE TEXTS:\n{full_context_str}\n\nUSER QUESTION: {question}"

        raw_response = self._generate_text(system_prompt, user_content, page_images=page_images)
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
                    "confidence": float(parsed.get("confidence", 0.98)),
                    "ymin": parsed.get("ymin"),
                    "xmin": parsed.get("xmin"),
                    "ymax": parsed.get("ymax"),
                    "xmax": parsed.get("xmax")
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
            "You are a clinical data extraction assistant.\n"
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

    def _generate_text(
        self, system_prompt: str, user_prompt: str, page_images: Optional[Dict[int, bytes]] = None
    ) -> Optional[str]:
        # 1. Try official SDK (Multimodal Text & Vision)
        if self.client:
            try:
                for model_id in ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                    try:
                        contents = [system_prompt]
                        if page_images:
                            for p_num, img_bytes in page_images.items():
                                try:
                                    contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
                                    contents.append(f"=== PAGE {p_num} IMAGE RENDER ===")
                                except Exception as img_err:
                                    logger.debug(f"Error attaching page {p_num} image bytes: {img_err}")
                        contents.append(user_prompt)

                        res = self.client.models.generate_content(
                            model=model_id,
                            contents=contents,
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
                contents = [f"{system_prompt}\n\n{user_prompt}"]
                if page_images:
                    for p_num, img_bytes in page_images.items():
                        contents.append({"mime_type": "image/png", "data": img_bytes})

                res = self.legacy_model.generate_content(
                    contents,
                    generation_config={"temperature": 0.0, "response_mime_type": "application/json"}
                )
                if res and res.text:
                    return res.text
            except Exception as e:
                logger.error(f"Error executing legacy Gemini call: {e}")

        return None
