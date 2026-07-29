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
    return f"""You are a precise PDF document localization system.

Analyze ONLY the uploaded PDF.

Question:

{question}

Find the exact location in the PDF that answers the question.

Return ONLY JSON with no additional markdown formatting outside the JSON block.

If the answer is found in the document, return:
{{
  "found": true,
  "page": 1,
  "bounding_box": {{
      "x1": 100,
      "y1": 200,
      "x2": 500,
      "y2": 300
  }},
  "matched_text": "exact text string extracted from the document",
  "confidence": 0.99
}}

Note on bounding box coordinates:
- "page": 1-based page index where the answer is found (e.g. 1 for first page).
- "bounding_box": Normalized integer coordinates from 0 to 1000 relative to the page dimensions:
  - x1: top-left horizontal coordinate (0-1000)
  - y1: top-left vertical coordinate (0-1000)
  - x2: bottom-right horizontal coordinate (0-1000)
  - y2: bottom-right vertical coordinate (0-1000)

If the answer is missing:
{{
  "found": false
}}

Never hallucinate.
Never use outside knowledge.
"""
