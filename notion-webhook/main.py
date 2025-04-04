from fastapi import FastAPI, Request
import redis
import json
import os
from qdrant_client import QdrantClient
from shared.mapping import init_db, get_collection_name, delete_mapping

app = FastAPI()
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
qdrant = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))

init_db()

@app.post("/webhook/notion")
async def webhook(request: Request):
    body = await request.json()

    if "challenge" in body:
        return {"challenge": body["challenge"]}

    print("📥 Webhook reçu :")
    print(json.dumps(body, indent=2, ensure_ascii=False))

    try:
        event_type = body.get("type")
        entity = body.get("entity", {})
        db_id = entity.get("id")

        print(f"🎯 Base ciblée via webhook : {db_id} [{event_type}]")

        if event_type == "database.deleted":
            collection = get_collection_name(db_id)
            if collection and qdrant.collection_exists(collection):
                qdrant.delete_collection(collection_name=collection)
                delete_mapping(db_id)
                print(f"🗑️ Collection '{collection}' supprimée suite à la suppression de la base.")
            return {"status": "deleted"}

        redis_client.rpush("notion_events", json.dumps({
            "database_id": db_id,
            "event": body
        }))

        print("📬 Événement ajouté à Redis (notion_events)")
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return {"status": "error", "details": str(e)}
