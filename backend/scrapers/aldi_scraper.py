"""
aldi_scraper.py — Aldi (Lakewood-area store: ALDI CTV 162, 86 NJ Route 70,
Toms River, NJ 08755 — this is the "80 NJ-70" location right on the
Lakewood/Toms River line, the closest real Aldi to Lakewood).

PLAIN-ENGLISH NOTE (updated 2026-08-07, after the founder flagged missed
sales): the first pass of this scraper only captured the small default
preview shown on aldi.us/en/weekly-specials/ (4-8 items per section), not
the full lists. Two things were fixed:
  1. LOCATION. Like the Seasons/Nutmeg/Kosher West platform, this site
     decides which store's ad to show via a location cookie, not the URL.
     Without confirming a store, it silently showed a Brooklyn, NY store's
     ad. Live scraping must first set the store to ALDI CTV 162 (zip
     08755 / "80 NJ-70") via the site's location picker before reading
     anything — get_all_specials_live() below does this.
  2. COVERAGE. The homepage only shows a short preview per section, each
     with a "View all (N+)" link to the full list. Real deals live at:
       - /store/aldi/collections/rc-weekly-ad   ("Weekly Ad Products")
       - /store/aldi/pages/price-drops          ("Price Drops" — has two
         sub-lists: fresh meat/seafood, and packaged snacks/drinks)
     Both need their "Load More" button clicked until it stops adding new
     items, not just the first page.

CATEGORY RULES (per the founder, updated 2026-08-07 — this REPLACES the
original "no meat except salmon" rule):
  - ONLY these are shown from Aldi: Produce, Eggs, Pantry (includes canned
    goods), and Beverages (drinks). Everything else — meat/deli/seafood
    (including salmon — no exception anymore), dairy, bakery, frozen,
    candy & snacks, household, health & beauty — is left off entirely.
  - "Eggs" isn't one of base_scraper's category buckets (it would
    otherwise fall into the "Pantry" catch-all), so items with "egg" in
    the name are explicitly allowed through regardless of guessed
    category.
  - Kosher certification: Aldi's own site DOES have a "Kosher" tagged
    collection (aldi.us/store/aldi/collections/rc-kosher) — but checking
    it (2026-08-07) showed only 4 items store-wide carry that tag, far
    fewer than the pantry/beverage items Aldi actually sells with a real
    hechsher on the physical package. That makes the tag too sparse to
    use as a hard filter (it would wrongly exclude genuinely kosher items
    just because Aldi's own metadata hasn't caught up). So this scraper
    does NOT gate on it — instead, every Aldi page carries a clear
    disclaimer (see build_site.py's STORE_META) telling shoppers to check
    the package's own kosher symbol before buying, same as before.

Each product in the scraped page text looks like this (one block per
item, always starting with "Current price:"):
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

from scrapers.base_scraper import (
    guess_category, clean_item_name, current_wed_to_tue_window, CATEGORY_KEYWORDS,
)
from db.database import get_connection, init_db, insert_deal

STORE_SLUG = "aldi"
SPECIALS_URL = "https://www.aldi.us/en/weekly-specials/"
WEEKLY_AD_COLLECTION_URL = "https://www.aldi.us/store/aldi/collections/rc-weekly-ad"
PRICE_DROPS_URL = "https://www.aldi.us/store/aldi/pages/price-drops"
STORE_ZIP = "08755"  # ALDI CTV 162, 86 NJ Route 70, Toms River (the Lakewood-area store)
SAMPLE_PATH = Path(__file__).parent / "sample_data" / "aldi_2026-08-07_specials.txt"

# Splits the page text into one chunk per product — every product block
# starts with this exact phrase.
BLOCK_SPLIT_RE = re.compile(r"(?=Current price:)")

PRICE_RE = re.compile(r"Current price:\s*\$(\d+(?:\.\d{2})?)")
ORIGINAL_PRICE_RE = re.compile(r"Original Price:\s*\$(\d+(?:\.\d{2})?)")

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

# Only these categories are shown from Aldi (see docstring above for why).
ALDI_ALLOWED_CATEGORIES = {"Produce", "Beverages", "Pantry"}
# "Eggs" has no category bucket of its own in base_scraper.py — allow by
# name instead of category so egg items aren't accidentally dropped.
ALWAYS_ALLOWED_NAME_KEYWORDS = ["egg"]

# HARD SAFETY NET — do not remove. guess_category() checks categories in a
# fixed order and returns on the first keyword match, which means a meat
# item whose name also contains a seasoning/produce word (e.g. "Salt &
# Pepper Seasoned Brisket", "Cilantro Lime Seasoned Chicken", "Sun-Dried
# Tomato & Basil Seasoned Chicken") can get miscategorized as "Produce"
# BEFORE its real "Meat & Deli" keyword is ever checked — found this the
# hard way on 2026-08-07 when three chicken/brisket items slipped through
# under "Produce". Since the founder was explicit and repeated that meat
# must NEVER appear on this page, this checks the item name directly
# against the full Meat & Deli keyword list, independent of whatever
# category guess_category() landed on, and excludes it regardless.
_MEAT_DELI_KEYWORDS = CATEGORY_KEYWORDS["Meat & Deli"]


def _is_meat_or_deli(item_name_lower: str) -> bool:
    return any(kw in item_name_lower for kw in _MEAT_DELI_KEYWORDS)


def get_all_specials_live() -> str | None:
    """Fetch the full Weekly Ad Products + Price Drops lists for the
    Lakewood-area store via a real browser (location must be confirmed
    first — see the docstring's LOCATION note). Returns combined page
    text, or None if live browsing isn't available in this environment
    (falls back to the cached snapshot in that case)."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        import time
    except ImportError as e:
        print(f"[aldi] Live mode unavailable, missing package: {e}")
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(SPECIALS_URL)
        time.sleep(2)
        # Confirm the Lakewood-area store (zip 08755) via the location
        # picker before reading anything — see docstring's LOCATION note.
        try:
            change_store = driver.find_element(By.XPATH, "//button[contains(text(),'Change store') or contains(text(),'Edit')]")
            change_store.click()
            time.sleep(1)
            zip_input = driver.find_element(By.XPATH, "//input[@placeholder='Enter your address' or @type='text']")
            zip_input.send_keys(STORE_ZIP)
            time.sleep(1)
            suggestion = driver.find_element(By.XPATH, f"//*[contains(text(),'{STORE_ZIP}')]")
            suggestion.click()
            time.sleep(1)
            shop_here = driver.find_element(By.XPATH, "//button[contains(text(),'Shop this store') or contains(text(),'Select')]")
            shop_here.click()
            time.sleep(1)
            confirm = driver.find_element(By.XPATH, "//button[contains(text(),'Confirm')]")
            confirm.click()
            time.sleep(2)
        except Exception as e:
            print(f"[aldi] Could not confirm store location automatically ({e}); "
                  f"data may be for the wrong store.")

        combined_text = ""

        # Weekly Ad Products — click Load More until it stops adding items.
        driver.get(WEEKLY_AD_COLLECTION_URL)
        time.sleep(2)
        last_len = -1
        for _ in range(15):  # safety cap
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if len(body_text) == last_len:
                break
            last_len = len(body_text)
            try:
                load_more = driver.find_element(By.XPATH, "//button[contains(text(),'Load More')]")
                load_more.click()
                time.sleep(1.5)
            except Exception:
                break
        combined_text += driver.find_element(By.TAG_NAME, "body").text + "\n"

        # Price Drops — a curated page (meat/seafood + packaged snacks),
        # not paginated the same way.
        driver.get(PRICE_DROPS_URL)
        time.sleep(2)
        combined_text += driver.find_element(By.TAG_NAME, "body").text + "\n"

        return combined_text if "Current price:" in combined_text else None
    except Exception as e:
        print(f"[aldi] Live fetch failed ({e}).")
        return None
    finally:
        if driver:
            driver.quit()


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
    seen_names = set()
    blocks = [b for b in BLOCK_SPLIT_RE.split(raw_text) if b.strip()]
    for block in blocks:
        price_match = PRICE_RE.search(block)
        if not price_match:
            continue
        sale_price = float(price_match.group(1))

        # HONESTY CHECK (added 2026-08-07, after the founder caught this):
        # earlier passes included items that only ever showed a single
        # "Current price" with no "Original Price" — those are just Aldi's
        # regular everyday price, not a real markdown. This site is about
        # deals, so an item only counts if there's real before/after
        # pricing evidence. If a category ends up with zero qualifying
        # items this week, it should show nothing rather than be padded
        # with regular-price items.
        original_match = ORIGINAL_PRICE_RE.search(block)
        if not original_match:
            continue
        original_price = float(original_match.group(1))
        if original_price <= sale_price:
            continue  # not actually a markdown

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

        # De-dupe — the same item can legitimately appear in both the
        # Weekly Ad Products list and the Price Drops list.
        dedupe_key = (item_name.lower(), sale_price)
        if dedupe_key in seen_names:
            continue
        seen_names.add(dedupe_key)

        category = guess_category(item_name)
        name_lower = item_name.lower()

        # Hard safety net first — see _is_meat_or_deli's comment above.
        # This overrides everything else, even if guess_category() (or the
        # "always allowed" egg check below) would otherwise have let it
        # through.
        if _is_meat_or_deli(name_lower):
            continue

        always_allowed = any(kw in name_lower for kw in ALWAYS_ALLOWED_NAME_KEYWORDS)
        if category not in ALDI_ALLOWED_CATEGORIES and not always_allowed:
            continue  # not Produce/Beverages/Pantry, and not an egg item — skip it

        deals.append(
            {
                "store_slug": STORE_SLUG,
                "item_name": item_name,
                "original_price": original_price,
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
    text = get_all_specials_live()
    is_live = text is not None
    if not is_live:
        print(f"[{STORE_SLUG}] Using cached snapshot (dev fallback).")
        text = SAMPLE_PATH.read_text()

    mode = "LIVE" if is_live else "CACHED SNAPSHOT (dev fallback)"
    print(f"[{STORE_SLUG}] Source mode: {mode}")

    deals = parse_deals(text)
    print(f"[{STORE_SLUG}] Parsed {len(deals)} candidate deals (Produce/Eggs/Pantry/Beverages only).")
    print(
        f"[{STORE_SLUG}] NOTE: Aldi updates its weekly ad on Wednesdays, so dates "
        f"shown are an ESTIMATED Wednesday-to-Tuesday sale week "
        f"({deals[0]['date_valid_from'] if deals else 'n/a'} to "
        f"{deals[0]['date_valid_to'] if deals else 'n/a'}). Aldi is not a "
        f"dedicated kosher grocer — kosher certification isn't reliably "
        f"published on this site and isn't checked by this scraper."
    )

    print(f"\nFirst {min(limit_preview, len(deals))} scraped items:")
    for d in deals[:limit_preview]:
        print(
            f"  - [{d['category']:<7}] {d['item_name']:<50} ${d['sale_price']:.2f}"
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
