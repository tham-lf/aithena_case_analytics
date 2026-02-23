import sys
import os
# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


import logging
import os
from src.database import get_db_connection
from dotenv import load_dotenv

load_dotenv()
DB_NAME = os.getenv("DATABASE_URL", "data/cases.db")
logging.basicConfig(level=logging.INFO)

def clean_mock_data():
    print("Cleaning up Mock Data...")
    conn = get_db_connection(DB_NAME)
    try:
        cur = conn.cursor()
        
        # Citations to remove
        mock_citations = ['[2024] SGHC 1', '[2024] SGHC 2']
        
        for cit in mock_citations:
            cur.execute(f"DELETE FROM court_cases WHERE citation = '{cit}'")
            
        conn.commit()
        print("Deleted mock cases.")
        
        # Verify what remains
        cur.execute("SELECT citation, case_name FROM court_cases")
        rows = cur.fetchall()
        print("\n--- Current DB Content ---")
        for r in rows:
            print(dict(r))
            
    except Exception as e:
        print(f"Error cleaning DB: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clean_mock_data()
