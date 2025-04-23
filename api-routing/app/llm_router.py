import requests

OLLAMA_HOST = "http://ollama:11434"
QDRANT_HOST = "http://qdrant:6333"
MODEL_NAME = "mistral:instruct"

def get_qdrant_collections():
    url = f"{QDRANT_HOST}/collections"
    try:
        response = requests.get(url)
        response.raise_for_status()
        collections = response.json().get("result", {}).get("collections", [])
        return [c["name"] for c in collections]
    except Exception as e:
        print(f"Erreur lors de la récupération des collections : {e}")
        return []

def get_collection_from_question(question: str, collections: list[str]) -> str:
    domain_list = ", ".join(collections)
    prompt = f"""
Tu es un système de routage d'information.

Ta tâche est de déterminer, à partir d'une question utilisateur, à quelle ou quelles collections de données (appelées *collections*) cette question fait référence.

Voici la liste des collections disponibles :  
{domain_list}

Analyse bien le contenu de la question.  
Il est possible qu'elle corresponde à plusieurs collections à la fois.

Réponds uniquement avec le ou les noms exacts des collections pertinentes, séparés par des virgules (ex. : "revenus_(mensuels), dépenses_(mensuelles)").  
Si aucune ne correspond, réponds uniquement par : aucun

Question : {question}  
Collections :
"""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "temperature": 0
            }
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception as e:
        print(f"Erreur lors de l'appel à Ollama : {e}")
        return ""

async def route_question(question: str) -> str:
    collections = get_qdrant_collections()
    matched_collection = get_collection_from_question(question, collections)
    if matched_collection in collections:
        return matched_collection
    return "aucun"
