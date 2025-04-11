from fastapi import FastAPI, Request
import redis
import json
import os
from qdrant_client import QdrantClient
from shared.mapping import init_db, get_collection_name, delete_mapping, save_mapping  # Importer la fonction pour sauvegarder le mapping
from notion_client import Client  # Importer le client Notion

app = FastAPI()
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
qdrant = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))

# Initialiser le client Notion
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
notion = Client(auth=NOTION_API_KEY)

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
        parent = body.get("data", {}).get("parent", {})

        # Déterminer l'ID de la base en fonction du type d'événement
        if event_type == "database.created":
            db_id = entity.get("id")  # L'ID de la base est dans entity.id
        elif event_type == "page.created":
            db_id = parent.get("id")  # L'ID de la base est dans parent.id
        elif event_type == "database.deleted":
            db_id = entity.get("id")  # L'ID de la base supprimée est dans entity.id
        else:
            db_id = None

        if not db_id:
            print(f"⚠️ Impossible de déterminer l'ID de la base pour l'événement : {event_type}")
            return {"status": "ignored"}

        print(f"🎯 Base ciblée via webhook : {db_id} [{event_type}]")

        # 🔄 Ajout d'une nouvelle base
        if event_type == "database.created":
            # Récupérer les détails de la base via l'API Notion
            try:
                db_details = notion.databases.retrieve(db_id)
                title = db_details["title"][0]["plain_text"] if db_details["title"] else "sans_nom"
            except Exception as e:
                print(f"❌ Erreur lors de la récupération du titre de la base : {e}")
                title = "sans_nom"

            collection_name = title.strip().lower().replace(" ", "_")
            save_mapping(db_id, collection_name)
            print(f"✅ Nouvelle base ajoutée au mapping : {db_id} ➜ {collection_name}")
            return {"status": "created"}

        # 🔥 Suppression d’une base
        if event_type == "database.deleted":
            try:
                # Supprimer du mapping
                collection_name = get_collection_name(db_id)
                if collection_name:
                    # Supprimer la collection dans Qdrant
                    if qdrant.collection_exists(collection_name):
                        qdrant.delete_collection(collection_name=collection_name)
                        print(f"🗑️ Collection supprimée dans Qdrant : {collection_name}")
                    else:
                        print(f"⚠️ Collection introuvable dans Qdrant : {collection_name}")

                    # Supprimer du mapping
                    delete_mapping(db_id)
                    print(f"🗑️ Base supprimée du mapping : {db_id}")
                else:
                    print(f"⚠️ Aucun mapping trouvé pour la base : {db_id}")
            except Exception as e:
                print(f"❌ Erreur lors de la suppression de la base : {e}")
            return {"status": "deleted"}

        # ✅ Push dans Redis pour d'autres événements
        redis_client.rpush("notion_events", json.dumps({
            "database_id": db_id,
            "event": body
        }))

        print("📬 Événement ajouté à Redis (notion_events)")
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return {"status": "error", "details": str(e)}
