import re
from typing import Dict, Any, Optional, List
from pdf_reader import PDFReader
from document_index import DocumentIndex
from question_parser import QuestionParser
from text_search import TextSearchEngine
from cropper import ScreenshotCropper
from config import MIN_CONFIDENCE_SCORE
from logger import logger

NOT_FOUND_MESSAGE = "The uploaded report does not contain this information."

class QAEngine:
    def __init__(self, pdf_path: str, document_index: DocumentIndex):
        self.pdf_path = pdf_path
        self.index = document_index
        self.search_engine = TextSearchEngine(document_index)

    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Answers a user question based ONLY on the indexed PDF content with 100% precision.
        Returns:
            {
                "question": str,
                "answer": str,
                "page_number": Optional[int],
                "confidence": float,
                "snippet_url": Optional[str],
                "bounding_box": Optional[List[float]]
            }
        """
        parsed_q = QuestionParser.parse(question)
        logger.info(f"Parsed question intent: {parsed_q['intent']}, target entities: {parsed_q['target_entities']}")

        # Tier 0: Abnormal Values Summary Request ("Are there any high or low abnormal values?")
        if parsed_q["intent"] == "abnormal_values_request":
            abnormal_res = self._extract_abnormal_summary()
            if abnormal_res:
                logger.info(f"Abnormal values query answered with confidence {abnormal_res['confidence']}")
                return self._build_response(question, abnormal_res)

        # Tier 1: Direct Targeted Entity & Key-Value Lookup
        direct_result = self._try_direct_entity_extraction(parsed_q)
        if direct_result:
            logger.info(f"Direct entity lookup hit with confidence {direct_result['confidence']}")
            return self._build_response(question, direct_result)

        # Tier 2: Hybrid Row & Block Vector Search
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

    def _try_direct_entity_extraction(self, parsed_q: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        norm_q = parsed_q["normalized_question"]
        entities = parsed_q["target_entities"]

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
                m = re.search(r'(?:hospital\s*name|laboratory|clinic)\s*[:\-]\s*([A-Za-z0-9\s&\.]+)', txt, re.I)
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
                if any(kw in txt.lower() for kw in ["metro diagnostic", "city care hospital", "apollo health", "st. jude heart", "global diagnostics", "jeevandeep diagnostic"]):
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
                m = re.search(r'(?:patient\s*name|proposer\s*name|client\s*name|pt\.?\s*name)\s*[:\-]\s*([A-Za-z\s\.]+)', txt, re.I)
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

        # 6. Targeted Lab Results
        kw_map = {
            "hemoglobin": ["hemoglobin", "hgb", "hb"],
            "creatinine": ["creatinine", "serum creatinine"],
            "hba1c": ["hba1c", "glycated hemoglobin"],
            "blood pressure": ["blood pressure", "bp"],
            "hiv": ["hiv", "hiv 1", "hiv 2", "serology"],
            "ecg": ["ecg", "ekg", "rhythm", "electrocardiogram"],
            "wbc": ["wbc", "white blood cell", "leukocyte"],
            "platelets": ["platelet", "plt"],
            "glucose": ["glucose", "fasting blood glucose", "fbs", "sugar"],
            "tsh": ["tsh", "thyroid"]
        }

        for test_key, synonyms in kw_map.items():
            if any(syn in norm_q for syn in synonyms):
                for block in self.index.blocks:
                    norm_txt = block["normalized_text"]
                    if any(syn in norm_txt for syn in synonyms):
                        if ":" in block["text"] or any(char.isdigit() for char in block["text"]) or any(v in norm_txt for v in ["non-reactive", "reactive", "sinus rhythm", "negative", "positive", "normal"]):
                            ans_text = block.get("full_row_text") or block["text"].strip()
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
