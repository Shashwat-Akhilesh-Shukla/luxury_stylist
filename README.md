# Quickeee Gen AI Assignment: The Luxury Stylist Concierge

This repository contains the backend system for Quickeee's ultra-premium fashion concierge, as per the assignment requirements.

## Overview
The system provides a context-aware shopping assistant pipeline that can scrape inventory, store it intelligently using vector embeddings, and use an agentic LLM workflow to recommend fashion pairings via a FastAPI endpoint.

## Project Structure
- `scraper/`: Web scraping scripts (Playwright/Scrapy)
- `rag/`: Vector database and embedding logic
- `agent/`: Agentic workflow (LangChain/LangGraph)
- `api/`: FastAPI endpoints
- `data/`: Extracted JSON data
