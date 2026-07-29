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

CRITICAL RULES FOR ACCURACY & PAGE SELECTION:
1. INDEPENDENT PAGE LOCATION:
   - Evaluate this question completely independently across all pages (Page 1 through Page {total_str}).
   - Different questions are answered on different pages (e.g. Vitals on Page 1, Blood Count on Page 2, Diabetes/Kidney tests on Page 3, ECG/Serology on Page 4).
   - Find the SPECIFIC 1-based page number (between 1 and {total_str}) where the answer to THIS specific question is printed. Do NOT default to page 1 or page 4!

2. LAB TEST & PARAMETER ACCURACY:
   - If the question asks for a lab result or test parameter (e.g., "HbA1c", "Fasting Blood Sugar", "Creatinine", "Hemoglobin", "Blood Pressure"):
     - Locate the specific row in the laboratory/vitals report table for that exact test name.
     - Extract the actual numerical value and unit (e.g. "5.1 %", "112.12 mg/dL", "0.88 mg/dL", "125/81 mmHg").
     - NEVER confuse lab values with clinical complaints, patient history, or symptoms (e.g. NEVER return "having chest pains" for a lab value question like HbA1c/Sugar).

3. REPORT FINDINGS vs ORDER LISTS:
   - Locate the actual diagnostic FINDINGS, IMPRESSION, or REPORT RESULT.
   - Do NOT match generic order lists or test package names.

Return ONLY valid JSON.

Schema:
{{
    "found": true,
    "answer": "Exact numerical value/result string (e.g. '5.1 %', '0.88 mg/dL', '125/81 mmHg')",
    "page": 1,
    "bounding_box": {{
        "x1": 0.23,
        "y1": 0.41,
        "x2": 0.68,
        "y2": 0.47
    }},
    "matched_text": "Exact text line as printed in the report table",
    "confidence": 0.99
}}

IMPORTANT:
- "answer": The direct, accurate answer (e.g. "5.1 %", "112.12 mg/dL", "125/81 mmHg", "ECG within normal limits").
- "page": The exact 1-based page number where this answer is printed.
- "bounding_box": Coordinates x1, y1, x2, y2 of the visual answer region on that page (normalized between 0.0 and 1.0 or 0 and 1000, where x1, y1 is top-left and x2, y2 is bottom-right).
- "matched_text": Must exactly match the text string printed in the PDF.
- Do not paraphrase. Do not hallucinate.

If the answer does not exist on ANY page in the PDF, return ONLY:
{{
    "found": false
}}
"""
