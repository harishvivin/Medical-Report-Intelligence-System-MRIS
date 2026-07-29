"""
Gemini API Client Module for Experimental Gemini Pipeline.
Supports dual API Key failover (GEMINI_API_KEY_PRIMARY -> GEMINI_API_KEY_FALLBACK).
Extracts visual location of requested answers in PDF using Flash-Lite model.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List

from .config import (
    GEMINI_API_KEY_PRIMARY,
    GEMINI_API_KEY_FALLBACK,
    MODEL_NAME,
    FALLBACK_MODEL_NAME,
    TEMPERATURE,
)
from .prompt_builder import build_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("experimental_gemini_client")

# Candidate model list to ensure model availability
CANDIDATE_MODELS = [
    MODEL_NAME,
    FALLBACK_MODEL_NAME,
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash",
]


def _clean_json_response(raw_text: str) -> Dict[str, Any]:
    """
    Parses JSON from raw Gemini model response text, stripping markdown blocks if present.
    """
    text = raw_text.strip()
    
    # Strip markdown code blocks ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON directly from model output: {e}. Raw text:\n{raw_text}")
        # Try to locate JSON object substring
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(text[start_idx : end_idx + 1])
            except Exception:
                pass
        return {"found": False, "error": "Invalid JSON response from model", "raw_response": raw_text}


def _call_gemini_with_genai_sdk(api_key: str, pdf_path: str, prompt: str) -> str:
    """
    Calls Gemini API using official google-genai SDK.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    
    # Read PDF bytes directly as Part
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_part = types.Part.from_bytes(
        data=pdf_bytes,
        mime_type="application/pdf"
    )

    last_error = None
    # Try candidate models
    for model_id in CANDIDATE_MODELS:
        try:
            config = types.GenerateContentConfig(
                temperature=TEMPERATURE,
                response_mime_type="application/json",
            )
            response = client.models.generate_content(
                model=model_id,
                contents=[pdf_part, prompt],
                config=config,
            )
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = e
            logger.debug(f"Model {model_id} call failed with key: {e}")
            continue

    if last_error:
        raise last_error
    raise RuntimeError("All candidate models failed to produce a response.")


def _call_gemini_with_legacy_sdk(api_key: str, pdf_path: str, prompt: str) -> str:
    """
    Fallback method using google-generativeai legacy SDK if google-genai fails.
    """
    import google.generativeai as genai_legacy

    genai_legacy.configure(api_key=api_key)
    
    # Upload PDF file
    uploaded_file = genai_legacy.upload_file(pdf_path, mime_type="application/pdf")
    
    last_error = None
    for model_id in CANDIDATE_MODELS:
        try:
            model = genai_legacy.GenerativeModel(
                model_name=model_id,
                generation_config={
                    "temperature": TEMPERATURE,
                    "response_mime_type": "application/json",
                }
            )
            response = model.generate_content([uploaded_file, prompt])
            if response and response.text:
                # Cleanup uploaded file asynchronously / quietly
                try:
                    genai_legacy.delete_file(uploaded_file.name)
                except Exception:
                    pass
                return response.text
        except Exception as e:
            last_error = e
            continue

    # Cleanup uploaded file
    try:
        genai_legacy.delete_file(uploaded_file.name)
    except Exception:
        pass

    if last_error:
        raise last_error
    raise RuntimeError("Legacy SDK failed for all candidate models.")


def _call_gemini_single_key(api_key: str, pdf_path: str, prompt: str) -> str:
    """
    Performs API call with a single key, trying modern SDK then legacy SDK.
    """
    if not api_key:
        raise ValueError("API key is empty")

    try:
        return _call_gemini_with_genai_sdk(api_key, pdf_path, prompt)
    except Exception as err:
        logger.debug(f"google-genai SDK attempt failed: {err}. Trying google-generativeai SDK...")
        try:
            return _call_gemini_with_legacy_sdk(api_key, pdf_path, prompt)
        except Exception as legacy_err:
            raise RuntimeError(f"Both SDKs failed for key: {err} | {legacy_err}")


def locate_answer_in_pdf(pdf_path: str, question: str) -> Dict[str, Any]:
    """
    Primary interface to locate answer in PDF using Gemini with transparent primary -> fallback key retry.

    Args:
        pdf_path: Path to local PDF report file.
        question: User query string.

    Returns:
        Structured JSON dictionary with visual localization details.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return {"found": False, "error": f"PDF file not found: {pdf_path}"}

    prompt = build_prompt(question)
    
    # Key strategy: Primary Key -> Fallback Key retry
    primary_key = GEMINI_API_KEY_PRIMARY
    fallback_key = GEMINI_API_KEY_FALLBACK

    raw_response_text = None
    used_key_type = "PRIMARY"

    # Attempt 1: Primary API Key
    if primary_key:
        try:
            logger.info("Attempting Gemini API call with PRIMARY key...")
            raw_response_text = _call_gemini_single_key(primary_key, str(pdf_file), prompt)
        except Exception as e:
            logger.warning(f"PRIMARY API Key encounter exception ({type(e).__name__}: {e}). Retrying transparently with FALLBACK key...")
            raw_response_text = None

    # Attempt 2: Fallback API Key (Transparent failover)
    if raw_response_text is None:
        if fallback_key and fallback_key != primary_key:
            try:
                logger.info("Attempting Gemini API call with FALLBACK key...")
                raw_response_text = _call_gemini_single_key(fallback_key, str(pdf_file), prompt)
                used_key_type = "FALLBACK"
            except Exception as e:
                logger.error(f"FALLBACK API Key also encountered failure ({type(e).__name__}: {e}).")
                return {
                    "found": False,
                    "error": f"Both Primary and Fallback API key attempts failed. Last exception: {e}",
                }
        else:
            if not primary_key:
                return {
                    "found": False,
                    "error": "No Gemini API key provided. Set GEMINI_API_KEY_PRIMARY or GEMINI_API_KEY_FALLBACK.",
                }
            return {
                "found": False,
                "error": "PRIMARY API key failed and no distinct FALLBACK API key configured.",
            }

    parsed = _clean_json_response(raw_response_text)
    parsed["api_key_used"] = used_key_type
    return parsed
