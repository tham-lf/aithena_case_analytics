import logging
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

def extract_legal_metadata(text: str) -> Dict[str, Any]:
    """
    Extracts metadata using Rule-Based Regex (No LLM required).
    """
    data = {}
    
    # 1. Parties (Plaintiff / Defendant) - Attempt to look for header block
    # Pattern: "Between ... [Name] ... Plaintiff ... And ... [Name] ... Defendant"
    # This is hard to do perfectly on raw text, but we can try.
    # Fallback: We rely on the case_name from scraper.py (Entity v Entity).
    
    # 2. Extract Counsel (The "arguing" lawyers)
    # Pattern: Look for "Counsel" header
    # Example text: "Counsel\nJohn Doe (Firm A) for the plaintiff; Jane Doe (Firm B) for the defendant."
    
    counsel_section = re.search(r"Counsel\s*(.*?)(?=\s*(?:Judgment|Introduction|Background|Reasons))", text, re.IGNORECASE | re.DOTALL)
    
    if counsel_section:
        counsel_text = counsel_section.group(1).strip()
        data['plaintiff_counsel'] = _extract_party_counsel(counsel_text, r"for the (?:plaintiff|appellant|claimant)")
        data['defendant_counsel'] = _extract_party_counsel(counsel_text, r"for the (?:defendant|respondent)")
    else:
        # Fallback: Try straight regex on the whole text (less reliable)
        data['plaintiff_counsel'] = _extract_party_counsel(text[:5000], r"for the (?:plaintiff|appellant|claimant)")
        data['defendant_counsel'] = _extract_party_counsel(text[:5000], r"for the (?:defendant|respondent)")

    # 3. Area of Law (Catchwords)
    # Pattern: "Catchwords\n[Topic] - [Subtopic]"
    catchwords = re.search(r"Catchwords\s*[:\n]\s*(.*?)(?=\s*(?:Case|Citation|Decision|Headnote))", text, re.IGNORECASE | re.DOTALL)
    if catchwords:
        # Take the first line or first few words
        words = catchwords.group(1).strip().split('\n')[0]
        data['area_of_law'] = words[:100] # Truncate
    else:
        data['area_of_law'] = "Unclassified"

    # 4. Outcome
    # Look for "Outcome" or "Disposition" or check last paragraph.
    # Simple keyword search for now.
    outcome_lower = text[-2000:].lower() # Last 2000 chars
    if "dismissed" in outcome_lower:
        data['outcome'] = "Dismissed"
    elif "allowed" in outcome_lower or "granted" in outcome_lower:
        data['outcome'] = "Allowed/Granted"
    else:
        data['outcome'] = "Other"

    return data

def _extract_party_counsel(text: str, role_pattern: str) -> str:
    """
    Helper to find counsel name relative to their role.
    Example: "John Doe (Firm) for the plaintiff"
    """
    # Regex: Capture text BEFORE the role pattern. 
    # e.g. "(.*?) (?=for the plaintiff)"
    # This is tricky because multiple counsel might be listed semicolon separated.
    
    # Strategy: Find the role, look backwards until a semicolon or newline.
    try:
        # Find all occurrences of the role
        matches = list(re.finditer(role_pattern, text, re.IGNORECASE))
        if not matches:
            return None
            
        counsels = []
        for m in matches:
            end_pos = m.start()
            # Look backwards for delimiter (; or \n or Start)
            start_pos = 0
            # We look at the preceding chunk
            preceding_chunk = text[:end_pos]
            # Find last split char
            last_split = max(preceding_chunk.rfind(';'), preceding_chunk.rfind('\n'), preceding_chunk.rfind('.'))
            
            if last_split != -1:
                start_pos = last_split + 1
            
            name = preceding_chunk[start_pos:].strip()
            # Clean up trailing punctuation
            name = name.rstrip("(),")
            counsels.append(name)
            
        return "; ".join(counsels)
        
    except Exception:
        return None

