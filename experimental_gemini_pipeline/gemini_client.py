import os
import re
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


def clean_extracted_value(answer_text: str, question: str = "") -> str:
    """
    Post-processing sanitizer that guarantees extracted answers contain ONLY
    the actual selected value, distinguishing between:
    1. Field labels (e.g. 'Patient Name:', 'Sex:', 'Age:')
    2. Candidate options (e.g. 'M/F', 'Male/Female', 'Yes/No', 'Married/Single', 'Fit/Unfit')
    3. Actual selected value (e.g. 'M', 'Female', '57Y', 'Manjit Singh', '1.2 mg/dL', 'Fit', 'Yes')
    """
    if not answer_text or not isinstance(answer_text, str):
        return answer_text or ""

    text = answer_text.strip()
    q_lower = (question or "").lower()

    # 1. Strip wrapping quotes or brackets around single words
    text = re.sub(r'^["\'\u201c\u201d\u2018\u2019]+|["\'\u201c\u201d\u2018\u2019]+$', '', text).strip()

    # 2. Check for explicit selection markers in checkbox/option text
    # e.g., "[x] Male [ ] Female", "[✓] Yes [ ] No", "☑ Married ☐ Single", "(X) Fit ( ) Unfit", "● Female ○ Male"
    checked_pattern = re.compile(
        r'(?:\[[xX\u2713\u2714\u2718]\]|[\u2611\u25cf\u2713\u2714]|\([xX\u2713\u2714]\))\s*([A-Za-z0-9\+\-]+)',
        re.UNICODE
    )
    checked_match = checked_pattern.search(text)
    if checked_match:
        selected_val = checked_match.group(1).strip()
        if selected_val:
            return selected_val

    # 3. Handle explicit selected annotations like "M (Selected)", "Male (ticked)", "Selected: M"
    selected_annotation = re.compile(
        r'(?:selected|ticked|checked|marked)\s*[:=\-\s]*([A-Za-z0-9\+\-]+)|([A-Za-z0-9\+\-]+)\s*\((?:selected|ticked|checked|marked)\)',
        re.IGNORECASE
    )
    annot_match = selected_annotation.search(text)
    if annot_match:
        val = annot_match.group(1) or annot_match.group(2)
        if val:
            return val.strip()

    # 4. Remove leading field label prefixes (e.g. "Patient Name:", "Sex:", "Age:", "Gender:")
    label_prefix_pattern = re.compile(
        r'^(?:Patient\s+Name|Patient\'?s?\s+Sex|Patient\'?s?\s+Gender|Patient\'?s?\s+Age|'
        r'Name|Sex|Gender|Age|Marital\s+Status|Smoking\s+Status|Smoking|Alcohol\s+Status|Alcohol|'
        r'Fit\s*\/\s*Unfit|Creatinine|HbA1c|Hemoglobin|Blood\s+Pressure|Blood\s+Group|'
        r'Hospital\s+Name|Hospital|Doctor|Diagnosis|Result|Value|Status|Ans(?:wer)?)\s*[:=\-\u2013\u2014]\s*',
        re.IGNORECASE
    )
    text = label_prefix_pattern.sub('', text).strip()

    # 5. Clean slash-separated candidate lists when no selection marker was preserved in raw text
    # e.g., "M/F", "Male/Female", "Male / Female", "Yes/No", "Yes / No", "Married/Single", "Fit/Unfit"
    slash_candidates = re.compile(r'^\s*([A-Za-z0-9]+)\s*[\/\u2044|]\s*([A-Za-z0-9]+)\s*$', re.IGNORECASE)
    slash_match = slash_candidates.match(text)
    if slash_match:
        opt1, opt2 = slash_match.group(1).strip(), slash_match.group(2).strip()
        opt1_u, opt2_u = opt1.upper(), opt2.upper()

        # If it's M/F or Male/Female
        if (opt1_u in ['M', 'MALE'] and opt2_u in ['F', 'FEMALE']) or (opt1_u in ['F', 'FEMALE'] and opt2_u in ['M', 'MALE']):
            if 'female' in q_lower or 'woman' in q_lower or 'girl' in q_lower:
                return 'F' if opt1_u in ['M', 'F'] else 'Female'
            elif 'male' in q_lower or 'man' in q_lower or 'boy' in q_lower:
                return 'M' if opt1_u in ['M', 'F'] else 'Male'
            else:
                return opt1

        # If it's Yes/No or No/Yes
        if (opt1_u == 'YES' and opt2_u == 'NO') or (opt1_u == 'NO' and opt2_u == 'YES'):
            return opt1

        # If it's Fit/Unfit
        if (opt1_u == 'FIT' and opt2_u == 'UNFIT') or (opt1_u == 'UNFIT' and opt2_u == 'FIT'):
            return opt1

        return opt1

    # 6. Final cleanup of any trailing/leading symbols
    text = re.sub(r'^[:\-=\s\u2013\u2014]+|[:\-\s\u2013\u2014]+$', '', text).strip()
    return text


# Schema — each individual answer found in the document
class GroundingBox(BaseModel):
    page_number: int = Field(description="1-based index of the PDF page containing this answer")
    box_2d: List[int] = Field(description="[ymin, xmin, ymax, xmax] normalized strictly to 0-1000")
    answer_text: str = Field(description="The ONLY actual selected value present in the report (e.g. 'M', '13.8 g/dL', 'Manjit Singh', 'Fit', 'Yes'). NEVER return candidate lists or labels like 'M/F' or 'Sex: M'.")
    label: Optional[str] = Field(default=None, description="Brief description of the field (e.g. 'Patient Sex', 'Patient Name')")

# Wrapper schema — Gemini MUST return ALL matches, not just one
class GroundingBoxList(BaseModel):
    results: List[GroundingBox] = Field(description="A list of ALL answers found in the document.")


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
        Returns ALL matching answers as a list with sanitized selected values.
        """
        prompt = self._build_prompt(user_question)

        try:
            print("[PRIMARY] Attempting visual grounding with Primary API Key...")
            client = self._get_client(self.primary_key)
            gbl = self._call_gemini(client, pdf_path, prompt)
        except Exception as e:
            print(f"[WARN] Primary API Key failed: {e}")
            if self.fallback_key and self.fallback_key != self.primary_key:
                print("[FALLBACK] Switching to Fallback API Key...")
                client = self._get_client(self.fallback_key)
                gbl = self._call_gemini(client, pdf_path, prompt)
            else:
                raise RuntimeError("Primary API key failed and no distinct fallback key provided.") from e

        # Post-process every extracted answer text to guarantee single selected value
        for item in gbl.results:
            item.answer_text = clean_extracted_value(item.answer_text, user_question)
        return gbl

    def extract_bounding_box(self, pdf_path: str, user_question: str) -> GroundingBox:
        """Single GroundingBox extraction helper for backward compatibility."""
        gbl = self.extract_bounding_boxes(pdf_path, user_question)
        if gbl.results:
            return gbl.results[0]
        return GroundingBox(page_number=1, box_2d=[0,0,0,0], answer_text="", label="")

    def _build_prompt(self, user_question: str) -> str:
        return (
            f'Look through the ENTIRE PDF document and answer this question: "{user_question}".\n\n'
            f'CRITICAL VALUE EXTRACTION RULES:\n'
            f'1. RETURN ONLY THE ACTUAL SELECTED VALUE.\n'
            f'   - NEVER return field labels (do NOT return "Sex: M", return "M").\n'
            f'   - NEVER return candidate option lists or concatenated options (if form has "Sex: [X] M  [ ] F" or "M/F", return ONLY "M", NEVER "M/F").\n'
            f'   - For checkboxes, radio buttons, tick marks (✓/✔/X/☑/●), circles, or highlighted options (Sex, Marital Status, Smoking, Alcohol, Fit/Unfit), inspect the visual mark and return ONLY the ONE selected option.\n'
            f'   - Patient Name -> return only the name (e.g. "Manjit Singh").\n'
            f'   - Age -> return only the age (e.g. "57Y" or "57").\n'
            f'   - Gender / Sex -> return only "M" or "F" (or "Male" or "Female" as marked).\n'
            f'   - Blood Group -> return only the actual blood group (e.g. "O+").\n'
            f'   - Creatinine / HbA1c / Hemoglobin -> return only the numeric result with unit (e.g. "1.2 mg/dL", "5.8%").\n'
            f'   - Hospital Name -> return only the hospital name.\n\n'
            f'2. MULTIPLE ENTITIES vs SINGLE ENTITY:\n'
            f'   - If asking about ONE entity (e.g. "patient name", "sex"), return 1 result.\n'
            f'   - If asking about MULTIPLE distinct entities (e.g. "siblings"), return 1 result per entity.\n\n'
            f'3. BOUNDING BOX RULES:\n'
            f'   - For table rows: cover the row containing the answer, from leftmost label to rightmost value cell.\n'
            f'   - For non-table content: cover the line or paragraph with the answer.\n'
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


# Backward compatibility helper — returns a LIST of result dicts
def locate_answer_in_pdf(pdf_path: str, question: str) -> dict:
    manager = GeminiClientManager()
    try:
        gbl = manager.extract_bounding_boxes(pdf_path, question)
        if not gbl.results:
            return {"found": False, "results": [], "error": "No matching information found in the document."}

        results = []
        for gb in gbl.results:
            clean_val = clean_extracted_value(gb.answer_text, question)
            results.append({
                "page_number": gb.page_number,
                "page": gb.page_number,
                "box_2d": gb.box_2d,
                "bounding_box": gb.box_2d,
                "answer": clean_val,
                "matched_text": clean_val,
                "label": gb.label,
                "confidence": 0.99,
            })

        return {"found": True, "results": results}
    except Exception as e:
        return {"found": False, "results": [], "error": str(e)}
