import json
from pathlib import Path
from rag.embedder import embed_texts, build_item_text
from rag.vector_store import upsert_items, get_catalog_collection

DATA_FILE = Path(__file__).parent.parent / "data" / "catalog.json"
BATCH_SIZE = 64


def load_catalog() -> list[dict]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Catalog not found at {DATA_FILE}. Run: python -m scraper.run_scrapers"
        )
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def already_indexed() -> set[str]:
    collection = get_catalog_collection()
    result = collection.get(include=[])
    return set(result.get("ids", []))


def ingest() -> None:
    catalog = load_catalog()
    indexed = already_indexed()

    new_items = [item for item in catalog if item["id"] not in indexed]
    if not new_items:
        print(f"[ingest] All {len(catalog)} items already indexed.")
        return

    print(f"[ingest] Indexing {len(new_items)} new items (skipping {len(indexed)} existing)...")

    for i in range(0, len(new_items), BATCH_SIZE):
        batch = new_items[i : i + BATCH_SIZE]
        texts = [build_item_text(item) for item in batch]
        embeddings = embed_texts(texts)
        upsert_items(batch, embeddings)
        print(f"[ingest] {min(i + BATCH_SIZE, len(new_items))}/{len(new_items)}")

    print(f"[ingest] Done. Total in DB: {len(catalog)}")


if __name__ == "__main__":
    ingest()
