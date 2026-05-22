import os
from pathlib import Path
import chromadb
from chromadb.config import Settings

CATALOG_COLLECTION = "fashion_catalog"
CACHE_COLLECTION = "semantic_cache"

_client: chromadb.Client | None = None


def get_client() -> chromadb.Client:
    global _client
    if _client is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_catalog_collection() -> chromadb.Collection:
    return get_client().get_or_create_collection(
        name=CATALOG_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def get_cache_collection() -> chromadb.Collection:
    return get_client().get_or_create_collection(
        name=CACHE_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_items(items: list[dict], embeddings: list[list[float]]) -> None:
    collection = get_catalog_collection()
    collection.upsert(
        ids=[item["id"] for item in items],
        embeddings=embeddings,
        documents=[
            f"{item['name']} {item['description']}" for item in items
        ],
        metadatas=[
            {
                "name": item.get("name", ""),
                "price": item.get("price", ""),
                "price_float": _parse_price(item.get("price", "0")),
                "category": item.get("category", ""),
                "color": item.get("color", ""),
                "source": item.get("source", ""),
                "image_url": item.get("image_url", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            }
            for item in items
        ],
    )


def query_catalog(
    query_embedding: list[float],
    n_results: int = 10,
    category_filter: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    collection = get_catalog_collection()

    where: dict = {}
    if category_filter:
        where["category"] = {"$eq": category_filter}
    if max_price is not None:
        price_clause = {"price_float": {"$lte": max_price}}
        if where:
            where = {"$and": [where, price_clause]}
        else:
            where = price_clause

    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["metadatas", "distances", "documents"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)
    items = []
    for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
        items.append({**meta, "relevance_score": round(1 - dist, 4)})
    return items


def _parse_price(price_str: str) -> float:
    import re
    nums = re.findall(r"[\d.]+", price_str.replace(",", ""))
    return float(nums[0]) if nums else 0.0
