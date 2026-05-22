from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from rag.vector_store import get_catalog_collection, get_cache_collection
    get_catalog_collection()
    get_cache_collection()
    print("[startup] ChromaDB collections ready.")
    yield
    print("[shutdown] Goodbye.")


app = FastAPI(
    title="Quickeee Luxury Stylist Concierge",
    description=(
        "Context-aware fashion concierge powered by RAG + Gemini. "
        "Scrapes real inventory, embeds it into a vector DB, and uses an "
        "agentic LangGraph workflow to style your perfect outfit."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.router import router
app.include_router(router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
