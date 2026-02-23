
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import sqlite3
import pandas as pd
from contextlib import asynccontextmanager

from pipeline import process_case
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic Models for Request/Response
class ScrapeRequest(BaseModel):
    urls: List[str]
    force: bool = False

class Case(BaseModel):
    citation: str
    case_name: Optional[str]
    decision_date: Optional[str]
    area_of_law: Optional[str]
    outcome: Optional[str]
    plaintiff_counsel: Optional[str] = None
    defendant_counsel: Optional[str] = None
    judge_name: Optional[str] = None
    # Omit raw text for list view to keep it light

class EntityStats(BaseModel):
    name: str
    case_count: int

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure JSONL file exists
    os.makedirs("data", exist_ok=True)
    if not os.path.exists("data/case_data.jsonl"):
        open("data/case_data.jsonl", "a").close()
    yield
    # Shutdown

app = FastAPI(
    title="Case Analytics API",
    description="REST API for accessing Singapore Court Case data and triggering scraping jobs.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Case Analytics API is running"}

@app.get("/cases", response_model=List[Case], tags=["Data"])
def get_cases(limit: int = 20, offset: int = 0):
    """
    Retrieve a list of processed cases from JSONL.
    """
    jsonl_path = "data/case_data.jsonl"
    if not os.path.exists(jsonl_path):
        return []
        
    results = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
                
    # Basic pagination and sorting (newest first)
    results.reverse()
    return results[offset : offset + limit]

def parse_lawyers(counsel_str: str) -> List[str]:
    if not counsel_str:
        return []
    import re
    # Remove firm names in brackets/parentheses
    clean_str = re.sub(r'\(.*?\)', '', counsel_str)
    # Remove roles
    clean_str = re.sub(r'for the .*', '', clean_str, flags=re.IGNORECASE)
    # Split by comma and " and "
    parts = re.split(r',|\band\b', clean_str)
    return [p.strip() for p in parts if p.strip()]

@app.get("/lawyers", response_model=List[EntityStats], tags=["Data"])
def get_lawyers(limit: int = 50, offset: int = 0):
    """
    Retrieve statistics on unique lawyers and the number of cases they handled.
    """
    jsonl_path = "data/case_data.jsonl"
    if not os.path.exists(jsonl_path):
        return []
        
    lawyer_counts = {}
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                case = json.loads(line)
                lawyers = []
                lawyers.extend(parse_lawyers(case.get("plaintiff_counsel", "")))
                lawyers.extend(parse_lawyers(case.get("defendant_counsel", "")))
                
                for lawyer in set(lawyers): # use set to avoid double counting if a lawyer appears twice in same case (unlikely but safe)
                    lawyer_counts[lawyer] = lawyer_counts.get(lawyer, 0) + 1
                    
    # Sort by case count descending
    sorted_lawyers = sorted(lawyer_counts.items(), key=lambda x: x[1], reverse=True)
    
    results = [{"name": k, "case_count": v} for k, v in sorted_lawyers]
    return results[offset : offset + limit]

@app.get("/judges", response_model=List[EntityStats], tags=["Data"])
def get_judges(limit: int = 50, offset: int = 0):
    """
    Retrieve statistics on unique judges and the number of cases they handled.
    """
    jsonl_path = "data/case_data.jsonl"
    if not os.path.exists(jsonl_path):
        return []
        
    judge_counts = {}
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                case = json.loads(line)
                judge = case.get("judge_name")
                if judge and judge.strip():
                    j_name = judge.strip()
                    judge_counts[j_name] = judge_counts.get(j_name, 0) + 1
                    
    # Sort by case count descending
    sorted_judges = sorted(judge_counts.items(), key=lambda x: x[1], reverse=True)
    
    results = [{"name": k, "case_count": v} for k, v in sorted_judges]
    return results[offset : offset + limit]

@app.post("/cases/scrape", status_code=202, tags=["Jobs"])
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Trigger a background scraping job for a list of URLs.
    """
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    # We use BackgroundTasks to run this asynchronously without blocking the response
    background_tasks.add_task(run_pipeline_task, request.urls, request.force)
    
    return {
        "message": f"Scraping job accepted for {len(request.urls)} URLs.",
        "input_urls": request.urls
    }

async def run_pipeline_task(urls: List[str], force: bool):
    """
    Helper to run the async pipeline from a sync/thread context if needed, 
    but since FastAPI is async, we can just await gracefully.
    """
    logger.info(f"Starting background scrape for {len(urls)} URLs")
    tasks = [process_case(url, force=force) for url in urls]
    await asyncio.gather(*tasks)
    logger.info("Background scrape completed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
