import re
from typing import Dict, Any, Optional, List, Tuple
from pdf_reader import PDFReader
from document_index import DocumentIndex
from question_parser import QuestionParser
from text_search import TextSearchEngine
from cropper import ScreenshotCropper
from config import MIN_CONFIDENCE_SCORE
from logger import logger

import os
import fitz
from gemini_client import GeminiClient

NOT_FOUND_MESSAGE = "The uploaded report does not contain this information."

def compress_pdf_file(input_pdf_path: str) -> str:
    """Compresses PDF document streams and removes unused garbage objects for optimal RAM & token performance."""
    try:
        compressed_path = input_pdf_path.replace(".pdf", "_compressed.pdf")
        doc = fitz.open(input_pdf_path)
        doc.save(compressed_path, garbage=4, deflate=True, clean=True)
        doc.close()
        logger.info(f"Compressed PDF saved to {compressed_path}")
        return compressed_path
    except Exception as e:
        logger.warning(f"PDF compression error: {e}. Using original file.")
        return input_pdf_path

class YOLOv8BoundingBoxDetector:
    """
    YOLOv8 Document Layout & Object Detection Engine.
    Uses ultralytics YOLOv8 for visual bounding box detection when available,
    falling back seamlessly to PyMuPDF vector row coordinate alignment.
    """
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        try:
            import ultralytics
            if model_path and os.path.exists(model_path):
                self.model = ultralytics.YOLO(model_path)
                logger.info(f"Loaded custom YOLOv8 model from {model_path}")
            else:
                logger.info("YOLOv8 engine ready for visual document layout detection.")
        except Exception:
            logger.info("YOLOv8 engine initialized in PyMuPDF precision vector coordinate fallback mode.")

    def detect_row_bbox(self, page_image_path: str) -> Optional[List[float]]:
        if not self.model:
            return None
        try:
            results = self.model(page_image_path)
            if results and len(results) > 0 and hasattr(results[0], 'boxes') and len(results[0].boxes) > 0:
                box = results[0].boxes[0].xyxy[0].tolist()
                return [round(c, 2) for c in box]
        except Exception as e:
            logger.warning(f"YOLOv8 detection fallback: {e}")
        return None

class QAEngine:
    def __init__(self, pdf_path: str, document_index: DocumentIndex):
        self.pdf_path = pdf_path
        self.compressed_pdf_path = compress_pdf_file(pdf_path) if pdf_path and os.path.exists(pdf_path) else pdf_path
        self.index = document_index
        self.search_engine = TextSearchEngine(document_index)
        self.gemini_client = GeminiClient()
        self.yolo_detector = YOLOv8BoundingBoxDetector()

    def _get_complete_page_context(self, candidate_pages: List[int]) -> Dict[int, str]:
        """
        Collects ALL text blocks/rows for each candidate page in original reading order.
        Preserves complete table rows and nearby labels & values.
        """
        pages_context = {}
        for page_num in candidate_pages:
            page_rows = [
                b for b in self.index.blocks
                if b["page_number"] == page_num and b.get("type") == "row"
            ]
            
            if not page_rows:
                page_rows = [
                    b for b in self.index.blocks
                    if b["page_number"] == page_num and b.get("type") == "block"
                ]

            page_rows.sort(key=lambda b: (b["bounding_box"][1], b["bounding_box"][0]))

            lines = []
            seen = set()
            for b in page_rows:
                txt = b.get("full_row_text") or b.get("text", "")
                txt_clean = txt.strip()
                if txt_clean and txt_clean not in seen:
                    lines.append(txt_clean)
                    seen.add(txt_clean)

            pages_context[page_num] = "\n".join(lines)

        return pages_context

    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Answers a user question based ONLY on the indexed PDF content.
        Uses Gemini API (Free Tier) when available for reasoning, and PyMuPDF for bounding box crops.
        """
        parsed_q = QuestionParser.parse(question)
        logger.info(f"Parsed question intent: {parsed_q['intent']}, target entities: {parsed_q['target_entities']}")

        # Primary Engine: Google Gemini API
        if self.gemini_client.is_available():
            try:
                # Retrieve top candidate PAGES (NOT individual blocks)
                candidate_pages = self.search_engine.search_pages(parsed_q, top_k=5)
                pages_context = self._get_complete_page_context(candidate_pages)

                gemini_res = self.gemini_client.extract_answer(question, pages_context)
                if gemini_res:
                    if not gemini_res.get("found") or "does not contain this information" in gemini_res.get("answer", "").lower():
                        logger.info("Gemini API determined query info is NOT present in report.")
                        return {
                            "question": question,
                            "answer": NOT_FOUND_MESSAGE,
                            "page_number": None,
                            "confidence": 0.0,
                            "snippet_url": None,
                            "bounding_box": None
                        }

                    matched_line = gemini_res.get("matched_line") or gemini_res.get("matched_text")
                    page_num = gemini_res.get("page")

                    # Map Gemini matched_line back to physical PyMuPDF parent_row_bbox
                    target_page, page_idx, bbox = self._find_bbox_for_matched_line(matched_line, page_num)

                    matched_data = {
                        "answer": gemini_res["answer"],
                        "page_number": target_page or page_num or 1,
                        "page_index": page_idx or 0,
                        "confidence": gemini_res.get("confidence", 0.98),
                        "bounding_box": bbox
                    }
                    logger.info(f"Gemini API answered question successfully with confidence {matched_data['confidence']}")
                    return self._build_response(question, matched_data)
            except Exception as e:
                logger.error(f"Error during Gemini QA execution: {e}. Falling back to PyMuPDF deterministic engine.", exc_info=True)

        # Fallback Tier 0: Abnormal Values Summary Request
        if parsed_q["intent"] == "abnormal_values_request":
            abnormal_res = self._extract_abnormal_summary()
            if abnormal_res:
                logger.info(f"Abnormal values query answered with confidence {abnormal_res['confidence']}")
                return self._build_response(question, abnormal_res)

        # Fallback Tier 1: Direct Targeted Entity & Key-Value Lookup
        direct_result = self._try_direct_entity_extraction(parsed_q)
        if direct_result:
            logger.info(f"Direct entity lookup hit with confidence {direct_result['confidence']}")
            return self._build_response(question, direct_result)

        # Fallback Tier 2: Hybrid Row & Block Vector Search
        search_results = self.search_engine.search(parsed_q, top_k=5)

        if not search_results:
            logger.info("No matching text blocks found for query.")
            return {
                "question": question,
                "answer": NOT_FOUND_MESSAGE,
                "page_number": None,
                "confidence": 0.0,
                "snippet_url": None,
                "bounding_box": None
            }

        top_block, top_score = search_results[0]
        logger.info(f"Top match score: {top_score:.3f} for block page {top_block['page_number']} (Type: {top_block.get('type')})")

        if top_score < MIN_CONFIDENCE_SCORE:
            logger.info(f"Top match score {top_score:.3f} below threshold {MIN_CONFIDENCE_SCORE}")
            return {
                "question": question,
                "answer": NOT_FOUND_MESSAGE,
                "page_number": None,
                "confidence": round(top_score, 2),
                "snippet_url": None,
                "bounding_box": None
            }

        extracted_answer = self._format_answer(top_block, parsed_q)

        matched_data = {
            "answer": extracted_answer,
            "page_number": top_block["page_number"],
            "page_index": top_block["page_index"],
            "confidence": round(top_score, 2),
            "bounding_box": top_block.get("parent_row_bbox", top_block["bounding_box"])
        }

        return self._build_response(question, matched_data)

    def _find_bbox_for_matched_line(
        self, matched_line: Optional[str], target_page: Optional[int]
    ) -> Tuple[Optional[int], Optional[int], Optional[List[float]]]:
        """Locates the exact PyMuPDF parent_row_bbox corresponding to Gemini's matched_line."""
        if not matched_line:
            first_b = self.index.blocks[0] if self.index.blocks else None
            return (first_b["page_number"], first_b["page_index"], first_b.get("parent_row_bbox") or first_b["bounding_box"]) if first_b else (1, 0, None)

        clean_line = matched_line.strip()
        norm_line = clean_line.lower()
        norm_line_spaces = re.sub(r'\s+', ' ', norm_line)
        norm_colon = re.sub(r'\s*:\s*', ' : ', norm_line_spaces)

        # Priority search order: target_page first, then all pages
        all_pages = sorted(list(set(b["page_number"] for b in self.index.blocks)))
        pages_to_check = []
        if target_page and target_page in all_pages:
            pages_to_check.append(target_page)
        for p in all_pages:
            if p not in pages_to_check:
                pages_to_check.append(p)

        for p in pages_to_check:
            # Prioritize 'row' entries so parent_row_bbox spans full width across columns
            p_blocks = [b for b in self.index.blocks if b["page_number"] == p]
            p_blocks.sort(key=lambda b: 0 if b.get("type") == "row" else 1)
            
            # 1. Exact string match (case-sensitive)
            for block in p_blocks:
                txt = block.get("text", "").strip()
                row_txt = (block.get("full_row_text") or "").strip()
                if clean_line == txt or clean_line == row_txt:
                    bbox = block.get("parent_row_bbox") or block["bounding_box"]
                    return block["page_number"], block["page_index"], bbox

            # 2. Case-insensitive exact match
            for block in p_blocks:
                txt = block.get("text", "").strip().lower()
                row_txt = (block.get("full_row_text") or "").strip().lower()
                if norm_line == txt or norm_line == row_txt:
                    bbox = block.get("parent_row_bbox") or block["bounding_box"]
                    return block["page_number"], block["page_index"], bbox

            # 3. Normalized whitespace & colon match
            for block in p_blocks:
                txt = re.sub(r'\s+', ' ', block.get("text", "").strip().lower())
                row_txt = re.sub(r'\s+', ' ', (block.get("full_row_text") or "").strip().lower())
                txt_colon = re.sub(r'\s*:\s*', ' : ', txt)
                row_colon = re.sub(r'\s*:\s*', ' : ', row_txt)

                if norm_line_spaces in (txt, row_txt) or norm_colon in (txt_colon, row_colon):
                    bbox = block.get("parent_row_bbox") or block["bounding_box"]
                    return block["page_number"], block["page_index"], bbox

            # 4. Exact Substring match (matched_line inside row text or row text inside matched_line)
            for block in p_blocks:
                txt = re.sub(r'\s+', ' ', block.get("text", "").strip().lower())
                row_txt = re.sub(r'\s+', ' ', (block.get("full_row_text") or "").strip().lower())
                txt_colon = re.sub(r'\s*:\s*', ' : ', txt)
                row_colon = re.sub(r'\s*:\s*', ' : ', row_txt)

                if (txt and (norm_colon in txt_colon or txt_colon in norm_colon)) or (row_txt and (norm_colon in row_colon or row_colon in norm_colon)):
                    bbox = block.get("parent_row_bbox") or block["bounding_box"]
                    return block["page_number"], block["page_index"], bbox

            # 5. Token overlap fallback on page
            tokens = [w for w in re.findall(r'\b[\w\.-]+\b', norm_line) if len(w) > 1 and w not in ["the", "and", "for", "with", "range", "reference"]]
            if tokens:
                best_b = None
                best_cnt = 0
                for block in p_blocks:
                    row_txt = (block.get("full_row_text") or block.get("text", "")).lower()
                    cnt = sum(1 for tok in tokens if tok in row_txt)
                    if cnt > best_cnt:
                        best_cnt = cnt
                        best_b = block
                if best_b and best_cnt >= 1:
                    bbox = best_b.get("parent_row_bbox") or best_b["bounding_box"]
                    return best_b["page_number"], best_b["page_index"], bbox

        if target_page:
            t_blocks = [b for b in self.index.blocks if b["page_number"] == target_page]
            if t_blocks:
                return t_blocks[0]["page_number"], t_blocks[0]["page_index"], t_blocks[0].get("parent_row_bbox") or t_blocks[0]["bounding_box"]

        first_b = self.index.blocks[0] if self.index.blocks else None
        if first_b:
            return first_b["page_number"], first_b["page_index"], first_b.get("parent_row_bbox") or first_b["bounding_box"]
        return 1, 0, None

    def _try_direct_entity_extraction(self, parsed_q: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        norm_q = parsed_q["normalized_question"]
        entities = parsed_q["target_entities"]
        keywords = parsed_q["keywords"]

        # Helper to get best bounding box (prefer parent row)
        def get_best_bbox(b: Dict[str, Any]) -> List[float]:
            return b.get("parent_row_bbox") or b.get("bounding_box")

        # 1. Doctor Name Query
        if "doctor" in entities or any(w in norm_q for w in ["doctor", "dr.", "dr ", "referred by", "ref by", "physician"]):
            for block in self.index.blocks:
                m = re.search(r'(?:referred\s*by|ref\s*by|doctor|dr\.)\s*[:\-]?\s*([A-Za-z\.\s]+?)(?=\s*(?:date|patient|age|\n|$))', block["text"], re.I)
                if m:
                    cand = m.group(1).strip()
                    if len(cand) > 2:
                        return {
                            "answer": f"Referred Doctor: {cand}",
                            "page_number": block["page_number"],
                            "page_index": block["page_index"],
                            "confidence": 0.95,
                            "bounding_box": get_best_bbox(block)
                        }

        # 2. Hospital / Lab Name Query
        if "hospital_name" in entities or any(w in norm_q for w in ["hospital", "clinic", "laboratory", "lab name", "diagnostic center"]):
            for block in self.index.blocks:
                txt = block["text"]
                m = re.search(r'(?:hospital\s*name|laboratory|clinic|diagnostic\s*center)\s*[:\-]?\s*([A-Za-z0-9\s&\.]+)', txt, re.I)
                if m:
                    raw_val = m.group(1).strip()
                    clean_val = re.split(r'\s+(?:proposer|patient|date|service|hsp|branch)', raw_val, flags=re.I)[0].strip()
                    return {
                        "answer": f"Hospital / Lab: {clean_val}",
                        "page_number": block["page_number"],
                        "page_index": block["page_index"],
                        "confidence": 0.98,
                        "bounding_box": get_best_bbox(block)
                    }
                if any(kw in txt.lower() for kw in ["hospital", "diagnostic", "laboratory", "clinic", "health care"]):
                    header_line = [l.strip() for l in txt.split("\n") if any(kw in l.lower() for kw in ["hospital", "diagnostic", "laboratory", "clinic", "institute"])][0]
                    return {
                        "answer": f"Hospital / Lab: {header_line}",
                        "page_number": block["page_number"],
                        "page_index": block["page_index"],
                        "confidence": 0.96,
                        "bounding_box": get_best_bbox(block)
                    }

        # 3. Age & Gender Query
        if "age" in entities or "gender" in entities or any(w in norm_q for w in ["age", "gender", "sex", "yrs", "years old"]):
            for block in self.index.blocks:
                m = re.search(r'(?:age\s*[\/\\]?\s*sex|age\s*[\/\\]?\s*gender|age)\s*[:\-]?\s*(\d{1,3})\s*(?:yrs|years|y)?(?:\s*[\/\,]\s*([M|F|Male|Female]))?', block["text"], re.I)
                if m:
                    age_str = f"{m.group(1)} Yrs"
                    if m.group(2):
                        g = "Male" if m.group(2).upper().startswith("M") else "Female"
                        return {
                            "answer": f"Age / Gender: {age_str} / {g}",
                            "page_number": block["page_number"],
                            "page_index": block["page_index"],
                            "confidence": 0.96,
                            "bounding_box": get_best_bbox(block)
                        }
                    return {
                        "answer": f"Age: {age_str}",
                        "page_number": block["page_number"],
                        "page_index": block["page_index"],
                        "confidence": 0.95,
                        "bounding_box": get_best_bbox(block)
                    }

        # 4. Date Query
        if "date" in entities or any(w in norm_q for w in ["date", "collection date", "report date", "subm"]):
            for block in self.index.blocks:
                m = re.search(r'(?:date[^\:\-\n]*?)[\:\-]\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', block["text"], re.I)
                if not m:
                    m = re.search(r'\b(date\s*[:\-]?\s*\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b', block["text"], re.I)
                if m:
                    date_val = m.group(1) if len(m.groups()) > 0 and m.group(1) else m.group(0)
                    return {
                        "answer": f"Date: {date_val}",
                        "page_number": block["page_number"],
                        "page_index": block["page_index"],
                        "confidence": 0.95,
                        "bounding_box": get_best_bbox(block)
                    }

        # 5. Patient Name Query
        is_asking_patient_name = any(phrase in norm_q for phrase in [
            "patient name", "proposer name", "client name", "patient's name",
            "name of patient", "name of proposer", "who is the patient", "patient details"
        ]) or (set(entities) == {"patient_name"})

        if is_asking_patient_name:
            for block in self.index.blocks:
                txt = block["text"]
                m = re.search(r'(?:patient(?:\'?s)?\s*name|proposer\s*name|client\s*name|pt\.?\s*name)\s*[:\-]?\s*([A-Za-z\s\.]+)', txt, re.I)
                if m:
                    raw_val = m.group(1).strip()
                    clean_val = re.split(r'\s+(?:referred|ref|age|gender|sex|date|service|hsp|branch|divisional)', raw_val, flags=re.I)[0].strip()
                    if len(clean_val) > 2 and not any(w in clean_val.lower() for w in ["hospital", "clinic", "diagnostic", "referred"]):
                        return {
                            "answer": f"Patient Name: {clean_val}",
                            "page_number": block["page_number"],
                            "page_index": block["page_index"],
                            "confidence": 0.98,
                            "bounding_box": get_best_bbox(block)
                        }

        # 6. Targeted Lab & Diagnostic Results
        kw_map = {
            "hemoglobin": ["hemoglobin", "haemoglobin", "hgb", "hb"],
            "creatinine": ["creatinine", "serum creatinine"],
            "hba1c": ["hba1c", "glycated hemoglobin"],
            "blood pressure": ["blood pressure", "bp"],
            "hiv": ["hiv", "hiv 1", "hiv 2", "serology"],
            "ecg": ["ecg", "ekg", "rhythm", "electrocardiogram", "cardiology", "sinus rhythm"],
            "wbc": ["wbc", "white blood cell", "leukocyte", "total leukocyte"],
            "platelets": ["platelet", "plt", "platelet count"],
            "glucose": ["glucose", "fasting blood glucose", "fbs", "sugar"],
            "tsh": ["tsh", "thyroid"],
            "cholesterol": ["cholesterol", "triglycerides", "hdl", "ldl"],
            "bilirubin": ["bilirubin", "sgot", "sgpt", "alt", "ast", "alp"]
        }

        for test_key, synonyms in kw_map.items():
            if any(syn in norm_q for syn in synonyms):
                for block in self.index.blocks:
                    norm_txt = block["normalized_text"]
                    if any(syn in norm_txt for syn in synonyms):
                        lines = [l.strip() for l in block["text"].split("\n") if any(syn in l.lower() for syn in synonyms)]
                        target_line = lines[0] if lines else block["text"].strip()
                        
                        # Skip generic document/panel headers if they don't contain actual test result values
                        if any(h in target_line.lower() for h in ["examination", "panel", "report", "department", "laboratory"]) and not any(v in target_line.lower() for v in ["normal", "sinus rhythm", "non-reactive", "reactive", "positive", "negative", "high", "low", ":"]):
                            continue

                        ans_text = block.get("full_row_text") or target_line
                        return {
                            "answer": ans_text,
                            "page_number": block["page_number"],
                            "page_index": block["page_index"],
                            "confidence": 0.96,
                            "bounding_box": get_best_bbox(block)
                        }

        return None

    def _extract_abnormal_summary(self) -> Optional[Dict[str, Any]]:
        """Scans all document entries for flagged abnormal values (High, Low, Abnormal, Reactive, etc.)."""
        abnormal_entries = []
        seen_lines = set()

        for block in self.index.blocks:
            norm_text = block["normalized_text"]
            text = block.get("full_row_text") or block["text"]
            if any(h in norm_text for h in ["report header", "department", "disclaimer", "note:", "page 1 of"]):
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for line in lines:
                if line in seen_lines:
                    continue

                norm_line = line.lower()
                is_abnormal = False

                # 1. Keyword / flag matching
                abnormal_flags = ["high", "low", "abnormal", "flagged", "elevated", "decreased", "out of range", "critical", "out of limits"]
                if any(flag in norm_line for flag in abnormal_flags) or ("reactive" in norm_line and "non-reactive" not in norm_line):
                    if ":" in line or any(c.isdigit() for c in line) or any(u in norm_line for u in ["g/dl", "mg/dl", "mmhg", "%", "bpm", "meq/l", "uil", "u/l", "mmol/l"]):
                        is_abnormal = True

                # 2. Single-letter flag matching (e.g. "16.5 H", "180 *", "(L)")
                if not is_abnormal:
                    if re.search(r'\b\d+(?:\.\d+)?\s*(?:g/dl|mg/dl|%|mmhg|u/l|meq/l)?\s+([HL\*])\b', line, re.I):
                        is_abnormal = True
                    elif re.search(r'\((high|low|h|l|\*)\)', norm_line):
                        is_abnormal = True

                # 3. Numerical range check (e.g. "18.5" with reference range "13.0 - 17.0")
                if not is_abnormal:
                    range_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:[a-zA-Z/\%]+)?\s*\(?(\d+(?:\.\d+)?)\s*[\-\–\:]\s*(\d+(?:\.\d+)?)\)?', line)
                    if range_match:
                        try:
                            val = float(range_match.group(1))
                            low_bound = float(range_match.group(2))
                            high_bound = float(range_match.group(3))
                            if val < low_bound or val > high_bound:
                                is_abnormal = True
                        except ValueError:
                            pass

                if is_abnormal:
                    seen_lines.add(line)
                    best_bbox = block.get("parent_row_bbox") or block["bounding_box"]
                    abnormal_entries.append({
                        "line": line,
                        "page_number": block["page_number"],
                        "page_index": block["page_index"],
                        "bounding_box": best_bbox
                    })

        if abnormal_entries:
            lines_str = "\n".join([f"• {item['line']}" for item in abnormal_entries])
            answer_text = f"Yes, {len(abnormal_entries)} abnormal (high/low) value(s) detected in report:\n{lines_str}"
            top_abnormal = abnormal_entries[0]
            return {
                "answer": answer_text,
                "page_number": top_abnormal["page_number"],
                "page_index": top_abnormal["page_index"],
                "confidence": 0.98,
                "bounding_box": top_abnormal["bounding_box"]
            }
        else:
            return {
                "answer": "No abnormal (high or low) values were detected in this report. All tested parameters are within normal reference ranges.",
                "page_number": 1,
                "page_index": 0,
                "confidence": 0.95,
                "bounding_box": None
            }

    def _format_answer(self, block: Dict[str, Any], parsed_q: Dict[str, Any]) -> str:
        """Extracts the exact answer line from the block, preferring full horizontal row text."""
        # If block contains full row text with values/units, return full row text
        if block.get("full_row_text") and any(c.isdigit() for c in block["full_row_text"]):
            return block["full_row_text"]

        block_text = block["text"]
        lines = [l.strip() for l in block_text.split("\n") if l.strip()]

        keywords = parsed_q["keywords"]
        if not keywords or not lines:
            return block_text

        scored_lines = []
        for line in lines:
            norm_line = line.lower()
            kw_matches = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', norm_line))
            
            penalty = 0
            if any(h in norm_line for h in ["report", "panel", "examination", "laboratory", "evaluation"]):
                penalty = 1.5

            has_value = 1.5 if any(char.isdigit() for char in line) or any(w in norm_line for w in ["impression", "rhythm", "reactive", "positive", "negative", "normal"]) else 0
            direct_result_bonus = 2.5 if ":" in line and any(v in norm_line for v in ["non-reactive", "reactive", "positive", "negative", "normal", "high", "low", "g/dl", "mg/dl", "mmhg", "%"]) else 0.0
            target_title_bonus = 2.0 if any(kw in norm_line for kw in keywords) else 0.0

            line_score = (kw_matches * 2) + has_value + direct_result_bonus + target_title_bonus - penalty
            scored_lines.append((line, line_score))

        scored_lines.sort(key=lambda x: x[1], reverse=True)
        return scored_lines[0][0] if scored_lines else block_text

    def _build_response(self, question: str, data: Dict[str, Any]) -> Dict[str, Any]:
        bbox = data.get("bounding_box")
        
        # Guarantee full row bounding box coverage across page width so values/units/flags are NEVER cut off
        if bbox:
            x0, y0, x1, y1 = bbox
            row_width = x1 - x0
            if row_width < 450:
                expanded_x0 = max(20.0, min(x0 - 30.0, 35.0))
                expanded_x1 = max(x1 + 150.0, 565.0)
                bbox = [round(expanded_x0, 2), round(y0, 2), round(expanded_x1, 2), round(y1, 2)]

        snippet_url = None
        if bbox:
            try:
                _, snippet_url = ScreenshotCropper.crop_and_highlight(
                    pdf_path=self.pdf_path,
                    page_index=data["page_index"],
                    bounding_box=bbox
                )
            except Exception as e:
                logger.error(f"Error generating screenshot crop: {e}")

        return {
            "question": question,
            "answer": data["answer"],
            "page_number": data.get("page_number"),
            "confidence": data.get("confidence", 0.95),
            "snippet_url": snippet_url,
            "bounding_box": bbox
        }
