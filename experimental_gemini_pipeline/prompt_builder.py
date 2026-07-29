"""
Prompt Builder Module for Experimental Gemini Pipeline.
Generates inline prompts for visual PDF localization using Python f-strings.
"""

def build_prompt(question: str, total_pages: int = None) -> str:
    """
    Build a prompt using Python f-strings instructing Gemini to locate the exact answer and coordinates in the PDF.
    
    Args:
        question: The user's query/question to locate in the PDF.
        total_pages: Optional total page count of the PDF to ensure Gemini inspects every page.
        
    Returns:
        Formatted prompt string.
    """
    page_context = (
        f"The uploaded PDF document contains EXACTLY {total_pages} page(s) (from Page 1 to Page {total_pages})."
        if total_pages
        else "The uploaded PDF document contains multiple pages."
    )
    
    total_str = str(total_pages) if total_pages else "N"

    return f"""You are an expert PDF visual document understanding and localization system.

Analyze ONLY the uploaded PDF document.

{page_context}

Task: Give me the exact answer, target page number, and bounding box coordinates for this question:
{question}

CRITICAL RULES FOR ACCURACY & EXCLUSIONS:

1. STRICT EXCLUSION OF TEST CODES & ORDER LISTS:
   - NEVER return test code lists, requisition codes, or package headers (e.g. NEVER return lines like ": BPB-F,CBC (Complete Blood Count),ECG-R,HBA1C,MER...").
   - If a line contains package codes like 'ECG-R', 'BPB-F', 'CBC', 'HBA1C', or 'MER' inside a 'TEST DETAILS' or order list section, REJECT IT IMMEDIATELY.
   - You MUST locate the ACTUAL DIAGNOSTIC RESULT, INTERPRETATION, or VALUE row (e.g., "ECG within normal limits", "Sinus Rhythm 69 BPM", "14.92 g/dL").

2. MEDICAL TERMINOLOGY & SYNONYM MATCHING:
   - For ECG questions ("ecg recording", "ecg report", "ecg result", "ecg graph", "ecg trace", "electrocardiogram"):
     - Locate the actual ECG Findings / Cardiology Examination / ECG Impression section (e.g. "ECG within normal limit", "Sinus Rhythm", "Heart Rate: 69 BPM").
     - NEVER return the list of ordered test names like ": BPB-F, CBC, ECG-R...".
   - For blood test questions ("blood sugar", "fasting blood sugar", "hba1c", "creatinine", "blood pressure"):
     - Locate the exact test row in the laboratory results section and extract the value and unit (e.g. "5.1 %", "0.88 mg/dL", "125/81 mmHg").

3. INDEPENDENT PAGE LOCATION:
   - Evaluate this question completely independently across all pages (Page 1 through Page {total_str}).
   - Find the SPECIFIC 1-based page number (between 1 and {total_str}) where the actual answer to THIS question is printed. Do NOT default to page 1 or page 4!

Return ONLY valid JSON.

Schema:
{{
    "found": true,
    "answer": "Actual clinical finding or test result string (e.g. 'ECG within normal limits', '14.92 g/dL', '125/81 mmHg')",
    "page": 1,
    "bounding_box": {{
        "x1": 0.23,
        "y1": 0.41,
        "x2": 0.68,
        "y2": 0.47
    }},
    "matched_text": "Exact text line of the result printed on the PDF page",
    "confidence": 0.99
}}

IMPORTANT:
- "answer": The direct clinical result/finding (e.g. "ECG within normal limits (Heart Rate: 69 BPM, Sinus Rhythm)").
- "page": The exact 1-based page number where this answer is printed.
- "bounding_box": Coordinates x1, y1, x2, y2 of the visual answer region on that page (normalized between 0.0 and 1.0 or 0 and 1000, where x1, y1 is top-left and x2, y2 is bottom-right).
- "matched_text": Must exactly match the result text printed in the PDF.
- Do not paraphrase. Do not hallucinate.

If the answer does not exist on ANY page in the PDF, return ONLY:
{{
    "found": false
}}
"""
