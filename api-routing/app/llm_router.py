import requests
import json

# 🔗 URL de Qdrant et Ollama dans le réseau Docker
QDRANT_URL = "http://qdrant:6333/collections"
OLLAMA_URL = "http://ollama:11434/api/generate"
OLLAMA_MODEL = "openhermes"  # ou celui que tu utilises dans Ollama

def get_collections():
    """Récupère les collections Qdrant = domaines disponibles"""
    try:
        res = requests.get(QDRANT_URL)
        res.raise_for_status()
        return [c["name"] for c in res.json()["result"]["collections"]]
    except Exception as e:
        print(f"❌ Erreur Qdrant : {e}")
        return []

def route_question(question: str) -> str:
    """Envoie un prompt à Ollama pour classer la question dans un domaine"""
    collections = get_collections()
    if not collections:
        return "aucun_domaine"

    domains_str = ", ".join([f'"{c}"' for c in collections])

    prompt = f"""
Tu es un routeur de questions. Ton rôle est de classer la question de l'utilisateur dans un des domaines suivants : {domains_str}

Réponds uniquement par le nom exact du domaine approprié.

Question : "{question}"

Domaine :
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0,
                "max_tokens": 20
            },
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip().split("\n")[0]
    except Exception as e:
        print(f"❌ Erreur Ollama : {e}")
        return "erreur_ollama"
