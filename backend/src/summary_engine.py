import re
from typing import Dict, Any, List, Tuple
from document_index import DocumentIndex
from logger import logger

class SummaryEngine:
    def __init__(self, blocks: List[Dict[str, Any]]):
        self.blocks = blocks
        self.full_text = "\n".join([b["text"] for b in blocks])
        self.full_text_lower = self.full_text.lower()

    def generate_summary(self) -> Dict[str, Any]:
        """
        Extracts structured medical report summary:
        - Patient Information
        - Hospital / Lab Name
        - Tests Performed
        - Important Findings
        - Abnormal Values
        - Recommendations (if present)
        """
        patient_info = self._extract_patient_info()
        hospital_name = self._extract_hospital_name()
        tests_performed = self._extract_tests_performed()
        findings, abnormal_values = self._extract_findings_and_abnormals()
        recommendations = self._extract_recommendations()

        return {
            "patient_info": patient_info,
            "hospital": hospital_name,
            "tests_performed": tests_performed,
            "important_findings": findings,
            "abnormal_values": abnormal_values,
            "recommendations": recommendations
        }

    def _extract_patient_info(self) -> Dict[str, str]:
        info = {
            "name": "Not specified in report",
            "age": "Not specified",
            "gender": "Not specified",
            "ref_doctor": "Not specified",
            "date": "Not specified"
        }

        # Patient Name Patterns
        name_match = re.search(
            r'(?:patient\s*name|name|pt\.\s*name)\s*[:\-]?\s*([A-Za-z\.\s]+?)(?=\s*(?:age|sex|gender|date|ref|id|mrn|\n|$))',
            self.full_text, re.IGNORECASE
        )
        if name_match:
            candidate = name_match.group(1).strip()
            if len(candidate) > 2 and not any(w in candidate.lower() for w in ["hospital", "clinic", "report"]):
                info["name"] = candidate

        # Age & Gender Patterns
        age_gender_match = re.search(
            r'(?:age\s*[\/\\]?\s*sex|age\s*[\/\\]?\s*gender|age)\s*[:\-]?\s*(\d{1,3})\s*(?:yrs|years|y)?(?:\s*[\/\,]\s*([M|F|Male|Female]))?',
            self.full_text, re.IGNORECASE
        )
        if age_gender_match:
            info["age"] = age_gender_match.group(1) + " Yrs"
            if age_gender_match.group(2):
                g = age_gender_match.group(2).upper()
                info["gender"] = "Male" if g.startswith("M") else "Female" if g.startswith("F") else g

        if info["gender"] == "Not specified":
            gender_match = re.search(r'\b(Male|Female)\b', self.full_text, re.IGNORECASE)
            if gender_match:
                info["gender"] = gender_match.group(1).capitalize()

        # Date pattern
        date_match = re.search(r'\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b', self.full_text)
        if date_match:
            info["date"] = date_match.group(1)

        # Doctor pattern
        doc_match = re.search(r'(?:ref\s*by|referred\s*by|doctor|dr\.)\s*[:\-]?\s*([A-Za-z\.\s]+?)(?=\s*(?:date|patient|age|\n|$))', self.full_text, re.IGNORECASE)
        if doc_match:
            cand = doc_match.group(1).strip()
            if len(cand) > 2:
                info["ref_doctor"] = cand

        return info

    def _extract_hospital_name(self) -> str:
        # Search first page text blocks for clinic/hospital/laboratory names
        lines = self.full_text.split("\n")[:10]  # top 10 lines of report header
        for line in lines:
            if any(kw in line.lower() for kw in ["hospital", "diagnostic", "laboratory", "labs", "clinic", "health center", "institute"]):
                return line.strip()
        return "Medical Diagnostic Laboratory"

    def _extract_tests_performed(self) -> List[str]:
        tests = set()
        test_keywords = [
            ("Complete Blood Count (CBC)", ["cbc", "complete blood count", "hemogram"]),
            ("Renal Function Test (KFT)", ["creatinine", "kidney function", "kft", "renal", "blood urea"]),
            ("Liver Function Test (LFT)", ["lft", "liver function", "sgot", "sgpt", "bilirubin"]),
            ("Lipid Profile", ["lipid", "cholesterol", "triglycerides", "hdl", "ldl"]),
            ("Diabetes & Glycemic Index", ["hba1c", "glucose", "fasting sugar", "glycated"]),
            ("Thyroid Panel", ["thyroid", "tsh", "t3", "t4"]),
            ("Infectious Disease Screen", ["hiv", "hepatitis", "serology", "hiv 1"]),
            ("Cardiology / ECG", ["ecg", "ekg", "electrocardiogram", "heart rate", "rhythm"])
        ]

        for display_name, synonyms in test_keywords:
            if any(syn in self.full_text_lower for syn in synonyms):
                tests.add(display_name)

        if not tests:
            tests.add("General Medical Diagnostics")
        return sorted(list(tests))

    def _extract_findings_and_abnormals(self) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        findings = []
        abnormal_values = []

        lines = self.full_text.split("\n")
        
        # Regex to capture test results like: "Hemoglobin 14.5 g/dL (13.0 - 17.0)" or "Creatinine: 1.8 mg/dL [High]"
        pattern = re.compile(
            r'([A-Za-z0-9\s\-\(\)]+?)\s*[:\=]?\s*(\d+(?:\.\d+)?|\bNon-Reactive\b|\bReactive\b|\bNormal\b|\bSinus Rhythm\b)\s*([a-zA-Z\/\%]+)?\s*(?:\(?([0-9\.\-\s]+)\)?)?\s*(\bHigh\b|\bLow\b|\bAbnormal\b|\bFlagged\b|\*+)?',
            re.IGNORECASE
        )

        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) < 4:
                continue

            match = pattern.search(line_str)
            if match:
                test_name = match.group(1).strip()
                val = match.group(2).strip()
                unit = match.group(3) or ""
                ref_range = match.group(4) or ""
                flag = match.group(5) or ""

                # Ignore non-medical noise lines
                if any(w in test_name.lower() for w in ["page", "patient", "date", "doctor", "name", "age", "phone"]):
                    continue

                if len(test_name) > 2 and len(test_name) < 45:
                    finding_item = {
                        "parameter": test_name,
                        "value": f"{val} {unit}".strip(),
                        "reference_range": ref_range if ref_range else "N/A",
                        "status": "Abnormal" if flag or "high" in line_str.lower() or "low" in line_str.lower() else "Normal"
                    }
                    findings.append(finding_item)

                    # Check if flagged abnormal
                    if flag or "high" in line_str.lower() or "low" in line_str.lower() or "reactive" in val.lower() or "abnormal" in line_str.lower():
                        abnormal_values.append(finding_item)

        # Fallback summary if structured regex lines were not explicitly formatted
        if not findings:
            for b in self.blocks[:6]:
                for line in b["text"].split("\n"):
                    if any(char.isdigit() for char in line) and len(line) < 60:
                        findings.append({
                            "parameter": line.strip(),
                            "value": "Observed in report",
                            "reference_range": "N/A",
                            "status": "Recorded"
                        })

        return findings[:12], abnormal_values[:8]

    def _extract_recommendations(self) -> List[str]:
        recs = []
        rec_triggers = ["recommendation", "advised", "advice", "follow up", "follow-up", "note:", "impression", "conclusion"]
        
        for line in self.full_text.split("\n"):
            line_str = line.strip()
            if any(trig in line_str.lower() for trig in rec_triggers):
                if len(line_str) > 8 and not any(w in line_str.lower() for w in ["page", "date"]):
                    recs.append(line_str)

        return recs[:4]
