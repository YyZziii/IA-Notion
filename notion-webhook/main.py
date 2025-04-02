from fastapi import FastAPI, Request
import redis
import json
import os

app = FastAPI()

# Connexion à Redis via l'URL d'environnement
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url)

@app.post("/webhook/notion")
async def webhook(request: Request):
    body = await request.json()

    # Webhook de vérification de Notion
    if "challenge" in body:
        return {"challenge": body["challenge"]}

    print("📥 Webhook reçu :")
    print(json.dumps(body, indent=2, ensure_ascii=False))

    try:
        database_id = body.get("data", {}).get("parent", {}).get("id")
        print(f"🎯 Base ciblée via webhook : {database_id}")

        # Envoi dans Redis
        redis_client.rpush("notion_events", json.dumps({
            "database_id": database_id,
            "event": body
        }))

        print("📬 Événement ajouté à Redis (notion_events)")
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return {"status": "error", "details": str(e)}
