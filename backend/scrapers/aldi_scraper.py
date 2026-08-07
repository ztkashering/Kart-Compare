"""
aldi_scraper.py — Aldi (Lakewood, NJ — 80 NJ-70).

PLAIN-ENGLISH NOTE: Aldi's "Weekly Specials" page (aldi.us/en/weekly-specials/)
renders real product cards with a name, current price, and (for sale items)
an original price and a percent-off badge — and unlike the other platform
stores, it didn't need a ZIP-code/location confirmation step to load real
data. Aldi updates this page every Wednesday, so — same reasoning as
Seasons/Nutmeg/Kosher West/Kosher Village — deals are tagged with the real
Wednesday-to-Tuesday sale week.

IMPORTANT — Aldi is a general supermarket, not a dedicated kosher grocer
like the other six stores. Per the founder's explicit instruction:
  - NO meat or deli items are included from Aldi, at all, with ONE
    exception: items with "salmon" in the name are allowed through (fish
    doesn't carry the same kosher-slaughter concerns meat does).
  - Kosher certification (hechsher) is NOT something this scraper can
    verify — Aldi's own website doesn't publish that information per
    item. The site shows a clear disclaimer on the Aldi page (see
    build_site.py's STORE_META) telling shoppers to check the package's
    own kosher certification themselves before buying.

Each product in the scraped page text looks like this (one block per item,
always starting with "Current price:"):
    Current price: $6.49
    $649
    Original Price: $7.15
    $7.15
    9% off
    Lunch Buddies 12pk Apple Squeezies Varie, 3.2 oz Pouch
    38.4 oz
    Many in stock
Not every item is on sale (no "Original Price"/"X% off" lines for those),
and the very first real line after the price block is always the item
name — parse_deals() below uses that pattern rather than relying on any
fixed line count, since blocks vary in length.
"""

import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.base_scraper import guess_category, clean_item_name, current_wed_to_tue_window
from db.database import get_connection, init_db, insert_deal, clear_store_deals

STORE_SLUG = "aldi"
SPECIALS_URL = "https://www.aldi.us/en/weekly-specials/"
SAMPLE_PATH = Path(__file__).parent / "sample_data" / "aldi_2026-08-07_specials.txt"

# Splits the page text into one chunk per product — every product block
# starts with this exact phrase.
BLOCK_SPLIT_RE = re.compile(r"(?=Current price:)")

PRICE_RE = re.compile(r"Current price:\s*\$(\d+(?:\.\d{2})?)")

# Lines that are never the item name — used to skip past the price/
# percent-off/label lines and land on the first real name line.
SKIP_LINE_RE = re.compile(
    r"^\s*("
    r"Current price:.*|"
    r"Original Price:.*|"
    r"\$[\d,.]+\s*$|"
    r"\d+%\s*off\s*$|"
    r"per\s+(package|lb|each)\s*\(estimated\)\s*$|"
    r"/\s*(pkg|ea)\s*\(est\.?\)\s*$|"
    r"each\s*\(est\.?\)\s*$"
    r")\s*$",
    re.I,
)

# Aldi carries meat and deli items like any general supermarket. Per the
# founder's instruction, none of those belong on a kosher-shopper-focused
# site UNLESS they're salmon (fish, not covered by the same kosher-
# slaughter certification concern as meat).
NON_KOSHER_FRIENDLY_CATEGORY = "Meat & Deli"
ALLOWED_EXCEPTION_KEYWORDS = ["salmon"]

# Per the founder's explicit instruction (2026-08-07): Aldi's bakery items
# (bread, rolls, etc.) aren't Pas Yisroel or otherwise kosher-supervised
# baking, so the whole Bakery category is left off this page entirely —
# no exception, unlike the meat/salmon carve-out above.
EXCLUDED_CATEGORIES_NO_EXCEPTION = {"Bakery"}


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
        text = resp.text
        # Aldi's page is JavaScript-rendered — a plain request usually just
        # returns an empty page shell. If we don't see real product text,
        # treat this as "live fetch not usable" so it falls back to the
        # cached snapshot instead of saving zero deals.
        if "Current price:" not in text:
            return None
        return text
    except Exception as e:
        print(f"[aldi] Live fetch failed ({e}); using cached snapshot.")
        return None


def _extract_name(block_lines: list[str]) -> str | None:
    for line in block_lines:
        line = line.strip()
        if not line:
            continue
        if SKIP_LINE_RE.match(line):
            continue
        return line
    return None


def parse_deals(raw_text: str) -> list[dict]:
    date_from, date_to = current_wed_to_tue_window()

    deals = []
    blocks = [b for b in BLOCK_SPLIT_RE.split(raw_text) if b.strip()]
    for block in blocks:
        price_match = PRICE_RE.search(block)
        if not price_match:
            continue
        sale_price = float(price_match.group(1))

        lines = block.splitlines()
        # Drop the first line (the "Current price: ..." line itself) before
        # hunting for the name, so SKIP_LINE_RE's "Current price:" check
        # doesn't need to special-case line 0.
        name = _extract_name(lines[1:])
        if not name:
            continue
        item_name = clean_item_name(name)
        if not item_name:
            continue

        category = guess_category(item_name)
        is_allowed_meat_exception = any(
            kw in item_name.lower() for kw in ALLOWED_EXCEPTION_KEYWORDS
        )
        if category == NON_KOSHER_FRIENDLY_CATEGORY and not is_allowed_meat_exception:
            continue  # meat/deli, and not the one allowed exception — skip it
        if category in EXCLUDED_CATEGORIES_NO_EXCEPTION:
            continue  # bakery — always excluded, no exception

        deals.append(
            {
                "store_slug": STORE_SLUG,
                "item_name": item_name,
                "original_price": None,
                "sale_price": sale_price,
                "unit": None,
                "category": category,
                "date_valid_from": date_from,
                "date_valid_to": date_to,
                "raw_text": block.strip()[:300],
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
    print(f"[{STORE_SLUG}] Parsed {len(deals)} candidate deals (meat/deli filtered out except salmon; bakery always filtered out).")
    print(
        f"[{STORE_SLUG}] NOTE: Aldi updates its weekly ad on Wednesdays, so dates "
        f"shown are an ESTIMATED Wednesday-to-Tuesday sale week "
        f"({deals[0]['date_valid_from'] if deals else 'n/a'} to "
        f"{deals[0]['date_valid_to'] if deals else 'n/a'}). Aldi is not a "
        f"dedicated kosher grocer — kosher certification isn't published on "
        f"this page and isn't checked by this scraper."
    )

    print(f"\nFirst {min(limit_preview, len(deals))} scraped items:")
    for d in deals[:limit_preview]:
        print(
            f"  - [{d['category']:<7}] {d['item_name']:<50} ${d['sale_price']:.2f}"
        )

    if save_to_db:
        init_db()
        with get_connection() as conn:
            clear_store_deals(conn, STORE_SLUG)
            for d in deals:
                insert_deal(conn, d)
        print(f"\n[{STORE_SLUG}] Saved {len(deals)} deals to the database.")

    return deals


if __name__ == "__main__":
    run()
