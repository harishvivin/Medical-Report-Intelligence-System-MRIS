"""
Prompt Builder Module for Experimental Gemini Pipeline.
Generates prompts for visual PDF localization across all pages using Python f-strings.
"""

def build_prompt(question: str, total_pages: int = None) -> str:
    """
    Build a prompt using Python f-strings instructing Gemini to locate the answer across ALL pages of the PDF.
    
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

    return f"""You are an expert multi-page PDF localization system.

Analyze ONLY the uploaded PDF.

{page_context}

CRITICAL MULTI-PAGE SCANNING INSTRUCTIONS:
- You MUST scan, inspect, and evaluate EVERY SINGLE PAGE in the document from Page 1 through Page {total_str}.
- Do NOT stop analyzing after page 4 or any early page!
- The answer to the question may be located on ANY page (from Page 1 to Page {total_str}).
- Search all {total_str} pages thoroughly before deciding on the final answer location.

The user's question is:

{question}

Your task is NOT to summarize.
Your task is NOT to explain.
Your task is ONLY to locate the exact portion of the PDF that answers this question.

Return ONLY valid JSON.

Schema:
{{
    "found": true,
    "page": 1,
    "bounding_box": {{
        "x1": 0.23,
        "y1": 0.41,
        "x2": 0.68,
        "y2": 0.47
    }},
    "matched_text": "exact text present in PDF",
    "confidence": 0.99
}}

IMPORTANT:
- "page": 1-based page number (between 1 and {total_str}) where the answer is found.
- "bounding_box": Coordinates x1, y1, x2, y2 of the answer region on that specified page (normalized between 0.0 and 1.0 or 0 and 1000, where x1, y1 is top-left and x2, y2 is bottom-right).
- "matched_text": Must exactly match the text present in the PDF.
- Do not paraphrase.
- Do not hallucinate.

If the answer does not exist on ANY of the {total_str} pages in the PDF, return ONLY:
{{
    "found": false
}}
"""
