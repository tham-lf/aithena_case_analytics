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
    Robustly waits for dynamic content to load.
    """
    logger.info(f"Fetching URL: {url}")
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()
            
            await page.goto(url)
            
            # Wait for specific LawNet content indicators
            try:
                # 'lr_judgments' seems to be a main section wrapper based on debug
                # Or wait for "Decision Date" label if class names change
                await page.wait_for_selector(".lr_judgments", timeout=15000)
            except Exception:
                logger.warning("Timeout waiting for .lr_judgments. Content might be partial.")

            # Extra safety wait for text rendering
            await page.wait_for_timeout(2000)
            
            content = await page.content()
            await browser.close()
            return content
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise

def extract_case_metadata(html_content: str) -> dict:
    """
    Extracts metadata from LawNet HTML using reverse-engineered class names.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    data = {}
    
    # helper to find value by label
    def get_meta_value(label_pattern):
        # Find the label cell
        label_div = soup.find("div", class_="lr_detail_col_left", string=re.compile(label_pattern, re.IGNORECASE))
        if label_div:
            # Find sibling value cell
            value_div = label_div.find_next_sibling("div", class_="lr_detail-col-right")
            if value_div:
                return value_div.get_text(" ", strip=True)
        return None

    # 1. Case Title & Citation
    # Robust fallback: Regex for data-page-title since BS4 might miss it in some parsers
    # Use DOTALL to catch multi-line attributes
    title_match = re.search(r'data-page-title=["\']([^"\']+)["\']', html_content, re.DOTALL | re.IGNORECASE)
    if title_match:
        data['case_name'] = title_match.group(1).strip()
    else:
        # Fallback to H1 or standard classes
        # Try finding the citation header which often contains the name
        title_tag = soup.find('h1') or soup.find(class_='caseTitle') or soup.find(class_='title')
        data['case_name'] = title_tag.get_text(strip=True) if title_tag else "Unknown Case"

    # Infer Parties
    if data.get('case_name') and " v " in data['case_name']:
        parts = data['case_name'].split(" v ", 1)
        data['plaintiff_name'] = parts[0].strip()
        data['defendant_name'] = parts[1].strip()
    else:
        data['plaintiff_name'] = None
        data['defendant_name'] = None

    # 2. Citation
    text = soup.get_text(" ", strip=True)
    citation_match = re.search(r'\[\d{4}\]\s+[A-Z]+\s+\d+', text)
    data['citation'] = citation_match.group(0) if citation_match else "Unknown Citation"
    
    # 3. Decision Date
    data['decision_date'] = get_meta_value("Decision Date")

    # 4. Coram (Judge)
    data['judge_name'] = get_meta_value("Coram")

    # 5. Counsel
    counsel_text = get_meta_value("Counsel Name")
    if counsel_text:
        data['plaintiff_counsel'] = _extract_party_counsel_html(counsel_text, r"plaintiff|appellant|claimant|applicant")
        data['defendant_counsel'] = _extract_party_counsel_html(counsel_text, r"defendant|respondent")
    else:
        data['plaintiff_counsel'] = None
        data['defendant_counsel'] = None

    # 6. Area of Law
    # "Legal Topics" is in div.lr_heading_text. The content should be in a sibling or cousin container.
    # We search for the specific header div.
    legal_topics_header = soup.find("div", class_="lr_heading_text", string=re.compile("Legal Topics", re.IGNORECASE))
    
    if legal_topics_header:
        # Debug structure suggests:
        # <div class="lr_heading_text">Legal Topics</div>
        # <div class="lr_sec_content">...</div> (sibling?)
        # Let's traverse to the next "lr_sec_content"
        container = legal_topics_header.find_next(class_="lr_sec_content")
        if container:
            cw_spans = container.find_all(class_="lr_cw")
            if cw_spans:
                topics = [s.get_text(strip=True) for s in cw_spans]
                seen = set()
                deduped = [x for x in topics if not (x in seen or seen.add(x))]
                data['area_of_law'] = "; ".join(deduped[:10])
            else:
                data['area_of_law'] = container.get_text(" ", strip=True)[:200]
        else:
             # Try parent's sibling
             parent = legal_topics_header.find_parent()
             if parent:
                 sibling = parent.find_next_sibling()
                 if sibling:
                     data['area_of_law'] = sibling.get_text(" ", strip=True)[:200]
                 else:
                     data['area_of_law'] = "Unclassified"
             else:
                 data['area_of_law'] = "Unclassified"
    else:
        # Fallback to Catchwords
        catchwords = soup.find(string=re.compile("Catchwords", re.IGNORECASE))
        if catchwords:
            # Often a list following it
            cw_text = catchwords.find_next().get_text(" ", strip=True) if catchwords.find_next() else ""
            data['area_of_law'] = cw_text.split('-')[0].strip()[:100]
        else:
            data['area_of_law'] = "Unclassified"

    # 7. Outcome
    data['outcome'] = None 

    return data

def _extract_party_counsel_html(text: str, role_regex: str) -> str:
    """
    Simple helper to extract name before a role pattern.
    """
    try:
        # The snippet showed spans with class 'bullet-separator'. 
        # If the input text already merged them, we might see "Name (Firm) for the plaintiff Name (Firm) for..."
        # We can try splitting by known role keywords if they are present.
        
        matches = []
        # Regex to find "X for the Y" pattern
        # This is tricky without the structured span splitting.
        # But let's try a best effort on the text block.
        
        # Split by typical separators if present in text dump
        parts = re.split(r'(?<=\))\s+(?=[A-Z])', text) # Split after closing bracket if followed by Capital (Name)
        if len(parts) == 1:
            parts = text.split(";")
            
        for p in parts:
            if re.search(role_regex, p, re.IGNORECASE):
                # Clean up " for the Plaintiff" suffix
                clean = re.sub(r"\s+(appearing|for)\s+(the)?\s*(" + role_regex + r").*", "", p, flags=re.IGNORECASE).strip()
                matches.append(clean)
                
        return "; ".join(matches) if matches else None
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
