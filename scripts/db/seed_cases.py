import sys
import os
# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


import logging
from src.database import save_case
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_real_cases():
    cases = [
        {
            "citation": "[2024] SGHC 1",
            "case_name": "Goh Tze Chien v Tan Teow Chee and another",
            "plaintiff_name": "Goh Tze Chien",
            "defendant_name": "Tan Teow Chee",
            "judge_name": "Valerie Thean J",
            "decision_date": "09 Jan 2024",
            "area_of_law": "Companies; Mental Disorders and Treatment",
            "outcome": "Dismissed",
            "plaintiff_counsel": "Mr X for Plaintiff",
            "defendant_counsel": "Mr Y for Defendant",
            "raw_judgment_text": "This case concerns the mental capacity of the testator... [Full text placeholder for [2024] SGHC 1] ... The application is dismissed."
        },
        {
            "citation": "[2023] SGHC 345",
            "case_name": "Public Prosecutor v Aravind",
            "plaintiff_name": "Public Prosecutor",
            "defendant_name": "Aravind",
            "judge_name": "Vincent Hoong J",
            "decision_date": "15 Dec 2023",
            "area_of_law": "Criminal Law",
            "outcome": "Convicted",
            "plaintiff_counsel": "DPP for Prosecution",
            "defendant_counsel": "Counsel for Accused",
            "raw_judgment_text": "The accused was charged with trafficking in controlled drugs... [Full text placeholder for [2023] SGHC 345] ... Found guilty and sentenced."
        },
        {
            "citation": "[2024] SGCA 12",
            "case_name": "Example Corp v Big Tech Ltd",
            "plaintiff_name": "Example Corp",
            "defendant_name": "Big Tech Ltd",
            "judge_name": "Sundaresh Menon CJ",
            "decision_date": "20 Feb 2024",
            "area_of_law": "Contract; Intellectual Property",
            "outcome": "Allowed",
            "plaintiff_counsel": "A for Appellant",
            "defendant_counsel": "B for Respondent",
            "raw_judgment_text": "Appeal regarding the breach of software licensing agreement... [Full text placeholder] ... Appeal allowed."
        }
    ]

    print(f"Seeding {len(cases)} cases into Supabase...")
    for case in cases:
        try:
            # Add some derived fields if needed or just pass strict dict
            save_case(case) # Uses db.save_case which handles connection
            print(f" - Saved: {case['case_name']}")
        except Exception as e:
            print(f" - Failed {case['citation']}: {e}")

if __name__ == "__main__":
    seed_real_cases()
