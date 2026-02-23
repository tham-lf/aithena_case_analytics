import sys
import os
# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


import asyncio
import logging
import os
from src.database import get_db_connection
from pipeline import process_case
from dotenv import load_dotenv

load_dotenv()
DB_NAME = os.getenv("DATABASE_URL", "data/cases.db")
logging.basicConfig(level=logging.INFO)

def clean_database():
    print("Cleaning up 'Unknown Case' entries...")
    conn = get_db_connection(DB_NAME)
    try:
        cur = conn.cursor()
        # Check count first
        cur.execute("SELECT count(*) FROM court_cases WHERE case_name = 'Unknown Case'")
        row = cur.fetchone()
        count = row[0] if row else 0
        print(f"Found {count} bad entries.")
        
        if count > 0:
            cur.execute("DELETE FROM court_cases WHERE case_name = 'Unknown Case'")
            conn.commit()
            print("Deleted bad entries.")
            
        # Also check for our specific case just in case key collision prevented update
        cur.execute("DELETE FROM court_cases WHERE citation = '[2026] SGHC 27'")
        conn.commit()
        print("Ensured target case is removed for fresh insert.")
        
    except Exception as e:
        print(f"Error cleaning DB: {e}")
    finally:
        conn.close()

async def main():
    clean_database()
    
    url = "https://www.lawnet.com/openlaw/cases/citation/[2026]+SGHC+27?ref=sg-sc"
    print(f"Re-seeding {url}...")
    
    await process_case(url, db_name=DB_NAME, force=True)
    
    # Verify
    conn = get_db_connection(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT case_name, citation FROM court_cases WHERE citation = '[2026] SGHC 27'")
    row = cur.fetchone()
    print(f"VERIFICATION RESULT: {row}")
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())
