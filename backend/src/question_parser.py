import re
from typing import Dict, Any, List, Set

# Medical entity mapping for targeted keyword extraction
MEDICAL_ENTITIES = {
    "hemoglobin": ["hemoglobin", "hgb", "hb"],
    "creatinine": ["creatinine", "serum creatinine"],
    "hba1c": ["hba1c", "glycated hemoglobin", "hb a1c", "a1c"],
    "blood pressure": ["blood pressure", "bp", "systolic", "diastolic"],
    "hiv": ["hiv", "hiv 1", "hiv 2", "human immunodeficiency virus", "serology"],
    "ecg": ["ecg", "ekg", "electrocardiogram", "heart rate", "rhythm"],
    "patient_name": ["patient name", "patient", "name", "client name"],
    "hospital_name": ["hospital", "clinic", "laboratory", "lab", "center", "institute"],
    "age": ["age", "yrs", "years old", "yo"],
    "gender": ["gender", "sex", "male", "female"],
    "diagnosis": ["diagnosis", "impression", "conclusion", "opinion", "finding", "result"],
    "wbc": ["wbc", "white blood cell", "leukocyte"],
    "platelets": ["platelet", "platelet count", "plt"],
    "glucose": ["glucose", "sugar", "fasting sugar", "ppbs", "fbs"],
    "cholesterol": ["cholesterol", "triglycerides", "hdl", "ldl", "lipid"],
    "thyroid": ["tsh", "t3", "t4", "thyroid"],
    "urea": ["urea", "bun", "blood urea"],
    "liver": ["sgot", "sgpt", "ast", "alt", "bilirubin", "alkaline phosphatase"]
}

SUMMARY_TRIGGER_WORDS = {"summary", "summarize", "overview", "report summary", "brief", "key findings"}
COMPARISON_TRIGGER_WORDS = {"compare", "comparison", "difference", "versus", "vs", "higher than", "lower than"}
LOOKUP_TRIGGER_WORDS = {"what is", "where is", "show", "find", "get", "value of", "level of", "check", "tell me"}

class QuestionParser:
    @staticmethod
    def parse(question: str) -> Dict[str, Any]:
        """
        Parses a user question into intent type and extracted keywords.
        Intents: 'summary_request', 'comparison_request', 'lookup_request', 'keyword_search'
        """
        raw_q = question.strip()
        norm_q = raw_q.lower()

        intent = "lookup_request"

        # Check intent
        if any(w in norm_q for w in SUMMARY_TRIGGER_WORDS):
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
