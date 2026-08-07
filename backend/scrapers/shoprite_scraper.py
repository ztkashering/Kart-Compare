"""
shoprite_scraper.py — ShopRite (Jackson, NJ — closest working store to
Lakewood; Lakewood itself has no ShopRite location).

PLAIN-ENGLISH NOTE ON WHAT THIS NEEDS: shoprite.com/circulars serves its
weekly ad through an embedded interactive circular widget (a Flipp-style
viewer), the same kind of thing found behind Bingo's PDF widget — a plain
HTTP request just gets an empty page shell, so this needs a real/headless
browser (Selenium), same as the grocery_platform stores. It also needs a
store confirmed first: shoprite.com tracks which physical store's ad
you're viewing via a ZIP/store-locator step, not the web address alone
(same trap documented in grocery_platform_scraper.py) — this uses the
Jackson, NJ ZIP (08527) to pin that down before reading the circular.

HONEST STATUS: my dev sandbox has no browser installed (same caveat as
every other scraper here — see the README's "Is this scraper live?"
section), so the CSS selectors in _extract_items_from_source() below are
a best-effort guess at Flipp's typical widget markup, NOT yet confirmed
against the real live page. There's also no cached snapshot to fall back
on, because nobody has captured one yet. Rather than invent fake ShopRite
prices to make this page look populated (see bingo_scraper.py for why
that's off the table), this will honestly report zero deals until it's
run somewhere with a real browser — same as the twice-weekly scheduled
task already covering the other stores. Once that first live run
confirms (or corrects) the selectors below, its output should be saved
as sample_data/shoprite_<date>_specials.txt so future runs have a real
fallback too.

ShopRite is a general supermarket, not a dedicated kosher grocer — per
the founder's explicit instruction, ALL meat and deli items are excluded
from this page, with no exception (unlike Aldi, which allows salmon
through). Kosher certification (hechsher) isn't published on this page
either, so — same as Aldi — this scraper can't verify it; the site shows
a disclaimer instead (see build_site.py's STORE_META).
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.base_scraper import parse_standard_price, guess_category, clean_item_name, current_wed_to_tue_window
from db.database import get_connection, init_db, insert_deal, clear_store_deals

STORE_SLUG = "shoprite"
CIRCULARS_URL = "https://www.shoprite.com/circulars"
ZIP_CODE = "08527"  # Jackson, NJ — closest working ShopRite to Lakewood
SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"

NON_KOSHER_FRIENDLY_CATEGORY = "Meat & Deli"


def _extract_items_from_source(page_source) -> list[tuple[str, str, str]]:
    """Best-effort parse of a Flipp-style circular widget's product tiles.

    UNVERIFIED — see the module docstring. These selectors are a
    reasonable starting guess (Flipp widgets commonly use classes like
    "flipp-item"/"item-name"/"item-price"), but the first real live run
    needs to confirm them against the actual rendered page and fix them
    here if wrong, the same way grocery_platform_scraper.py's selectors
    were confirmed by direct inspection.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page_source, "html.parser")
    items = []
    for card in soup.select("[class*='flipp-item'], [class*='item-card'], [class*='product-tile']"):
        name_el = card.select_one("[class*='item-name'], [class*='product-name'], [class*='title']")
        price_el = card.select_one("[class*='item-price'], [class*='product-price'], [class*='price']")
        old_el = card.select_one("[class*='original-price'], [class*='was-price'], [class*='old-price']")
        name = name_el.get_text(strip=True) if name_el else None
        price_text = price_el.get_text(strip=True) if price_el else ""
        old_text = old_el.get_text(strip=True) if old_el else ""
        if name and price_text:
            items.append((name, price_text, old_text))
    return items


def get_circular_items_live() -> list[tuple[str, str, str]] | None:
    """Confirm the Jackson, NJ store via ZIP lookup, then read the
    circular widget. Returns None if live fetching isn't possible in
    this environment (no browser, or the widget can't be found)."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        import time
    except ImportError as e:
        print(f"[shoprite] Live mode unavailable, missing package: {e}")
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(CIRCULARS_URL)
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
        except Exception as e:
            print(
                f"[shoprite] Could not confirm the Jackson, NJ store automatically "
                f"({e}); the circular below may be for the wrong location."
            )

        driver.implicitly_wait(5)
        time.sleep(2)

        items = _extract_items_from_source(driver.page_source)
        if not items:
            print(
                "[shoprite] No product tiles found on the circular page — "
                "either no current ad is posted, or the widget's real markup "
                "doesn't match the selectors guessed in this scraper yet."
            )
            return None
        return items
    except Exception as e:
        print(f"[shoprite] Live fetch failed ({e}).")
        return None
    finally:
        if driver:
            driver.quit()


def get_items_cached() -> list[tuple[str, str, str]]:
    matches = sorted(SAMPLE_DATA_DIR.glob(f"{STORE_SLUG}_*_specials.txt"))
    if not matches:
        return []
    items = []
    for line in matches[0].read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|||")]
        while len(parts) < 3:
            parts.append("")
        name, price_text, old_text = parts[0], parts[1], parts[2]
        if name:
            items.append((name, price_text, old_text))
    return items


def parse_deals(items: list[tuple[str, str, str]]) -> list[dict]:
    date_from, date_to = current_wed_to_tue_window()

    deals = []
    for name, price_text, old_text in items:
        sale_price, unit = parse_standard_price(price_text)
        if sale_price is None:
            continue
        item_name = clean_item_name(name)
        if not item_name:
            continue

        category = guess_category(item_name)
        if category == NON_KOSHER_FRIENDLY_CATEGORY:
            continue  # ShopRite: meat/deli always excluded, no exception

        original_price, _ = parse_standard_price(old_text) if old_text else (None, None)
        deals.append(
            {
                "store_slug": STORE_SLUG,
                "item_name": item_name,
                "original_price": original_price,
                "sale_price": sale_price,
                "unit": unit,
                "category": category,
                "date_valid_from": date_from,
                "date_valid_to": date_to,
                "raw_text": f"{name} | {price_text} | {old_text}"[:300],
            }
        )
    return deals


def run(save_to_db: bool = True, limit_preview: int = 8) -> list[dict]:
    items = get_circular_items_live()
    is_live = items is not None
    if not is_live:
        items = get_items_cached()
        if items:
            print(f"[{STORE_SLUG}] Using cached snapshot (dev fallback).")
        else:
            print(f"[{STORE_SLUG}] No live browser available and no cached snapshot exists yet.")

    mode = "LIVE" if is_live else ("CACHED SNAPSHOT (dev fallback)" if items else "NONE")
    print(f"[{STORE_SLUG}] Source mode: {mode}")

    deals = parse_deals(items)
    print(f"[{STORE_SLUG}] Parsed {len(deals)} candidate deals (meat/deli always filtered out).")
    if not deals:
        print(
            f"[{STORE_SLUG}] Zero deals is expected here, not a bug, until this runs "
            f"somewhere with a real browser (e.g. the twice-weekly scheduled task) — "
            f"see the module docstring."
        )
    else:
        print(
            f"[{STORE_SLUG}] NOTE: ShopRite's site doesn't publish an exact valid-through "
            f"date on the circular, so dates shown are an ESTIMATED Wednesday-to-Tuesday "
            f"sale week ({deals[0]['date_valid_from']} to {deals[0]['date_valid_to']})."
        )

    print(f"\nFirst {min(limit_preview, len(deals))} scraped items:")
    for d in deals[:limit_preview]:
        price_str = f"${d['sale_price']:.2f}"
        unit_str = f"/{d['unit']}" if d["unit"] else ""
        print(f"  - [{d['category']:<7}] {d['item_name']:<50} {price_str}{unit_str}")

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
