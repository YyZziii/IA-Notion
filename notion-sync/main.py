import os
from notion_client import Client
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient, models
from datetime import datetime
from tqdm import tqdm

# 🔐 Auth
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
notion = Client(auth=NOTION_API_KEY)
qdrant = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
embedder = SentenceTransformer("thenlper/gte-small")

def get_all_databases():
    return notion.search(filter={"property": "object", "value": "database"})["results"]

def fetch_database_rows(database_id):
    return notion.databases.query(database_id=database_id)["results"]

def extract_text_and_payload(row):
    payload = {"notion_id": row["id"]}
    text_parts = []
    for prop, val in row["properties"].items():
        if val["type"] == "title":
            value = val["title"][0]["plain_text"] if val["title"] else ""
        elif val["type"] == "rich_text":
            value = val["rich_text"][0]["plain_text"] if val["rich_text"] else ""
        elif val["type"] == "number":
            value = val["number"]
        elif val["type"] == "date":
            value = val["date"]["start"] if val["date"] else ""
        elif val["type"] == "select":
            value = val["select"]["name"] if val["select"] else ""
        else:
            value = str(val)
        payload[prop] = value
        text_parts.append(str(value))
    return row["id"], ", ".join(text_parts), payload

def process_database(db):
    db_id = db["id"]
    title = db["title"][0]["plain_text"] if db["title"] else "sans_nom"
    title_clean = title.strip().lower().replace(" ", "_")
    print(f"\n📥 Traitement de la base : {title_clean}")

    rows = fetch_database_rows(db_id)
    if not rows:
        print("⚠️ Aucune ligne à traiter.")
        return

    existing_payloads = {}
    if qdrant.collection_exists(title_clean):
        scroll = qdrant.scroll(collection_name=title_clean, with_payload=True)
        while True:
            points, next_page = scroll
            for pt in points:
                existing_payloads[pt.id] = pt.payload
            if next_page is None:
                break
            scroll = qdrant.scroll(collection_name=title_clean, with_payload=True, offset=next_page)
    else:
        qdrant.create_collection(
            collection_name=title_clean,
            vectors_config=models.VectorParams(size=384, distance="Cosine")
        )

    to_upsert = []
    current_ids = set()

    for row in tqdm(rows, desc="🔍 Comparaison des lignes"):
        pid, text, payload = extract_text_and_payload(row)
        current_ids.add(pid)
        if pid not in existing_payloads or existing_payloads[pid] != payload:
            embedding = embedder.encode(text)
            to_upsert.append(models.PointStruct(id=pid, vector=embedding.tolist(), payload=payload))

    to_delete = list(set(existing_payloads.keys()) - current_ids)
    if to_delete:
        qdrant.delete(collection_name=title_clean, points_selector=models.PointIdsList(points=to_delete))
        print(f"🗑️ {len(to_delete)} anciens points supprimés.")

    if to_upsert:
        qdrant.upsert(collection_name=title_clean, points=to_upsert)
        print(f"✅ {len(to_upsert)} points ajoutés ou mis à jour.")
    else:
        print("✅ Aucun changement détecté, pas de vectorisation.")

if __name__ == "__main__":
    mono_base_id = os.getenv("NOTION_DATABASE_ID")
    if mono_base_id:
        print(f"🎯 Mode mono-base activé : {mono_base_id}")
        db = notion.databases.retrieve(mono_base_id)
        process_database(db)
    else:
        print("🔄 Mode multi-bases activé")
        for db in get_all_databases():
            process_database(db)
