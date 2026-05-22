from sentence_transformers import SentenceTransformer
import numpy as np

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def build_item_text(item: dict) -> str:
    parts = [
        item.get("name", ""),
        item.get("description", ""),
        f"Color: {item.get('color', '')}",
        f"Category: {item.get('category', '')}",
        f"Price: {item.get('price', '')}",
        f"Brand: {item.get('source', '')}",
    ]
    return " | ".join(p for p in parts if p.strip())


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    return vectors.tolist()


def embed_single(text: str) -> list[float]:
    return embed_texts([text])[0]
