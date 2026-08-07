"""
aldi_scraper.py — Aldi (Lakewood, NJ — 80 NJ-70).

PLAIN-ENGLISH NOTE: Aldi's "Weekly Specials" page (aldi.us/en/weekly-specials/)
renders real product cards with a name, current price, and (for sale items)
an original price and a percent-off badge. Aldi updates this page every
Wednesday, so — same reasoning as Seasons/Nutmeg/Kosher West/Kosher
Village — deals are tagged with the real Wednesday-to-Tuesday sale week.

CORRECTION (2026-08-07): an earlier version of this file claimed Aldi
"didn't need a ZIP-code/location confirmation step to load real data,"
unlike the platform behind Seasons/Nutmeg/Kosher West. That claim was
never actually verified with a live browser — it was an assumption, and
a risky one: Aldi is a national multi-location chain, exactly the kind of
site where grocery_platform_scraper.py's docstring warns a generic URL
can silently serve a different region's ad with no error at all. So this
now confirms the Lakewood-area ZIP (08701) via a real browser before
reading the specials page, the same way every other multi-location store
in this codebase does — see get_page_live() below. UNVERIFIED CAVEAT:
this sandbox has no browser installed (same limitation noted throughout
this codebase), so the ZIP-confirmation selectors below are a best-effort
guess, not yet confirmed against Aldi's real store-locator flow. The
first live run (e.g. the scheduled task) needs to confirm or correct
them, then save that output as a fresh sample_data/aldi_<date>_specials.txt
snapshot — the current one predates this fix and was never confirmed to
be Lakewood-area data either.

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


ZIP_CODE = "08701"  # Lakewood, NJ


def get_page_text_live() -> str | None:
    """Confirm the Lakewood-area (08701) store via Aldi's store locator,
    then read the weekly-specials page with a real browser.

    UNVERIFIED — see the module docstring's 2026-08-07 correction. This
    replaces a plain `requests.get()` that could only ever see whatever
    Aldi serves with no location set at all (most likely a generic
    default store, not necessarily Lakewood's), and had no way to detect
    if the "wrong region" trap already documented in
    grocery_platform_scraper.py was happening here too.
    """
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

        try:
            accept_btn = driver.find_element(
                By.XPATH, "//*[self::button or self::a][contains(translate(text(),'ACEPT','acept'),'accept')]"
            )
            accept_btn.click()
            time.sleep(1)
        except Exception:
            pass  # no cookie banner present, fine

        try:
            zip_input = driver.find_element(By.XPATH, "//input[@type='text' or @type='tel' or @type='search']")
            zip_input.send_keys(ZIP_CODE)
            go_btn = driver.find_element(By.XPATH, "//button[not(@type='text')]")
            go_btn.click()
            time.sleep(2)
            driver.get(SPECIALS_URL)  # reload specials with the ZIP now confirmed
        except Exception as e:
            print(
                f"[aldi] Could not confirm the Lakewood, NJ (08701) store "
                f"automatically ({e}); the specials below may be for the "
                f"wrong region."
            )

        driver.implicitly_wait(5)
        time.sleep(2)
        text = driver.page_source

        if "Current price:" not in text:
            return None
        return text
    except Exception as e:
        print(f"[aldi] Live fetch failed ({e}); using cached snapshot.")
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
