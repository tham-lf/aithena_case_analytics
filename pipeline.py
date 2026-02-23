import asyncio
import argparse
import logging
import re
import json
import os
from typing import List

from src.scraper import fetch_case_html, extract_judgment_text, extract_case_metadata
from src.extractor import extract_legal_metadata
import src.database as db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_citation_from_url(url: str) -> str:
    """
    Attempts to extract citation from URL or returns a hash/placeholder.
    LawNet URLs: .../citation/[2026]+SGHC+21?ref...
    """
    try:
        match = re.search(r'citation/(\[.*?\]\+.*?)(\?|$)', url)
        if match:
            # Decode specific chars if needed, e.g. + to space
            return match.group(1).replace('+', ' ').strip()
    except Exception:
        pass
    return url # Fallback to URL as ID if extraction fails

async def process_case(url: str, db_name: str = None, force: bool = False, jsonl_path: str = "data/case_data.jsonl"):
    """
    Orchestrates the processing of a single case.
    """
    citation = extract_citation_from_url(url)
    
    # 1. Idempotency Check
    if not force and db_name and db.case_exists(citation, db_name=db_name):
        logger.info(f"Skipping {citation} - already exists in DB.")
        return

    logger.info(f"Processing case: {citation}")
    
    # 2. Retry Logic for Scraping
    html_content = None
    retries = 3
    for attempt in range(retries):
        try:
            html_content = await fetch_case_html(url)
            break
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{retries} failed for {url}: {e}")
            await asyncio.sleep(2) # Backoff
            
    if not html_content:
        logger.error(f"Failed to fetch content for {url} after {retries} attempts.")
        return

    # 3. HTML Metadata Extraction (Robust Fallback/Primary)
    html_metadata = extract_case_metadata(html_content)
    logger.info(f"HTML Metadata: {html_metadata}")

    # 4. Text Extraction
    raw_text = extract_judgment_text(html_content)
    iflen = len(raw_text)
    logger.info(f"Extracted {iflen} characters of raw text.")

    # 5. LLM Extraction (Regex Fallback in extractor.py)
    # Note: We pass the raw text to the LLM/Regex extractor. 
    llm_metadata = extract_legal_metadata(raw_text)
    
    # 6. Merge and Save
    # We prioritize HTML metadata for 'case_name' and 'citation' as strict parsing is often better.
    # LLM/Regex is better for 'area_of_law', 'outcome', etc.
    final_metadata = {**llm_metadata, **html_metadata}
    
    # Ensure keys that might be None in HTML metadata don't overwrite valid LLM data if any
    for k, v in html_metadata.items():
        if v:
            final_metadata[k] = v
            
    case_data = {
        "citation": citation,
        "raw_judgment_text": raw_text,
        **final_metadata # Unpack fields including counsel
    }
    
    if db_name:
        db.save_case(case_data, db_name=db_name)
        logger.info(f"Successfully saved {citation} to DB")
        
    if jsonl_path:
        with open(jsonl_path, mode='a', encoding='utf-8') as f:
            f.write(json.dumps(case_data, ensure_ascii=False) + '\n')
        logger.info(f"Successfully saved {citation} to JSONL")

async def main():
    parser = argparse.ArgumentParser(description="LawNet Case Processing Pipeline")
    parser.add_argument("urls", nargs='+', help="List of URLs to process")
    parser.add_argument("--force", action="store_true", help="Reprocess even if exists")
    parser.add_argument("--db", default=None, help="Database file path")
    parser.add_argument("--jsonl", default="data/case_data.jsonl", help="Path to output JSONL file")
    parser.add_argument("--no-db", action="store_true", help="Do not save to database (deprecated, default behavior)")
    
    args = parser.parse_args()
    
    db_name = None if args.no_db else args.db
    
    # Init DB
    if db_name:
        db.init_db(db_name)
    
    # Process Cases
    tasks = []
    for url in args.urls:
        tasks.append(process_case(url, db_name=db_name, force=args.force, jsonl_path=args.jsonl))
        
    # Run concurrently
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
