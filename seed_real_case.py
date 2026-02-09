
import asyncio
import logging
from pipeline import process_case
from src.database import get_db_connection
from psycopg2.extras import RealDictCursor

# Check if using Postgres
import os
from dotenv import load_dotenv
load_dotenv()
DB_NAME = os.getenv("DATABASE_URL", "data/cases.db")

async def verify_insertion(citation):
    print(f"\n--- Verifying {citation} in DB ---")
    conn = get_db_connection(DB_NAME)
    try:
        cur = conn.cursor()
        # Handle table name difference? simpler to just query
        cur.execute("SELECT * FROM court_cases WHERE citation = %s", (citation,))
        row = cur.fetchone()
        if row:
            # RealDictCursor returns dict-like
            print("Row Found:")
            # Convert to dict for printing if it's a RealDictRow
            d = dict(row)
            # Truncate long text
            if 'raw_judgment_text' in d:
                d['raw_judgment_text'] = f"{len(d['raw_judgment_text'])} chars"
            print(d)
        else:
            print("❌ Case not found in DB!")
    except Exception as e:
        print(f"Error verifying: {e}")
    finally:
        conn.close()

async def main():
    # URL for [2026] SGHC 27
    url = "https://www.lawnet.com/openlaw/cases/citation/[2026]+SGHC+27?ref=sg-sc"
    
    print("Starting pipeline...")
    # Force=True to ensure we overwrite any previous bad crawl
    await process_case(url, db_name=DB_NAME, force=True)
    
    await verify_insertion("[2026] SGHC 27")

if __name__ == "__main__":
    asyncio.run(main())
