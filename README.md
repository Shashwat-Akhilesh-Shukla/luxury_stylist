# Quickeee Gen AI Assignment: The Luxury Stylist Concierge

A context-aware fashion concierge backend — scrape inventory → embed into vector DB → LangGraph agent → FastAPI endpoint.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Scrape inventory
```bash
python -m scraper.run_scrapers
```
Runs H&M (Playwright) + ASOS (Scrapy) scrapers. Falls back to built-in mock catalog if scraping is blocked. Saves `data/catalog.json` with ≥50 tops + ≥50 bottoms.

### 4. Ingest into vector DB
```bash
python -m rag.ingest
```
Embeds all catalog items with `sentence-transformers` and stores them in ChromaDB at `data/chroma_db/`. Idempotent — safe to re-run.

### 5. Start the API
```bash
uvicorn api.main:app --reload
```
Visit `http://localhost:8000/docs` for the Swagger UI.

## API Usage

### `POST /api/v1/style-me`

**Request:**
```json
{
  "prompt": "I have dark navy chinos, what t-shirt and shoes should I wear for a summer yacht party?"
}
```

**Response:**
```json
{
  "recommended_items": [
    {
      "name": "Slim Fit Linen T-shirt",
      "price": "$19.99",
      "category": "tops",
      "color": "ivory",
      "description": "Breathable linen-blend tee with a clean finish.",
      "image_url": "https://...",
      "source": "H&M",
      "url": "https://www2.hm.com/..."
    }
  ],
  "total_price": "$19.99",
  "stylist_note": "The ivory linen tee cuts a crisp, nautical silhouette against your dark navy chinos — a pairing rooted in yacht-club tradition but elevated with modern ease.",
  "cache_hit": false
}
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system design, database schema, and prompt optimization strategies.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | ChromaDB storage path |
| `CACHE_SIMILARITY_THRESHOLD` | `0.92` | Cosine similarity threshold for cache hits |
