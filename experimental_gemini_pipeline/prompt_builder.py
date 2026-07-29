"""
Prompt Builder Module for Experimental Gemini Pipeline.
Generates prompts for visual PDF localization using Python f-strings.
"""

def build_prompt(question: str) -> str:
    """
    Build a prompt using Python f-strings instructing Gemini to locate the answer in the uploaded PDF.
    
    Args:
        question: The user's query/question to locate in the PDF.
        
    Returns:
        Formatted prompt string.
    """
    return f"""You are an expert PDF localization system.

Analyze ONLY the uploaded PDF.

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
- "page": 1-based page number where the answer is found.
- "bounding_box": The coordinates x1, y1, x2, y2 of the answer region on the specified page (normalized between 0.0 and 1.0 or 0 and 1000, where x1, y1 is top-left and x2, y2 is bottom-right).
- "matched_text": Must exactly match the text present in the PDF.
- Do not paraphrase.
- Do not hallucinate.

If the answer does not exist in the PDF, return ONLY:
{{
    "found": false
}}
"""
