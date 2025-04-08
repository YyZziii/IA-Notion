# check_mapping.py
import sqlite3

def main():
    db_path = "/app/shared/mapping.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"📂 Lecture de la DB : {db_path}")
    for row in cursor.execute("SELECT notion_id, collection_name FROM notion_mappings"):
        print(row)

    conn.close()

if __name__ == "__main__":
    main()
