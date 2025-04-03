import os
from notion_client import Client
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient, models
from datetime import datetime
from tqdm import tqdm

# 🔐 Auth
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
notion = Client(auth=NOTION_API_KEY)
qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
qdrant = QdrantClient(url=qdrant_url)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# 📚 Obtenir toutes les bases
def get_all_databases():
    return notion.search(filter={"property": "object", "value": "database"})["results"]

# 📄 Récupérer les lignes d'une base
def fetch_database_rows(database_id):
    return notion.databases.query(database_id=database_id)["results"]

# 🧠 Extraire le texte vectorisable
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

# 🔁 Traitement d'une base
def process_database(db):
    db_id = db["id"]
    title = db["title"][0]["plain_text"] if db["title"] else "sans_nom"
    title_clean = title.strip().lower().replace(" ", "_")
    print(f"\n📥 Traitement de la base : {title_clean}")

    rows = fetch_database_rows(db_id)
    if not rows:
        print("⚠️ Aucune ligne à traiter.")
        return

    # 🗑️ Obtenir les IDs existants dans Qdrant
    existing_ids = set()
    scroll = qdrant.scroll(collection_name=title_clean, with_payload=False)
    while True:
        points, next_page = scroll
        existing_ids.update(p.id for p in points)
        if next_page is None:
            break
        scroll = qdrant.scroll(collection_name=title_clean, with_payload=False, offset=next_page)

    point_ids, texts, payloads = zip(*(extract_text_and_payload(r) for r in rows))
    print(f"🧠 Vectorisation de {len(texts)} éléments...")

    embeddings = embedder.encode(list(texts), show_progress_bar=True)

    vectors = [
        models.PointStruct(id=pid, vector=vec.tolist(), payload=payload)
        for pid, vec, payload in zip(point_ids, embeddings, payloads)
    ]

    if not qdrant.collection_exists(title_clean):
        qdrant.create_collection(
            collection_name=title_clean,
            vectors_config=models.VectorParams(size=384, distance="Cosine")
        )
        print(f"🆕 Collection '{title_clean}' créée.")
    else:
        print(f"✏️ Collection '{title_clean}' trouvée. Mise à jour...")

    # 🔄 Supprimer les points qui ne sont plus dans Notion
    current_ids = set(point_ids)
    to_delete = list(existing_ids - current_ids)
    if to_delete:
        qdrant.delete(collection_name=title_clean, points_selector=models.PointIdsList(points=to_delete))
        print(f"🗑️ {len(to_delete)} anciens points supprimés.")

    qdrant.upsert(collection_name=title_clean, points=vectors)
    print(f"✅ Collection '{title_clean}' mise à jour.")

# 🔧 Entrée principale
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
