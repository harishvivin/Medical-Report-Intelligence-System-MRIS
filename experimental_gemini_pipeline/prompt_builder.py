"""
Prompt Builder Module for Experimental Gemini Pipeline.
Generates inline prompts for visual PDF localization using Python f-strings.
"""

def build_prompt(question: str, total_pages: int = None) -> str:
    """
    Build a prompt using Python f-strings instructing Gemini to locate the answer and coordinates in the PDF.
    
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

Task: Give me the exact answer and the page bounding box coordinates for this particular question in the PDF:
{question}

CRITICAL MULTI-PAGE SCANNING & ACCURACY INSTRUCTIONS:
- You MUST scan, inspect, and evaluate EVERY SINGLE PAGE in the document from Page 1 through Page {total_str}.
- Do NOT stop analyzing after page 4 or any early page!
- Search for the ACTUAL TEST RESULT, FINDINGS, IMPRESSION, or VALUE that directly answers "{question}".
- Do NOT match generic header lists, order packages, or test names (e.g. if asking for ECG results, locate the actual ECG findings/impression, NOT just the phrase 'ECG-R' in a list of ordered tests).
- Your job is to identify the exact page, extracted answer, and bounding box coordinates of the region containing the answer.

Return ONLY valid JSON.

Schema:
{{
    "found": true,
    "answer": "Concise extracted answer string",
    "page": 1,
    "bounding_box": {{
        "x1": 0.23,
        "y1": 0.41,
        "x2": 0.68,
        "y2": 0.47
    }},
    "matched_text": "Exact text string as printed on the PDF page",
    "confidence": 0.99
}}

IMPORTANT:
- "answer": The direct concise answer value (e.g. "ECG within normal limits", "14.8 g/dL", "Negative").
- "page": 1-based page number (between 1 and {total_str}) where the answer is found.
- "bounding_box": Coordinates x1, y1, x2, y2 of the visual answer region on that page (normalized between 0.0 and 1.0 or 0 and 1000, where x1, y1 is top-left and x2, y2 is bottom-right).
- "matched_text": Must exactly match the text string printed in the PDF.
- Do not paraphrase. Do not hallucinate.

If the answer does not exist on ANY of the {total_str} pages in the PDF, return ONLY:
{{
    "found": false
}}
"""
