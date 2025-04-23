from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient, models

# Initialisation du modèle d'embedding et du client Qdrant
embedder = SentenceTransformer("intfloat/multilingual-e5-small")
qdrant = QdrantClient(url="http://qdrant:6333")  # adapte si nécessaire

def search_qdrant(question: str, collection: str, top_k: int = 5):
    # Embed de la question utilisateur
    vector = embedder.encode(question).tolist()

    # Recherche vectorielle dans Qdrant
    search_result = qdrant.search(
        collection_name=collection,
        query_vector=vector,
        limit=top_k,
        with_payload=True
    )

    # Extraction des résultats (payloads uniquement)
    return [point.payload for point in search_result]
