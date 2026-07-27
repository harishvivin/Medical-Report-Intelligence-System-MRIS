import re
from typing import Dict, Any, List, Set

# Medical entity mapping for targeted keyword extraction
MEDICAL_ENTITIES = {
    "hemoglobin": ["hemoglobin", "hgb", "hb", "haemoglobin"],
    "creatinine": ["creatinine", "serum creatinine"],
    "hba1c": ["hba1c", "glycated hemoglobin", "hb a1c", "a1c"],
    "blood pressure": ["blood pressure", "bp", "systolic", "diastolic"],
    "hiv": ["hiv", "hiv 1", "hiv 2", "human immunodeficiency virus", "serology", "elisa"],
    "ecg": ["ecg", "ekg", "electrocardiogram", "heart rate", "rhythm"],
    "patient_name": ["patient name", "patient", "name", "proposer name", "client name", "pt name"],
    "hospital_name": ["hospital name", "hospital", "clinic", "laboratory", "lab", "center", "institute", "diagnostic"],
    "doctor": ["doctor", "dr", "referred by", "ref by", "physician"],
    "date": ["date", "collection date", "report date", "subm"],
    "age": ["age", "yrs", "years old", "yo"],
    "gender": ["gender", "sex", "male", "female"],
    "diagnosis": ["diagnosis", "impression", "conclusion", "opinion", "finding", "result", "test details"],
    "wbc": ["wbc", "white blood cell", "leukocyte", "tlc"],
    "platelets": ["platelet", "platelet count", "plt"],
    "glucose": ["glucose", "sugar", "fasting sugar", "ppbs", "fbs", "blood sugar"],
    "cholesterol": ["cholesterol", "triglycerides", "hdl", "ldl", "lipid", "serum cholesterol"],
    "thyroid": ["tsh", "t3", "t4", "thyroid"],
    "urea": ["urea", "bun", "blood urea"],
    "liver": ["sgot", "sgpt", "ast", "alt", "bilirubin", "alkaline phosphatase", "alp", "ggt"]
}

SUMMARY_TRIGGER_WORDS = {"summary", "summarize", "overview", "report summary", "brief", "key findings"}
COMPARISON_TRIGGER_WORDS = {"compare", "comparison", "difference", "versus", "vs", "higher than", "lower than"}
LOOKUP_TRIGGER_WORDS = {"what is", "where is", "show", "find", "get", "value of", "level of", "check", "tell me"}
ABNORMAL_TRIGGER_WORDS = {
    "abnormal", "high", "low", "out of range", "flagged", "abnormalities",
    "high or low", "elevated", "low values", "high values", "abnormal values",
    "any high", "any low", "out of reference", "out-of-range", "out of limits"
}

class QuestionParser:
    @staticmethod
    def parse(question: str) -> Dict[str, Any]:
        """
        Parses a user question into intent type and extracted keywords.
        Intents: 'abnormal_values_request', 'summary_request', 'comparison_request', 'lookup_request', 'keyword_search'
        """
        raw_q = question.strip()
        norm_q = raw_q.lower()

        intent = "lookup_request"

        # Check intent - abnormal value general queries
        is_abnormal_q = any(w in norm_q for w in ABNORMAL_TRIGGER_WORDS) or ("high" in norm_q and "low" in norm_q)
        is_specific_lab_q = any(w in norm_q for w in ["hemoglobin", "creatinine", "hba1c", "blood pressure", "wbc", "platelet", "glucose", "tsh"])

        if is_abnormal_q and not is_specific_lab_q:
            intent = "abnormal_values_request"
        elif any(w in norm_q for w in SUMMARY_TRIGGER_WORDS):
            intent = "summary_request"
        elif any(w in norm_q for w in COMPARISON_TRIGGER_WORDS):
            intent = "comparison_request"
        elif any(w in norm_q for w in LOOKUP_TRIGGER_WORDS):
            intent = "lookup_request"
        else:
            intent = "keyword_search"

        # Extract keywords and medical entity triggers
        target_entities = []
        for entity_key, synonyms in MEDICAL_ENTITIES.items():
            for syn in synonyms:
                pattern = r'\b' + re.escape(syn) + r'\b'
                if re.search(pattern, norm_q):
                    target_entities.append(entity_key)
                    break

        # Remove stop words to build search keywords
        stop_words = {
            "what", "is", "the", "of", "a", "an", "in", "on", "for", "and", "or", "to",
            "show", "me", "find", "get", "tell", "please", "can", "you", "report", "patient",
            "value", "level", "result", "status", "check", "number", "with", "does", "have"
        }

        words = re.findall(r'\b[a-zA-Z0-9\.\-]+\b', norm_q)
        keywords = [w for w in words if w not in stop_words and len(w) > 1]

        return {
            "raw_question": raw_q,
            "normalized_question": norm_q,
            "intent": intent,
            "target_entities": list(set(target_entities)),
            "keywords": keywords
        }
