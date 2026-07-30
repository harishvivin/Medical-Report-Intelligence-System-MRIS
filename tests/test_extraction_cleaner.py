"""
Unit Test Suite for Medical Report Extraction Cleaner & Value Sanitizer.
Tests extraction accuracy and post-processing for:
- Sex / Gender (M/F, Male/Female)
- Marital Status (Married/Single/Divorced)
- Smoking (Yes/No, Smoker/Non-Smoker)
- Alcohol (Yes/No, Social/Never)
- Fit / Unfit
- Patient Name (stripping prefixes)
- Age (stripping prefixes)
- Lab values (Creatinine, HbA1c, Hemoglobin, Blood Pressure)
- Hospital Name
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from experimental_gemini_pipeline.gemini_client import clean_extracted_value


class TestExtractionCleaner(unittest.TestCase):

    def test_01_sex_gender_single_option_extraction(self):
        """Verify candidate lists like M/F or Male/Female return ONLY the single selected value."""
        self.assertEqual(clean_extracted_value("M/F", "What is the patient's sex?"), "M")
        self.assertEqual(clean_extracted_value("Male/Female", "What is the patient's gender?"), "Male")
        self.assertEqual(clean_extracted_value("[X] M  [ ] F", "Sex"), "M")
        self.assertEqual(clean_extracted_value("[ ] M  [X] F", "Sex"), "F")
        self.assertEqual(clean_extracted_value("☑ Female  ☐ Male", "Gender"), "Female")
        self.assertEqual(clean_extracted_value("Sex: M", "Sex"), "M")
        self.assertEqual(clean_extracted_value("Gender: Female", "Gender"), "Female")
        self.assertEqual(clean_extracted_value("M (Selected)", "Patient sex"), "M")

    def test_02_marital_status_single_option_extraction(self):
        """Verify marital status multi-options return only the selected choice."""
        self.assertEqual(clean_extracted_value("Married/Single", "What is the marital status?"), "Married")
        self.assertEqual(clean_extracted_value("[X] Married  [ ] Single", "Marital status"), "Married")
        self.assertEqual(clean_extracted_value("☑ Single  ☐ Married", "Marital status"), "Single")
        self.assertEqual(clean_extracted_value("Marital Status: Divorced", "Marital status"), "Divorced")

    def test_03_smoking_status_single_option_extraction(self):
        """Verify smoking status Yes/No options return only single selected value."""
        self.assertEqual(clean_extracted_value("Yes/No", "Does the patient smoke?"), "Yes")
        self.assertEqual(clean_extracted_value("[ ] Yes  [X] No", "Smoking"), "No")
        self.assertEqual(clean_extracted_value("☑ Smoker  ☐ Non-Smoker", "Smoking status"), "Smoker")
        self.assertEqual(clean_extracted_value("Smoking: No", "Smoking"), "No")

    def test_04_alcohol_status_single_option_extraction(self):
        """Verify alcohol status Yes/No options return only single selected value."""
        self.assertEqual(clean_extracted_value("Yes/No", "Does the patient consume alcohol?"), "Yes")
        self.assertEqual(clean_extracted_value("[X] No  [ ] Yes", "Alcohol consumption"), "No")
        self.assertEqual(clean_extracted_value("Alcohol: Yes", "Alcohol"), "Yes")

    def test_05_fit_unfit_single_option_extraction(self):
        """Verify Fit/Unfit options return only single selected value."""
        self.assertEqual(clean_extracted_value("Fit/Unfit", "Is the candidate fit or unfit?"), "Fit")
        self.assertEqual(clean_extracted_value("[X] Fit  [ ] Unfit", "Fitness status"), "Fit")
        self.assertEqual(clean_extracted_value("☑ Unfit  ☐ Fit", "Fitness status"), "Unfit")
        self.assertEqual(clean_extracted_value("Status: Fit", "Fitness"), "Fit")

    def test_06_patient_name_prefix_stripping(self):
        """Verify field labels are stripped from patient name."""
        self.assertEqual(clean_extracted_value("Patient Name: Manjit Singh", "Patient Name"), "Manjit Singh")
        self.assertEqual(clean_extracted_value("Name: John Doe", "Name"), "John Doe")
        self.assertEqual(clean_extracted_value('"Manjit Singh"', "Patient Name"), "Manjit Singh")

    def test_07_age_prefix_stripping(self):
        """Verify age field returns only the value."""
        self.assertEqual(clean_extracted_value("Age: 57Y", "Age"), "57Y")
        self.assertEqual(clean_extracted_value("Patient Age: 57", "Age"), "57")
        self.assertEqual(clean_extracted_value("57Y", "Age"), "57Y")

    def test_08_lab_values_prefix_stripping(self):
        """Verify numeric results with units are preserved without labels."""
        self.assertEqual(clean_extracted_value("Creatinine: 1.2 mg/dL", "Creatinine"), "1.2 mg/dL")
        self.assertEqual(clean_extracted_value("HbA1c: 5.8%", "HbA1c"), "5.8%")
        self.assertEqual(clean_extracted_value("Hemoglobin: 14.8 g/dL", "Hemoglobin"), "14.8 g/dL")
        self.assertEqual(clean_extracted_value("Blood Pressure: 120/80 mmHg", "Blood Pressure"), "120/80 mmHg")

    def test_09_hospital_name_prefix_stripping(self):
        """Verify hospital name returns only the hospital name."""
        self.assertEqual(clean_extracted_value("Hospital Name: City Hospital", "Hospital Name"), "City Hospital")
        self.assertEqual(clean_extracted_value("Hospital: Apollo Clinic", "Hospital"), "Apollo Clinic")


if __name__ == "__main__":
    unittest.main()
