import sqlite3
import pandas as pd
import argparse
import src.database as db

def generate_summary(db_name: str):
    conn = db.get_db_connection(db_name)
    
    print(f"--- Case Analytics Report ({db_name}) ---")
    
    # 1. total Cases
    count = conn.execute("SELECT COUNT(*) FROM court_cases").fetchone()[0]
    print(f"Total Cases: {count}")
    
    if count == 0:
        print("No data available.")
        return

    # 2. Cases by Outcome
    print("\n[Outcomes]")
    df_outcome = pd.read_sql_query("SELECT outcome, COUNT(*) as count FROM court_cases GROUP BY outcome", conn)
    print(df_outcome.to_string(index=False))

    # 3. Cases by Area of Law
    print("\n[Area of Law]")
    df_area = pd.read_sql_query("SELECT area_of_law, COUNT(*) as count FROM court_cases GROUP BY area_of_law", conn)
    print(df_area.to_string(index=False))
    
    # 4. Recent Cases
    print("\n[Recent Cases]")
    df_recent = pd.read_sql_query("SELECT citation, case_name, decision_date FROM court_cases ORDER BY decision_date DESC LIMIT 5", conn)
    print(df_recent.to_string(index=False))
    
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/cases.db", help="Database file")
    args = parser.parse_args()
    
    generate_summary(args.db)
