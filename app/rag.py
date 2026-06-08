import json
import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL

_client = None
_collection = None
_model = None
_destinations = []


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.Client(Settings(anonymized_telemetry=False))
        _collection = _client.get_or_create_collection(
            name="pana_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def get_destinations():
    return _destinations


def get_destination_by_slug(slug: str) -> dict | None:
    for dest in _destinations:
        if dest.get("slug") == slug:
            return dest
    return None


def load_knowledge_base(filepath: str = "knowledge_base/destinations.json"):
    global _destinations
    collection = get_collection()
    model = get_embedding_model()

    with open(filepath, "r", encoding="utf-8") as f:
        _destinations = json.load(f)

    if collection.count() > 0:
        return

    documents = []
    metadatas = []
    ids = []

    for i, dest in enumerate(_destinations):
        catalog_url = f"/destination/{dest.get('slug', '')}"
        doc_text = (
            f"{dest['name']} - {dest['location']}\n"
            f"{dest['description']}\n"
            f"Contact: {dest['contact']}\n"
            f"Instagram: {dest['instagram']}\n"
            f"Duration: {dest['duration']}\n"
            f"Difficulty: {dest['difficulty']}\n"
            f"Best for: {dest['best_for']}\n"
            f"Catalog link: {catalog_url}"
        )
        documents.append(doc_text)
        metadatas.append({
            "name": dest["name"],
            "slug": dest.get("slug", ""),
            "location": dest["location"],
            "difficulty": dest["difficulty"],
            "duration": dest["duration"]
        })
        ids.append(f"dest_{i}")

    embeddings = model.encode(documents).tolist()

    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )


def search_knowledge(query: str, n_results: int = 3) -> str:
    collection = get_collection()
    model = get_embedding_model()

    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results
    )

    if not results["documents"][0]:
        return "No relevant information found in knowledge base."

    context_parts = []
    for doc in results["documents"][0]:
        context_parts.append(doc)

    return "\n\n---\n\n".join(context_parts)
