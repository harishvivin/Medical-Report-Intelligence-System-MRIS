"""
Prompt Builder Module for Experimental Gemini Pipeline.
Generates spatial prompts for visual PDF localization using Python f-strings.
"""

def build_spatial_prompt(user_question: str) -> str:
    """
    Build a spatial prompt using Python f-strings instructing Gemini to locate the exact region
    and return page_number, box_2d [ymin, xmin, ymax, xmax] (0-1000 scale), and label.
    """
    return f"""Analyze the provided PDF document. Locate the exact region/snippet that answers or contains the visual information for the following question:

Question: "{user_question}"

Instructions:
1. Scan the document and locate the answer.
2. Return a JSON object containing the page_number (1-based index) where the answer is found.
3. Return the 2D bounding box that tightly encloses ONLY the relevant text/snippet that answers the question.
4. Use the key "box_2d" in [ymin, xmin, ymax, xmax] format. Coordinates MUST be integers normalized to a 0-1000 scale relative to the page size.
5. SIBLINGS vs PARENTS RULE: Mother, Father, and Parents are NOT siblings. If asked about siblings, locate ONLY sibling/brother/sister entries. Do NOT include Mother or Father.

Return ONLY a JSON object in this format:
{{
  "page_number": 1,
  "box_2d": [ymin, xmin, ymax, xmax],
  "label": "Short description of the extracted section"
}}
"""

def build_prompt(question: str, total_pages: int = None) -> str:
    """Alias for build_spatial_prompt to maintain backward compatibility."""
    return build_spatial_prompt(question)
