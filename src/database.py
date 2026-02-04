import sqlite3
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

DB_NAME = "data/cases.db"

def get_db_connection(db_name: str = DB_NAME) -> sqlite3.Connection:
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_name: str = DB_NAME):
    """
    Initializes the database table if it doesn't exist.
    """
    conn = get_db_connection(db_name)
    try:
        conn.execute("""
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # New Tables for Dashboard
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT,
                count INTEGER DEFAULT 1,
                last_searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS generated_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                original_query TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        logger.info(f"Database {db_name} initialized and schema verified.")
        
        # Seed Mock Data if empty
        seed_mock_data(conn)
        
    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        conn.close()

def seed_mock_data(conn: sqlite3.Connection):
    """Seeds the database with mock data for the dashboard if tables are empty."""
    try:
        # 1. Seed Queries
        cursor = conn.execute("SELECT count(*) FROM search_queries")
        if cursor.fetchone()[0] == 0:
            mock_queries = [
                ("RTA s 64/65", 12),
                ("Breach of Fiduciary Duty", 8),
                ("Medical Negligence", 5),
                ("Sentencing Guidelines (Theft)", 7),
                ("Misrepresentation", 4)
            ]
            conn.executemany("INSERT INTO search_queries (query_text, count) VALUES (?, ?)", mock_queries)
            logger.info("Seeded mock search queries.")

        # 2. Seed Reports
        cursor = conn.execute("SELECT count(*) FROM generated_reports")
        if cursor.fetchone()[0] == 0:
            mock_reports = [
                ("Report on RTA Junction Accidents", "RTA s 64/65"),
                ("Analysis of Contractual Penalty Clauses", "Penalty Clauses"),
                ("Case Briefs for Medical Malpractice", "Medical Negligence"),
                ("Sentencing Precedents for Theft", "Theft Sentencing")
            ]
            conn.executemany("INSERT INTO generated_reports (title, original_query, created_at) VALUES (?, ?, datetime('now', '-2 days'))", mock_reports)
            logger.info("Seeded mock reports.")
            
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error seeding data: {e}")

def save_case(data: Dict[str, Any], db_name: str = DB_NAME):
    """
    Saves or updates a case in the database.
    """
    conn = get_db_connection(db_name)
    try:
        query = """
            INSERT INTO court_cases (
                citation, case_name, plaintiff_name, defendant_name, judge_name, decision_date, 
                area_of_law, outcome, plaintiff_counsel, defendant_counsel, 
                raw_judgment_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        
        conn.execute(query, values)
        conn.commit()
        logger.info(f"Case {data.get('citation')} saved successfully.")
        
    except sqlite3.Error as e:
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
        cursor = conn.execute("SELECT 1 FROM court_cases WHERE citation = ?", (citation,))
        return cursor.fetchone() is not None
    finally:
        conn.close()
