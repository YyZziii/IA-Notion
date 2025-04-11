# mapping.py
import sqlite3
import os

DB_PATH = os.getenv("MAPPING_DB", "mapping.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notion_mappings (
            notion_id TEXT PRIMARY KEY,
            collection_name TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_mapping(notion_id: str, collection_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO notion_mappings (notion_id, collection_name)
        VALUES (?, ?)
    """, (notion_id, collection_name))
    conn.commit()
    conn.close()

def get_collection_name(notion_id: str) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT collection_name FROM notion_mappings WHERE notion_id = ?", (notion_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def delete_mapping(notion_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notion_mappings WHERE notion_id = ?", (notion_id,))
    conn.commit()
    conn.close()
