import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "catalog.json"
MIN_PER_CATEGORY = 50


def _count(items: list[dict], category: str) -> int:
    return sum(1 for i in items if i.get("category") == category)


def _fill_with_mock(items: list[dict]) -> list[dict]:
    from scraper.mock_data import generate_mock_catalog

    mock = generate_mock_catalog()
    existing_ids = {i["id"] for i in items}
    tops_count = _count(items, "tops")
    bottoms_count = _count(items, "bottoms")

    for m in mock:
        if m["id"] in existing_ids:
            continue
        cat = m["category"]
        if cat == "tops" and tops_count >= MIN_PER_CATEGORY:
            continue
        if cat == "bottoms" and bottoms_count >= MIN_PER_CATEGORY:
            continue
        items.append(m)
        existing_ids.add(m["id"])
        if cat == "tops":
            tops_count += 1
        else:
            bottoms_count += 1

    return items


def _dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in items:
        key = item.get("id") or item.get("url") or item.get("name")
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


async def _run_hm() -> list[dict]:
    try:
        from scraper.hm_scraper import scrape_hm
        return await scrape_hm()
    except Exception as e:
        print(f"[orchestrator] H&M scraper failed: {e}")
        return []


def _run_asos() -> list[dict]:
    try:
        from scraper.asos_scraper import run_asos_spider
        return run_asos_spider()
    except Exception as e:
        print(f"[orchestrator] ASOS scraper failed: {e}")
        return []


async def run_all() -> list[dict]:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("[orchestrator] Starting H&M scraper...")
    hm_items = await _run_hm()
    print(f"[orchestrator] H&M: {len(hm_items)} items")

    print("[orchestrator] Starting ASOS scraper...")
    asos_items = _run_asos()
    print(f"[orchestrator] ASOS: {len(asos_items)} items")

    combined = _dedupe(hm_items + asos_items)
    tops = _count(combined, "tops")
    bottoms = _count(combined, "bottoms")
    print(f"[orchestrator] Combined: {tops} tops, {bottoms} bottoms")

    if tops < MIN_PER_CATEGORY or bottoms < MIN_PER_CATEGORY:
        print("[orchestrator] Filling gaps with mock data...")
        combined = _fill_with_mock(combined)

    tops = _count(combined, "tops")
    bottoms = _count(combined, "bottoms")
    print(f"[orchestrator] Final: {tops} tops, {bottoms} bottoms ({len(combined)} total)")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"[orchestrator] Saved to {DATA_FILE}")
    return combined


if __name__ == "__main__":
    asyncio.run(run_all())
