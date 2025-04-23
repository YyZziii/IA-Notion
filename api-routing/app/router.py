from fastapi import APIRouter
from llm_router import route_question
from qdrant_search import search_qdrant
from schemas import QuestionRequest, QuestionResponse
import requests

router = APIRouter()

OLLAMA_HOST = "http://ollama:11434"
FINAL_MODEL = "mistral:instruct"  # Ou "openhermes", selon ce que tu préfères

# === ROUTAGE SEUL ===
@router.post("/route", response_model=QuestionResponse)
async def route_question_endpoint(request: QuestionRequest):
    matched_collections = await route_question(request.question)
    if matched_collections:
        collections_str = ", ".join(matched_collections)
        return QuestionResponse(collection=collections_str)
    return QuestionResponse(collection="aucun")

# === RAG COMPLET ===
@router.post("/query", response_model=QuestionResponse)
async def query_endpoint(request: QuestionRequest):
    # Étape 1 : Routage
    matched_collections = await route_question(request.question)
    print("🧭 Collections détectées :", matched_collections)

    # Uniformise le format
    if isinstance(matched_collections, str):
        matched_collections = [matched_collections]

    # ⚠️ Si le routage renvoie uniquement "aucun", on arrête ici
    if not matched_collections or matched_collections == ["aucun"]:
        return QuestionResponse(collection="aucun", answer="Je n'ai pas trouvé de domaine correspondant.")

    # Étape 2 : Recherche vectorielle sur chaque collection
    all_docs = []
    for collection in matched_collections:
        docs = search_qdrant(request.question, collection)
        all_docs.extend(docs)

    if not all_docs:
        collections_str = ", ".join(matched_collections)
        return QuestionResponse(collection=collections_str, answer="Aucun contenu trouvé dans les collections.")

    # Étape 3 : Construire le contexte
    context_text = "\n".join([str(doc) for doc in all_docs])

    # Étape 4 : Prompt pour le LLM
    prompt = f"""Tu es un assistant personnel.
Réponds à la question suivante en utilisant uniquement les informations ci-dessous :

### CONTEXTE :
{context_text}

### QUESTION :
{request.question}

Réponds de manière claire et concise.
"""

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": FINAL_MODEL,
                "prompt": prompt,
                "stream": False,
                "temperature": 0
            }
        )
        response.raise_for_status()
        generated = response.json()["response"]
        collections_str = ", ".join(matched_collections)
        return QuestionResponse(collection=collections_str, answer=generated.strip())
    except Exception as e:
        collections_str = ", ".join(matched_collections)
        return QuestionResponse(collection=collections_str, answer=f"Erreur lors de la génération : {e}")
