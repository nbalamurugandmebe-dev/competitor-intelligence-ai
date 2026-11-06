import json
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).with_name("competitor_data.db")


def init_db():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS app_data (
                data_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def load_dataframe(data_key):
    init_db()
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT payload FROM app_data WHERE data_key = ?",
            (data_key,),
        ).fetchone()

    if row is None:
        return pd.DataFrame()

    try:
        records = json.loads(row[0])
        return pd.DataFrame(records)
    except (ValueError, TypeError):
        return pd.DataFrame()


def save_dataframe(data_key, dataframe):
    init_db()
    records = dataframe.where(pd.notna(dataframe), None).to_dict(
        orient="records"
    )
    payload = json.dumps(records, ensure_ascii=False, default=str)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            INSERT INTO app_data (data_key, payload, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(data_key) DO UPDATE SET
                payload = excluded.payload,
                updated_at = CURRENT_TIMESTAMP
        """, (data_key, payload))
