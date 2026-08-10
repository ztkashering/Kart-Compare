"""
kosher_village_scraper.py — Kosher Village (Lakewood, NJ).

PLAIN-ENGLISH NOTE: Kosher Village runs on a different website platform
than Seasons/Nutmeg/Kosher West (their site is at koshervillage.com, a
different e-commerce template entirely). The good news: unlike the other
three, this one does NOT need a browser to render — a plain web request
already returns the specials with item names and prices in the page's
HTML. That makes this the simplest, most reliable scraper of the bunch.

Each product on the specials page looks like this in the page text:
    "HALF MIX CHOCOLATE WAFER BARS12.2 $13.99$10.99 Add to cart"
i.e. name (sometimes with the size stuck directly onto it with no
space), then the "was" price, then the "now" price, then an "Add to
cart" button. parse_deals() below pulls those apart with a regular
expression.

No sale-date banner was found anywhere on this store's specials page,
so — same as Nutmeg and Kosher West — we tag deals with the real
Wednesday-to-Tuesday sale week these stores run on (confirmed by the
founder, who shops there) rather than a generic rolling window.
"""

import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.base_scraper import guess_category, clean_item_name, current_wed_to_tue_window
from db.database import get_connection, init_db, insert_deal

STORE_SLUG = "kosher-village"
SPECIALS_URL = "https://www.koshervillage.com/products/store-specials"
SAMPLE_PATH = Path(__file__).parent / "sample_data" / "kosher_village_2026-08-10_specials.txt"

# Matches: <name/size blob> $<original> $<sale> Add to cart
ITEM_RE = re.compile(
    r"(?P<label>.+?)\$(?P<original>\d+\.\d{2})\$(?P<sale>\d+\.\d{2})\s*Add to cart",
    re.I,
)


def get_page_text_live() -> str | None:
    try:
        import requests
    except ImportError:
        return None
    try:
        resp = requests.get(
            SPECIALS_URL,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LakewoodDealsBot/1.0)"},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[kosher_village] Live fetch failed ({e}); using cached snapshot.")
        return None


def parse_deals(raw_text: str) -> list[dict]:
    # Real weekly sale cycle (confirmed by the founder, who shops there):
    # Wednesday morning through Tuesday night. See base_scraper.py's
    # current_wed_to_tue_window() docstring for why.
    date_from, date_to = current_wed_to_tue_window()

    deals = []
    for m in ITEM_RE.finditer(raw_text):
        label = clean_item_name(m.group("label"))
        if not label:
            continue
        original_price = float(m.group("original"))
        sale_price = float(m.group("sale"))
        deals.append(
            {
                "store_slug": STORE_SLUG,
                "item_name": label,
                "original_price": original_price,
                "sale_price": sale_price,
                "unit": None,
                "category": guess_category(label),
                "date_valid_from": date_from,
                "date_valid_to": date_to,
                "raw_text": m.group(0),
            }
        )
    return deals


def run(save_to_db: bool = True, limit_preview: int = 8) -> list[dict]:
    text = get_page_text_live()
    is_live = text is not None
    if not is_live:
        print(f"[{STORE_SLUG}] Using cached snapshot (dev fallback).")
        text = SAMPLE_PATH.read_text()

    mode = "LIVE" if is_live else "CACHED SNAPSHOT (dev fallback)"
    print(f"[{STORE_SLUG}] Source mode: {mode}")

    deals = parse_deals(text)
    print(f"[{STORE_SLUG}] Parsed {len(deals)} candidate deals.")
    print(
        f"[{STORE_SLUG}] NOTE: no valid-through date is published on this "
        f"store's specials page, so dates shown are an ESTIMATED "
        f"Wednesday-to-Tuesday sale week "
        f"({deals[0]['date_valid_from'] if deals else 'n/a'} to "
        f"{deals[0]['date_valid_to'] if deals else 'n/a'})."
    )

    print(f"\nFirst {min(limit_preview, len(deals))} scraped items:")
    for d in deals[:limit_preview]:
        print(
            f"  - [{d['category']:<7}] {d['item_name']:<40} "
            f"${d['sale_price']:.2f} (was ${d['original_price']:.2f})"
        )

    if save_to_db:
        init_db()
        with get_connection() as conn:
            for d in deals:
                insert_deal(conn, d)
        print(f"\n[{STORE_SLUG}] Saved {len(deals)} deals to the database.")

    return deals


if __name__ == "__main__":
    run()
