from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from notion_client import Client
import os
import requests

app = FastAPI()

# 🔐 Auth Notion via clé d'API
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
notion = Client(auth=NOTION_API_KEY)

# 🚀 Modèle LLM configuré dynamiquement
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")

# 🗂️ Dictionnaire des bases disponibles (nom ➜ {id, colonnes})
database_map = {}

# ✅ Structure de la requête attendue
class NotionQuery(BaseModel):
    question: str

# 🔧 Chargement des bases de données Notion au démarrage
def load_databases():
    global database_map
    print("🔍 Chargement des bases de données Notion...")

    try:
        response = notion.search(filter={"property": "object", "value": "database"})
        databases = response['results']

        for db in databases:
            title = db['title'][0]['plain_text'] if db['title'] else 'Sans titre'
            db_id = db['id']

            # Extraction des colonnes
            db_info = notion.databases.retrieve(db_id)
            columns = list(db_info['properties'].keys())

            database_map[title] = {"id": db_id, "columns": columns}

        print(f"✅ Bases trouvées : {database_map}")

    except Exception as e:
        print(f"❌ Erreur lors du chargement des bases : {e}")

# 🔧 Fonction pour détecter la base ciblée par la question
def find_database_from_question(question: str):
    for db_name in database_map.keys():
        if db_name.lower() in question.lower():
            print(f"🔎 Base trouvée par le nom ➜ {db_name}")
            return database_map[db_name]

    print("⚠️ Aucune base explicite trouvée dans la question")
    return None

# 🔧 Récupération des données d'une base via son ID
def fetch_database_rows(db_id):
    try:
        notion_data = notion.databases.query(database_id=db_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Notion : {e}")

    rows = []
    for page in notion_data["results"]:
        item = {}
        for prop, val in page["properties"].items():
            if val["type"] == "title":
                item[prop] = val["title"][0]["plain_text"] if val["title"] else ""
            elif val["type"] == "rich_text":
                item[prop] = val["rich_text"][0]["plain_text"] if val["rich_text"] else ""
            elif val["type"] == "number":
                item[prop] = val["number"]
            elif val["type"] == "select":
                item[prop] = val["select"]["name"] if val["select"] else ""
            elif val["type"] == "date":
                item[prop] = val["date"]["start"] if val["date"] else ""
            else:
                item[prop] = str(val)
        rows.append(item)
    return rows

# ✅ Chargement initial des bases
load_databases()

# ✅ Endpoint principal générique
@app.post("/ask-llm")
def ask_llm(query: NotionQuery):
    print(f"👉 Question reçue : {query.question}")

    # Recherche d'une base explicite dans la question
    db_info = find_database_from_question(query.question)

    # Mode Mono-Base (simple) ➜ base spécifique trouvée
    if db_info:
        db_id = db_info["id"]
        print(f"📂 Base ciblée ➜ {db_info}")
        rows = fetch_database_rows(db_id)

        llm_prompt = generate_prompt(
            data=rows,
            question=query.question,
            instruction="Réponds uniquement à la question ci-dessous de façon simple et précise en français, sans explication. Ta réponse doit être une seule phrase."
        )

    # Mode Multi-Bases ➜ aucune base claire, on utilise toutes les données
    else:
        print("🔁 Mode Multi-Bases activé")
        all_rows = {}
        for db_name, db_data in database_map.items():
            db_rows = fetch_database_rows(db_data["id"])
            all_rows[db_name] = db_rows

        llm_prompt = generate_prompt_multi_base(
            data=all_rows,
            question=query.question,
            instruction="Réponds uniquement à la question ci-dessous de façon simple et précise en français."
        )

    # Envoi au modèle dynamique via Ollama API
    llm_response = requests.post("http://ollama:11434/api/generate", json={
        "model": MODEL_NAME,
        "prompt": llm_prompt,
        "stream": False
    })

    if llm_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Erreur lors de l'appel au modèle LLM.")

    result = llm_response.json()
    print(f"✅ Réponse {MODEL_NAME} ➜ {result['response']}")

    return {"response": result['response']}

# 🔧 Génération de prompt Mono-Base
def generate_prompt(data, question, instruction):
    return f"""
    Tu es un assistant chargé d'analyser les données ci-dessous et de répondre à une question spécifique.

    Données de la base :
    {data}

    {instruction}

    Question : "{question}"

    Réponse :
    """

# 🔧 Génération de prompt Multi-Bases
def generate_prompt_multi_base(data, question, instruction):
    return f"""
    Tu es un assistant chargé d'analyser les données ci-dessous, provenant de plusieurs bases Notion. Tu dois répondre à la question posée en utilisant toutes les informations disponibles.

    Bases de données :
    {data}

    {instruction}

    Question : "{question}"

    Réponse :
    """