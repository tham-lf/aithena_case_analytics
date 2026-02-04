import logging
import asyncio
from playwright.async_api import async_playwright
import trafilatura
from bs4 import BeautifulSoup
import re
import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

logger = logging.getLogger(__name__)

async def fetch_case_html(url: str, headless: bool = True) -> str:
    """
    Fetches the HTML content of a LawNet case URL using Playwright.
    """
    logger.info(f"Fetching URL: {url}")
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()
            
            await page.goto(url)
            
            # Wait for dynamic content
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except Exception as e:
                logger.warning(f"Network idle timeout: {e}. Proceeding.")
            
            # Extra wait for binding
            await page.wait_for_timeout(2000)
            
            content = await page.content()
            await browser.close()
            return content
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise

def extract_case_metadata(html_content: str) -> dict:
    """
    Extracts metadata (Case Name, Citation, Date, Coram) directly from HTML 
    using BeautifulSoup. This serves as a robust fallback/primary source vs LLM.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {}
    
    # 1. Case Title
    title_tag = soup.find('h1') or soup.find(class_='caseTitle') or soup.find(class_='title')
    data['case_name'] = title_tag.get_text(strip=True) if title_tag else None
    
    # Infer Parties from Case Name
    if data['case_name'] and " v " in data['case_name']:
        parts = data['case_name'].split(" v ", 1)
        data['plaintiff_name'] = parts[0].strip()
        data['defendant_name'] = parts[1].strip()
    else:
        data['plaintiff_name'] = None
        data['defendant_name'] = None
    
    # 2. Citation
    text = soup.get_text(" ", strip=True)
    citation_match = re.search(r'\[\d{4}\]\s+[A-Z]+\s+\d+', text)
    data['citation'] = citation_match.group(0) if citation_match else None
    
    # 3. Decision Date
    date_label = soup.find(string=re.compile("Decision Date", re.IGNORECASE))
    if date_label:
        next_elem = date_label.find_next()
        data['decision_date'] = next_elem.get_text(strip=True) if next_elem else date_label.parent.get_text(strip=True)
    else:
        # Fallback: try looking for date-like pattern near start
        pass 
    if not data.get('decision_date'):
        data['decision_date'] = None

    # 4. Coram
    coram_match = re.search(r"Coram\s+(.*?)(?=\s+(?:Counsel|Parties|Judgment|Introduction|\[))", text, re.IGNORECASE | re.DOTALL)
    if coram_match:
        data['judge_name'] = coram_match.group(1).strip()
    else:
        coram_label = soup.find(string=re.compile("Coram|Before", re.IGNORECASE))
        data['judge_name'] = coram_label.find_next().get_text(strip=True) if coram_label else None

    # 5. Counsel Extraction
    counsel_block = soup.find(string=re.compile("Representation|Counsel", re.IGNORECASE))
    
    # Look for the block following "Representation" or "Counsel"
    if counsel_block:
        counsel_text = counsel_block.find_next().get_text(" ", strip=True) if counsel_block.find_next() else counsel_block.parent.get_text(" ", strip=True)
        # Naive split for plaintiff/defendant if possible, or just dump all
        data['plaintiff_counsel'] = _extract_party_counsel_html(counsel_text, r"plaintiff|appellant|claimant")
        data['defendant_counsel'] = _extract_party_counsel_html(counsel_text, r"defendant|respondent")
    else:
        data['plaintiff_counsel'] = None
        data['defendant_counsel'] = None

    # 6. Area of Law
    # Priority: "Legal Topics" section with class 'lr_cw' > "Legal Topics" text block > "Catchwords"
    
    # Method A: Specific Class Extraction (most robust for LawNet)
    # The topics are often in spans with class 'lr_cw' inside a container
    # We try to find the "Legal Topics" header first to ensure we are in the right section
    legal_topics_header = soup.find(string=re.compile("Legal Topics", re.IGNORECASE))
    
    if legal_topics_header:
        # Try to find the container div 'lr_sec_content' nearby
        container = legal_topics_header.find_next(class_="lr_sec_content")
        
        if container:
            # Extract individual topic terms
            cw_spans = container.find_all(class_="lr_cw")
            if cw_spans:
                # Group them? They are linear spans. "Contract", "Breach", "Damages"...
                # We can join them with ' > ' if they are siblings, or just list them.
                # However, visual hierarchy (Contract > Breach) might be lost in linear spans.
                # But a simple join is better than nothing.
                topics = [s.get_text(strip=True) for s in cw_spans]
                # Cleanup duplicates if any
                seen = set()
                deduped = [x for x in topics if not (x in seen or seen.add(x))]
                data['area_of_law'] = "; ".join(deduped[:10]) # Take top 10 keywords
            else:
                # Fallback: just text
                data['area_of_law'] = container.get_text(" ", strip=True)[:200]
        else:
             # Fallback to traversing siblings if class not found
             current_elem = legal_topics_header.find_next()
             topics = []
             for _ in range(5):
                if not current_elem: break
                text = current_elem.get_text(strip=True)
                if "Judgments" in text or "Case Details" in text: break
                if text and len(text) > 2: topics.append(text)
                current_elem = current_elem.find_next()
             
             data['area_of_law'] = "; ".join(topics) if topics else "Unclassified"
    else:
        # Method B: Fallback to Catchwords
        catchwords = soup.find(string=re.compile("Catchwords", re.IGNORECASE))
        if catchwords:
            # Often a list following it
            cw_text = catchwords.find_next().get_text(" ", strip=True) if catchwords.find_next() else ""
            data['area_of_law'] = cw_text.split('-')[0].strip()[:100]
        else:
            data['area_of_law'] = "Unclassified"

    # 7. Outcome (Heuristic from HTML)
    # Check for "Outcome" or "Judgment" header at end? Hard to do in HTML.
    # We'll leave outcome to key word search in full text or LLM.
    # But let's check for "Appeal dismissed" type phrases in the first few paragraphs (Headnote).
    headnote = soup.find(class_='headnote')
    if headnote:
        hn_text = headnote.get_text().lower()
        if "dismissed" in hn_text:
            data['outcome'] = "Dismissed"
        elif "allowed" in hn_text:
            data['outcome'] = "Allowed"
        else:
            data['outcome'] = None
    else:
        data['outcome'] = None

    return data

def _extract_party_counsel_html(text: str, role_regex: str) -> str:
    """
    Simple helper to extract name before a role pattern.
    Defaulting to just returning the whole chunk if complex string parsing is needed,
    but let's try a split.
    """
    # E.g. "Mr X (Firm A) for the Plaintiff; Ms Y (Firm B) for the Defendant"
    # We want X if we pass 'plaintiff'.
    try:
        # Split by semicolon to separate parties
        parts = re.split(r'[;.]', text)
        found_names = []
        for p in parts:
            if re.search(role_regex, p, re.IGNORECASE):
                # Remove the role part like " for the Plaintiff"
                clean_name = re.sub(r"(for|appearing)?\s*(the)?\s*(" + role_regex + r").*", "", p, flags=re.IGNORECASE).strip()
                found_names.append(clean_name)
        return "; ".join(found_names) if found_names else None
    except:
        return None

def extract_judgment_text(html_content: str) -> str:
    """
    Extracts the main judgment text from HTML using Trafilatura.
    """
    text = trafilatura.extract(html_content, include_comments=False, include_tables=False)
    if not text:
        # Fallback if trafilatura fails: return raw text
        soup = BeautifulSoup(html_content, 'html.parser')
        logger.warning("Trafilatura extraction returned empty text. Using BS4 fallback.")
        return soup.get_text("\n", strip=True)
    return text
