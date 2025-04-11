from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "chorusAvery.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable name-based access to columns
    return conn
