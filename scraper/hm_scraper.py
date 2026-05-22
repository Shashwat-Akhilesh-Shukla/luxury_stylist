import asyncio
import json
import random
from typing import Optional
from playwright.async_api import async_playwright, Page

CATEGORIES = {
    "tops": "https://www2.hm.com/en_us/men/products/tops.html",
    "bottoms": "https://www2.hm.com/en_us/men/products/trousers.html",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

COLOR_KEYWORDS = ["black", "white", "navy", "blue", "grey", "gray", "green", "red",
                  "beige", "khaki", "brown", "olive", "cream", "ecru", "tan", "camel"]


def _infer_color(name: str) -> str:
    name_lower = name.lower()
    for color in COLOR_KEYWORDS:
        if color in name_lower:
            return color
    return "multicolor"


async def _dismiss_overlays(page: Page) -> None:
    for selector in ["button#onetrust-accept-btn-handler", "[data-testid='close-button']",
                     ".modal-close", "button.cookie-notice-close"]:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await asyncio.sleep(1)
        except Exception:
            pass


async def _scroll_and_load(page: Page, max_scrolls: int = 8) -> None:
    for _ in range(max_scrolls):
        await page.keyboard.press("End")
        await asyncio.sleep(random.uniform(1.5, 3.0))
        try:
            btn = page.locator(
                "button.load-more-heading, button[data-testid='load-more'], .load-more"
            ).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await asyncio.sleep(random.uniform(2.0, 3.5))
        except Exception:
            pass


async def _extract_products(page: Page, category: str, limit: int = 70) -> list[dict]:
    items = []

    selector_groups = [
        ("article.hm-product-item", "h3", ".price-value", "img", "a"),
        ("li.product-item", ".item-heading", ".price", "img", "a"),
        ("[data-testid='product-item']", "[data-testid='product-title']",
         "[data-testid='price']", "img", "a"),
        (".product-listing article", "h3", ".price", "img", "a"),
    ]

    products = []
    for (container, *_) in selector_groups:
        products = await page.query_selector_all(container)
        if len(products) > 5:
            break

    for product in products[:limit]:
        try:
            name_el = await product.query_selector(
                "h3, .item-heading, [data-testid='product-title'], .product-name"
            )
            price_el = await product.query_selector(
                ".price-value, [data-testid='price'], .price strong, .price"
            )
            img_el = await product.query_selector("img")
            link_el = await product.query_selector("a")

            name = (await name_el.inner_text()).strip() if name_el else ""
            price_text = (await price_el.inner_text()).strip() if price_el else ""
            img_src = (await img_el.get_attribute("src") or
                       await img_el.get_attribute("data-src") or "") if img_el else ""
            if img_src.startswith("//"):
                img_src = "https:" + img_src
            href = await link_el.get_attribute("href") if link_el else ""
            if href and not href.startswith("http"):
                href = "https://www2.hm.com" + href

            if name and price_text:
                items.append({
                    "id": f"hm_{abs(hash(href)) % 999999:06d}",
                    "name": name,
                    "price": price_text,
                    "image_url": img_src or "https://www2.hm.com/favicon.ico",
                    "category": category,
                    "description": f"{name} — {category} from H&M.",
                    "color": _infer_color(name),
                    "source": "H&M",
                    "url": href,
                })
        except Exception:
            continue

    return items


async def scrape_hm(limit_per_category: int = 70) -> list[dict]:
    all_items = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page = await context.new_page()

            for category, url in CATEGORIES.items():
                try:
                    print(f"[H&M] Scraping {category}...")
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(random.uniform(3.0, 5.0))
                    await _dismiss_overlays(page)
                    await _scroll_and_load(page)
                    items = await _extract_products(page, category, limit_per_category)
                    all_items.extend(items)
                    print(f"[H&M] Got {len(items)} {category}")
                except Exception as e:
                    print(f"[H&M] Failed {category}: {e}")

            await browser.close()
    except Exception as e:
        print(f"[H&M] Browser error: {e}")

    return all_items


if __name__ == "__main__":
    items = asyncio.run(scrape_hm())
    print(f"Total: {len(items)}")
    print(json.dumps(items[:2], indent=2))
