import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import re

ASOS_TOPS_URL = (
    "https://www.asos.com/api/product/search/v2/categories/7616"
    "?channel=desktop-web&country=US&currency=USD&lang=en-US&limit=72&offset=0&rowlength=4&store=US"
)
ASOS_BOTTOMS_URL = (
    "https://www.asos.com/api/product/search/v2/categories/4174"
    "?channel=desktop-web&country=US&currency=USD&lang=en-US&limit=72&offset=0&rowlength=4&store=US"
)


def _clean_price(val) -> str:
    if isinstance(val, (int, float)):
        return f"${val:.2f}"
    return str(val)


class AsosSpider(scrapy.Spider):
    name = "asos"
    custom_settings = {
        "DOWNLOAD_DELAY": 2.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "WARNING",
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.asos.com/",
        },
        "RETRY_TIMES": 3,
        "HTTPERROR_ALLOW_ALL": True,
    }

    start_urls = [ASOS_TOPS_URL, ASOS_BOTTOMS_URL]

    def parse(self, response):
        category = "tops" if "7616" in response.url else "bottoms"

        if response.status != 200:
            self.logger.warning(f"ASOS returned {response.status} for {category}")
            return

        try:
            data = response.json()
        except Exception:
            self.logger.warning("ASOS response is not JSON")
            return

        products = data.get("products", [])
        for p in products:
            price_data = p.get("price", {})
            current = price_data.get("current", {})
            price_val = current.get("value") or current.get("text", "$0.00")

            img_url = p.get("imageUrl", "")
            if img_url and not img_url.startswith("http"):
                img_url = "https://" + img_url

            colour = (p.get("colour") or "").lower() or "multicolor"

            yield {
                "id": f"asos_{p.get('id', abs(hash(p.get('name',''))) % 999999)}",
                "name": p.get("name", "").strip(),
                "price": _clean_price(price_val),
                "image_url": img_url,
                "category": category,
                "description": p.get("description") or p.get("name", "").strip(),
                "color": colour,
                "source": "ASOS",
                "url": f"https://www.asos.com{p.get('url', '')}",
            }


def run_asos_spider() -> list[dict]:
    collected: list[dict] = []

    class _Collector:
        def process_item(self, item, spider):
            collected.append(dict(item))
            return item

    settings = get_project_settings()
    settings.update({
        "ITEM_PIPELINES": {"scraper.asos_scraper._Collector": 300},
        "LOG_LEVEL": "WARNING",
    })

    process = CrawlerProcess(settings)
    process.crawl(AsosSpider)
    process.start()

    return collected


if __name__ == "__main__":
    import json
    items = run_asos_spider()
    print(f"Total: {len(items)}")
    print(json.dumps(items[:2], indent=2))
