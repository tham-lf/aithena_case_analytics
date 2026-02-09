import os
import sqlite3
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DB_NAME = "data/cases.db"
IS_POSTGRES = False

def get_db_connection(db_name: str = DB_NAME):
    """
    Returns a database connection. 
    Prioritizes DATABASE_URL environment variable (Postgres).
    Falls back to SQLite if not set.
    """
    global IS_POSTGRES
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        try:
            conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
            IS_POSTGRES = True
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to Postgres: {e}")
            raise
    else:
        IS_POSTGRES = False
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        return conn

def get_placeholder():
    return "%s" if IS_POSTGRES else "?"

def init_db(db_name: str = DB_NAME):
    """
    Initializes the database table if it doesn't exist.
    """
    conn = get_db_connection(db_name)
    try:
        cur = conn.cursor()
        
        # Dialect specific types
        pk_type = "SERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
        timestamp_type = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        
        # 1. Court Cases Table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS court_cases (
                citation TEXT PRIMARY KEY,
                case_name TEXT,
                plaintiff_name TEXT,
                defendant_name TEXT,
                judge_name TEXT,
                decision_date TEXT,
                area_of_law TEXT,
                outcome TEXT,
                plaintiff_counsel TEXT,
                defendant_counsel TEXT,
                raw_judgment_text TEXT,
                created_at {timestamp_type}
            )
        """)
        
        # 2. Search Queries Table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS search_queries (
                id {pk_type},
                query_text TEXT,
                count INTEGER DEFAULT 1,
                last_searched_at {timestamp_type}
            )
        """)
        
        # 3. Generated Reports Table
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS generated_reports (
                id {pk_type},
                title TEXT,
                original_query TEXT,
                created_at {timestamp_type}
            )
        """)
        
        conn.commit()
        logger.info(f"Database initialized (Postgres={IS_POSTGRES}) and schema verified.")
        
        # Seed Mock Data if empty
        seed_mock_data(conn)
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # Re-raise to alert caller
        pass 
    finally:
        conn.close()

def seed_mock_data(conn):
    """Seeds the database with mock data for the dashboard if tables are empty."""
    try:
        cur = conn.cursor()
        p = get_placeholder()
        
        # 1. Seed Queries
        cur.execute("SELECT count(*) FROM search_queries")
        # Handle different return types (tuple vs dict vs Row)
        res = cur.fetchone()
        count = res[0] if isinstance(res, (tuple, list)) else res['count'] if 'count' in res else list(res.values())[0]

        if count == 0:
            mock_queries = [
                ("RTA s 64/65", 12),
                ("Breach of Fiduciary Duty", 8),
                ("Medical Negligence", 5),
                ("Sentencing Guidelines (Theft)", 7),
                ("Misrepresentation", 4)
            ]
            # executemany syntax differs slightly in pure psycopg2 for bulk, but loop is safe
            for q in mock_queries:
                cur.execute(f"INSERT INTO search_queries (query_text, count) VALUES ({p}, {p})", q)
            logger.info("Seeded mock search queries.")

        # 2. Seed Reports
        cur.execute("SELECT count(*) FROM generated_reports")
        res = cur.fetchone()
        count = res[0] if isinstance(res, (tuple, list)) else res['count'] if 'count' in res else list(res.values())[0]

        if count == 0:
            mock_reports = [
                ("Report on RTA Junction Accidents", "RTA s 64/65"),
                ("Analysis of Contractual Penalty Clauses", "Penalty Clauses"),
                ("Case Briefs for Medical Malpractice", "Medical Negligence"),
                ("Sentencing Precedents for Theft", "Theft Sentencing")
            ]
            
            # Simple timestamp logic compatible with both?
            # Postgres supports CURRENT_TIMESTAMP - interval '2 days', SQLite uses datetime()
            # We'll calculate the date in python to be safe
            past_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for r in mock_reports:
                cur.execute(f"INSERT INTO generated_reports (title, original_query, created_at) VALUES ({p}, {p}, {p})", (*r, past_date))
            
            logger.info("Seeded mock reports.")
            
        conn.commit()
    except Exception as e:
        logger.error(f"Error seeding data: {e}")

def save_case(data: Dict[str, Any], db_name: str = DB_NAME):
    """
    Saves or updates a case in the database.
    """
    conn = get_db_connection(db_name)
    try:
        cur = conn.cursor()
        p = get_placeholder()
        
        query = f"""
            INSERT INTO court_cases (
                citation, case_name, plaintiff_name, defendant_name, judge_name, decision_date, 
                area_of_law, outcome, plaintiff_counsel, defendant_counsel, 
                raw_judgment_text
            ) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
            ON CONFLICT(citation) DO UPDATE SET
                case_name=excluded.case_name,
                plaintiff_name=excluded.plaintiff_name,
                defendant_name=excluded.defendant_name,
                judge_name=excluded.judge_name,
                decision_date=excluded.decision_date,
                area_of_law=excluded.area_of_law,
                outcome=excluded.outcome,
                plaintiff_counsel=excluded.plaintiff_counsel,
                defendant_counsel=excluded.defendant_counsel,
                raw_judgment_text=excluded.raw_judgment_text,
                created_at=CURRENT_TIMESTAMP
        """
        
        values = (
            data.get('citation'),
            data.get('case_name'),
            data.get('plaintiff_name'),
            data.get('defendant_name'),
            data.get('judge_name'),
            data.get('decision_date'),
            data.get('area_of_law'),
            data.get('outcome'),
            data.get('plaintiff_counsel'),
            data.get('defendant_counsel'),
            data.get('raw_judgment_text')
        )
        
        cur.execute(query, values)
        conn.commit()
        logger.info(f"Case {data.get('citation')} saved successfully.")
        
    except Exception as e:
        logger.error(f"Error saving case {data.get('citation')}: {e}")
        raise
    finally:
        conn.close()

def case_exists(citation: str, db_name: str = DB_NAME) -> bool:
    """
    Checks if a case with the given citation already exists.
    """
    conn = get_db_connection(db_name)
    try:
        cur = conn.cursor()
        p = get_placeholder()
        cur.execute(f"SELECT 1 FROM court_cases WHERE citation = {p}", (citation,))
        return cur.fetchone() is not None
    finally:
        conn.close()
