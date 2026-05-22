import hashlib
import json
import os

from rag.embedder import embed_single
from rag.vector_store import get_cache_collection

THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.92"))


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.strip().lower().encode()).hexdigest()[:16]


def get_cached(prompt: str) -> dict | None:
    collection = get_cache_collection()

    if collection.count() == 0:
        return None

    embedding = embed_single(prompt)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=1,
        include=["metadatas", "distances"],
    )

    if not results["metadatas"] or not results["metadatas"][0]:
        return None

    distance = results["distances"][0][0]
    similarity = 1 - distance

    if similarity >= THRESHOLD:
        raw = results["metadatas"][0][0].get("response_json", "")
        try:
            print(f"[cache] HIT (similarity={similarity:.4f})")
            return json.loads(raw)
        except Exception:
            return None

    return None


def set_cache(prompt: str, response: dict) -> None:
    collection = get_cache_collection()
    embedding = embed_single(prompt)
    cache_id = _prompt_hash(prompt)

    collection.upsert(
        ids=[cache_id],
        embeddings=[embedding],
        documents=[prompt],
        metadatas=[{"response_json": json.dumps(response)}],
    )
    print(f"[cache] Stored response for prompt hash {cache_id}")
