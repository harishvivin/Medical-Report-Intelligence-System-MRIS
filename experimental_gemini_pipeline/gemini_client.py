"""
Gemini API Client Module for Experimental Gemini Pipeline.
Supports dual API Key failover (GEMINI_API_KEY_PRIMARY -> GEMINI_API_KEY_FALLBACK).
Extracts spatial visual bounding box coordinates (box_2d: [ymin, xmin, ymax, xmax]) across all PDF pages.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List

import fitz  # PyMuPDF for page counting

from .config import (
    GEMINI_API_KEY_PRIMARY,
    GEMINI_API_KEY_FALLBACK,
    MODEL_NAME,
    FALLBACK_MODEL_NAME,
    TEMPERATURE,
)
from .prompt_builder import build_spatial_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("experimental_gemini_client")

CANDIDATE_MODELS = [
    MODEL_NAME,
    "gemini-3.1-flash-lite",
    FALLBACK_MODEL_NAME,
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
]


def _clean_json_response(raw_text: str) -> Dict[str, Any]:
    """
    Parses JSON from raw Gemini model response text, stripping markdown blocks if present.
    """
    text = raw_text.strip()
    
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON directly from model output: {e}. Raw text:\n{raw_text}")
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                data = json.loads(text[start_idx : end_idx + 1])
            except Exception:
                return {"found": False, "error": "Invalid JSON response from model", "raw_response": raw_text}
        else:
            return {"found": False, "error": "Invalid JSON response from model", "raw_response": raw_text}

    # Normalize response format for box_2d and page_number
    page_num = data.get("page_number", data.get("page", 1))
    box_2d = data.get("box_2d", data.get("bounding_box"))
    label = data.get("label", data.get("answer", data.get("matched_text", "")))
    confidence = data.get("confidence", 0.99)

    is_found = True if (box_2d or data.get("found", True)) and not data.get("found") is False else False

    return {
        "found": is_found,
        "page_number": page_num,
        "page": page_num,
        "box_2d": box_2d,
        "bounding_box": box_2d,
        "label": label,
        "answer": label,
        "matched_text": label,
        "confidence": confidence,
        "raw_json": data
    }


def _get_pdf_total_pages(pdf_path: str) -> int:
    try:
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 1


def _call_gemini_with_genai_sdk(api_key: str, pdf_path: str, prompt: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    file_ref = client.files.upload(file=pdf_path)

    last_error = None
    try:
        for model_id in CANDIDATE_MODELS:
            try:
                config = types.GenerateContentConfig(
                    temperature=TEMPERATURE,
                    response_mime_type="application/json",
                )
                response = client.models.generate_content(
                    model=model_id,
                    contents=[file_ref, prompt],
                    config=config,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_error = e
                logger.debug(f"Model {model_id} call failed: {e}")
                continue
    finally:
        try:
            client.files.delete(name=file_ref.name)
        except Exception:
            pass

    if last_error:
        raise last_error
    raise RuntimeError("All candidate models failed to produce a response.")


def _call_gemini_with_legacy_sdk(api_key: str, pdf_path: str, prompt: str) -> str:
    import google.generativeai as genai_legacy

    genai_legacy.configure(api_key=api_key)
    uploaded_file = genai_legacy.upload_file(pdf_path, mime_type="application/pdf")
    
    last_error = None
    try:
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
                    return response.text
            except Exception as e:
                last_error = e
                continue
    finally:
        try:
            genai_legacy.delete_file(uploaded_file.name)
        except Exception:
            pass

    if last_error:
        raise last_error
    raise RuntimeError("Legacy SDK failed for all candidate models.")


def _call_gemini_single_key(api_key: str, pdf_path: str, prompt: str) -> str:
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
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return {"found": False, "error": f"PDF file not found: {pdf_path}"}

    total_pages = _get_pdf_total_pages(str(pdf_file))
    logger.info(f"Loaded PDF: {pdf_file.name} ({total_pages} pages). Building spatial prompt...")

    prompt = build_spatial_prompt(question)
    
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
            logger.warning(f"PRIMARY API Key encountered exception ({type(e).__name__}: {e}). Retrying transparently with FALLBACK key...")
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
    parsed["total_pages_scanned"] = total_pages
    return parsed
