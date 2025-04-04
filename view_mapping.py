import sqlite3

conn = sqlite3.connect("./shared/mapping.db")
cur = conn.cursor()

print("📄 Contenu de la table notion_mappings :\n")
cur.execute("SELECT * FROM notion_mappings")
rows = cur.fetchall()

for row in rows:
    print(f"- database_id : {row[0]}")
    print(f"  collection  : {row[1]}\n")

conn.close()
