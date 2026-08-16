import sqlite3
import os
import pandas as pd
from typing import Dict, Any, Optional

DB_FILE = "business_data.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS daily_metrics (
    date TEXT PRIMARY KEY,
    traffic INTEGER NOT NULL,
    orders INTEGER NOT NULL,
    conversion_rate REAL NOT NULL,
    revenue REAL NOT NULL,
    marketing_spend REAL NOT NULL,
    operating_cost REAL NOT NULL,
    refunds INTEGER NOT NULL,
    new_customers INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_FILE) -> None:
    """Initializes SQLite database and creates daily_metrics table."""
    with get_connection(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()


def save_df_to_db(df: pd.DataFrame, db_path: str = DB_FILE, replace: bool = False) -> None:
    """Saves a pandas DataFrame into SQLite daily_metrics table."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        if replace:
            conn.execute("DELETE FROM daily_metrics")
        
        for _, row in df.iterrows():
            conn.execute(
                """
                INSERT OR REPLACE INTO daily_metrics 
                (date, traffic, orders, conversion_rate, revenue, marketing_spend, operating_cost, refunds, new_customers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(row['date']),
                    int(row['traffic']),
                    int(row['orders']),
                    float(row['conversion_rate']),
                    float(row['revenue']),
                    float(row['marketing_spend']),
                    float(row['operating_cost']),
                    int(row['refunds']),
                    int(row['new_customers'])
                )
            )
        conn.commit()


def load_df_from_db(db_path: str = DB_FILE) -> pd.DataFrame:
    """Loads all records from SQLite daily_metrics table into a pandas DataFrame."""
    if not os.path.exists(db_path):
        init_db(db_path)
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daily_metrics")
        count = cursor.fetchone()[0]
        
        # If DB is empty but business_data.csv exists, populate DB automatically
        if count == 0 and os.path.exists("business_data.csv"):
            df_csv = pd.read_csv("business_data.csv")
            save_df_to_db(df_csv, db_path=db_path)

        df = pd.read_sql_query("SELECT date, traffic, orders, conversion_rate, revenue, marketing_spend, operating_cost, refunds, new_customers FROM daily_metrics ORDER BY date ASC", conn)
    return df



def record_exists_in_db(date_str: str, db_path: str = DB_FILE) -> bool:
    """Checks if a record for `date_str` already exists in SQLite."""
    if not os.path.exists(db_path):
        return False
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM daily_metrics WHERE date = ?", (str(date_str),))
        return cursor.fetchone() is not None


def insert_record_to_db(record: Dict[str, Any], db_path: str = DB_FILE) -> None:
    """Inserts a single daily record into SQLite database."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO daily_metrics 
            (date, traffic, orders, conversion_rate, revenue, marketing_spend, operating_cost, refunds, new_customers)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(record['date']),
                int(record['traffic']),
                int(record['orders']),
                float(record['conversion_rate']),
                float(record['revenue']),
                float(record['marketing_spend']),
                float(record['operating_cost']),
                int(record['refunds']),
                int(record['new_customers'])
            )
        )
        conn.commit()
