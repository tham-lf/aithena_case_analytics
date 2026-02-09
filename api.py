
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import sqlite3
import pandas as pd
from contextlib import asynccontextmanager

from pipeline import process_case
import src.database as db

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
    # Omit raw text for list view to keep it light

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB is ready
    db.init_db()
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
    Retrieve a list of processed cases.
    """
    conn = db.get_db_connection()
    try:
        cur = conn.cursor() if db.IS_POSTGRES else conn
        p = db.get_placeholder()
        
        # Select specific columns to match Case model
        query = f"""
            SELECT citation, case_name, decision_date, area_of_law, outcome 
            FROM court_cases 
            ORDER BY decision_date DESC 
            LIMIT {p} OFFSET {p}
        """
        cur.execute(query, (limit, offset))
        rows = cur.fetchall()
        
        # Convert to dict if not already
        results = []
        for row in rows:
            if isinstance(row, (dict, sqlite3.Row)):
                results.append(dict(row))
            else:
                # Basic tuple fallback if ReadDictCursor logic fails (unlikely)
                results.append(row)
        
        return results
    finally:
        conn.close()

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
    tasks = [process_case(url, db_name="data/cases.db", force=force) for url in urls]
    await asyncio.gather(*tasks)
    logger.info("Background scrape completed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
