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

async def route_question(question: str) -> list[str]:
    collections = get_qdrant_collections()
    matched_collections = get_collection_from_question(question, collections)
    if matched_collections == "aucun":
        return []
    return [col.strip() for col in matched_collections.split(",") if col.strip() in collections]

def fetch_data_from_collections(collections: list[str]) -> dict:
    data = {}
    for collection in collections:
        url = f"{QDRANT_HOST}/collections/{collection}/points/search"
        try:
            response = requests.post(url, json={"limit": 100})
            response.raise_for_status()
            data[collection] = response.json().get("result", [])
        except Exception as e:
            print(f"Erreur lors de la récupération des données pour {collection} : {e}")
    return data

def generate_multi_collection_prompt(data: dict, question: str) -> str:
    prompt = f"""
Tu es un assistant chargé d'analyser les données ci-dessous, provenant de plusieurs collections.  
Réponds à la question en utilisant toutes les informations disponibles.

"""
    for collection, rows in data.items():
        prompt += f"Collection : {collection}\nDonnées : {rows}\n\n"

    prompt += f"Question : {question}\n\nRéponse :"
    return prompt

async def handle_question(question: str) -> str:
    # Étape 1 : Identifier les collections pertinentes
    matched_collections = await route_question(question)
    if not matched_collections:
        return "Aucune collection pertinente trouvée."

    # Étape 2 : Récupérer les données des collections
    data = fetch_data_from_collections(matched_collections)

    # Étape 3 : Générer un prompt multi-collections
    prompt = generate_multi_collection_prompt(data, question)

    # Étape 4 : Envoyer le prompt au modèle LLM
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
        print(f"Erreur lors de l'appel au modèle LLM : {e}")
        return "Erreur lors de la génération de la réponse."
