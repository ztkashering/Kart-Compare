"""
grocery_platform_scraper.py — shared scraper for the "Rosie-style" grocery
e-commerce platform used by Seasons, Nutmeg, and Kosher West.

PLAIN-ENGLISH NOTE: while researching each store, I found that Seasons
(seasonskosher.com), Nutmeg (nutmegkoshermarket.com), and Kosher West
(kosherwest.com) are all built on the exact same underlying website
software. Same page layout, same URL pattern
(`https://<domain>/<location>/category/specials`), same HTML structure.
So instead of writing three separate scrapers, this one file handles all
three — each store's own file just calls into this with its own domain.

Two important details from the research:
  1. These pages are JavaScript-rendered (a plain HTTP request just shows
     "Loading"), so live scraping needs a real/headless browser (Selenium),
     same as the other stores.
  2. Unlike Gourmet Glatt's flyer, prices here are normal decimals
     ("$4.69"), not the "squashed" flyer style — see base_scraper.py's
     parse_standard_price().

On sale dates: Seasons *does* show a "PRICES VALID 8/2/26 - 8/7/26" date
banner, but it's baked into a flyer image (not real text), so pulling it
out automatically would need image OCR, not simple scraping. Nutmeg and
Kosher West don't show a date banner on their specials page at all. To
keep this honest rather than guessing, every deal from this platform is
tagged with the date it was scraped, and a valid-through date 7 days
later (a standard weekly-sale assumption), clearly marked as
"estimated" so nobody mistakes it for a confirmed store-published date.
"""

import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.base_scraper import (
    parse_standard_price, guess_category, clean_item_name, current_wed_to_tue_window,
)
from db.database import get_connection, init_db, insert_deal

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"


def _extract_items_from_source(page_source) -> list[tuple[str, str, str]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page_source, "html.parser")
    items = []
    for card in soup.select("a.product-item-link"):
        name_el = card.select_one(".product-item-title")
        price_el = card.select_one(".product-item-price")
        old_el = card.select_one(".product-item-old-price")
        name = name_el.get_text(strip=True) if name_el else None
        price_text = price_el.get_text(strip=True) if price_el else ""
        old_text = old_el.get_text(strip=True) if old_el else ""
        if name:
            items.append((name, price_text, old_text))
    return items


def get_all_pages_live(domain: str, location_slug: str, max_pages: int = 10, zip_code: str = "08701"):
    """Fetch every page of /category/specials via a headless browser.

    Two important behaviors, found the hard way while double-checking this
    scraper's real output against the live site on 2026-08-06:

    1. LOCATION MUST BE CONFIRMED, NOT JUST GUESSED FROM THE URL. This
       platform tracks which store you're shopping (Lakewood vs. Queens vs.
       Lawrence, etc.) with a cookie set during a ZIP-code confirmation
       flow on the homepage. Navigating straight to a URL like
       "/Lakewood-NJ/category/specials" can silently serve a DIFFERENT
       location's inventory if that cookie was never set — the page loads
       fine, shows no error, and just quietly shows the wrong store's
       deals. So this function first visits the homepage, accepts the
       cookie banner, types the ZIP code into the store locator, and
       confirms Lakewood before going anywhere near the specials page.
    2. PAGES DO NOT RELIABLY ACCUMULATE. Earlier code assumed each page
       click added its items to the ones already on the page (so reading
       the DOM once at the end would have everything). Direct testing
       showed this is NOT reliable — clicking a page number sometimes
       fully replaces the item list instead of appending to it. To be
       safe, this function now reads and stores the item list after
       EVERY page click, then de-duplicates the combined set at the end,
       instead of trusting one final read.

    Returns a de-duplicated list of (name, price_text, old_price_text)
    tuples, or None if live fetching isn't possible in this environment.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        import time
    except ImportError as e:
        print(f"[grocery_platform] Live mode unavailable, missing package: {e}")
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    driver = None
    try:
        driver = webdriver.Chrome(options=options)

        # Step 1: pin the location to Lakewood via the ZIP-confirmation
        # flow on the homepage, BEFORE trying to read any deals.
        driver.get(f"https://{domain}/")
        time.sleep(2)
        try:
            accept_btn = driver.find_element(By.XPATH, "//*[self::button or self::a][contains(translate(text(),'ACEPT','acept'),'accept')]")
            accept_btn.click()
            time.sleep(1)
        except Exception:
            pass  # no cookie banner present, fine
        try:
            zip_input = driver.find_element(By.XPATH, "//input[@type='text' or @type='tel' or @type='search']")
            zip_input.send_keys(zip_code)
            go_btn = driver.find_element(By.XPATH, "//button[not(@type='text')]")
            go_btn.click()
            time.sleep(2)
        except Exception as e:
            print(f"[grocery_platform] Could not confirm ZIP/location automatically ({e}); "
                  f"falling back to direct URL, which may serve the wrong store's data.")

        # Step 2: now that the location cookie is set, go to specials.
        url = f"https://{domain}/{location_slug}/category/specials"
        driver.get(url)
        driver.implicitly_wait(5)
        time.sleep(2)

        all_items = list(_extract_items_from_source(driver.page_source))

        for page_num in range(2, max_pages + 1):
            try:
                # The page-number control is plain visible text ("2", "3", ...)
                # — find it by exact text rather than a CSS class, since we
                # don't have a stable class name for it and the surrounding
                # markup differs slightly between this platform's sites.
                page_link = driver.find_element(
                    By.XPATH, f"//*[self::a or self::button][normalize-space(text())='{page_num}']"
                )
            except Exception:
                break  # no more page numbers — we've reached the end

            page_link.click()
            time.sleep(2)
            # Read after EVERY click and accumulate — do not assume the
            # DOM keeps earlier pages' items (see docstring above).
            all_items.extend(_extract_items_from_source(driver.page_source))

        # De-duplicate (this platform sometimes renders the same card twice,
        # e.g. once for a mobile layout, once for desktop, or repeats an
        # item across two page reads).
        seen = set()
        deduped = []
        for item in all_items:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped
    except Exception as e:
        print(f"[grocery_platform] Live fetch for {domain} failed ({e}).")
        return None
    finally:
        if driver:
            driver.quit()


def get_page_cached(store_slug: str) -> list[tuple[str, str, str]]:
    """Load the cached real-data snapshot captured during development.

    PLAIN-ENGLISH NOTE (found 2026-08-06): this platform tracks which store
    location you're shopping via a cookie set during a ZIP-code confirmation
    flow, not just the URL. Visiting "/Lakewood-NJ/..." directly can silently
    serve a *different* location's inventory (e.g. Queens) if that cookie
    was never set in this session. Earlier snapshots were captured before
    this was understood and may have mixed in wrong-location data. Snapshots
    named "*_specials.txt" were captured AFTER explicitly confirming the
    Lakewood store via the ZIP flow (08701) and are the trustworthy ones —
    prefer those over any older "*_page1.txt" file for the same store.
    """
    # Sort so the most-recently-dated snapshot (YYYY-MM-DD in the filename)
    # comes first — filenames sort correctly by date lexicographically, so
    # this just means newest-first. (Found 2026-08-10: this used to pick
    # matches[0] off an ascending sort, which silently always loaded the
    # OLDEST snapshot on disk instead of the newest — a real bug, fixed
    # here rather than routing around it, same spirit as aldi_scraper.py
    # always using the newest aldi_*_flipp.json by filename.)
    matches = sorted(SAMPLE_DATA_DIR.glob(f"{store_slug}_*_specials.txt"), reverse=True)
    if not matches:
        matches = sorted(SAMPLE_DATA_DIR.glob(f"{store_slug}_*_page1.txt"), reverse=True)
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


def scrape_store(
    domain: str,
    location_slug: str,
    store_slug: str,
    max_pages: int = 10,
) -> list[dict]:
    """Scrape all specials pages for one store on this shared platform."""
    is_live = False

    live_items = get_all_pages_live(domain, location_slug, max_pages)
    if live_items is not None:
        is_live = True
        all_items = live_items
    else:
        print(f"[{store_slug}] Using cached snapshot (dev fallback).")
        all_items = get_page_cached(store_slug)

    mode = "LIVE" if is_live else "CACHED SNAPSHOT (dev fallback)"
    print(f"[{store_slug}] Source mode: {mode}")

    # De-duplicate — this platform sometimes renders the same card twice
    # (once for desktop layout, once for mobile), which showed up during
    # testing as exact-duplicate rows.
    seen = set()
    deduped = []
    for name, price_text, old_text in all_items:
        key = (name, price_text, old_text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((name, price_text, old_text))

    # Real weekly sale cycle for this platform (confirmed by the founder,
    # who shops there): Wednesday morning through Tuesday night — see
    # base_scraper.py's current_wed_to_tue_window() for why this replaced
    # a generic "7 days from scrape date" estimate.
    date_from, date_to = current_wed_to_tue_window()

    deals = []
    for name, price_text, old_text in deduped:
        sale_price, unit = parse_standard_price(price_text)
        if sale_price is None:
            continue
        original_price, _ = parse_standard_price(old_text) if old_text else (None, None)
        clean_name = clean_item_name(name)
        deals.append(
            {
                "store_slug": store_slug,
                "item_name": clean_name,
                "original_price": original_price,
                "sale_price": sale_price,
                "unit": unit,
                "category": guess_category(clean_name),
                "date_valid_from": date_from,
                "date_valid_to": date_to,
                "raw_text": f"{name} | {price_text} | {old_text}",
            }
        )
    return deals


def run(
    domain: str,
    location_slug: str,
    store_slug: str,
    save_to_db: bool = True,
    limit_preview: int = 8,
) -> list[dict]:
    deals = scrape_store(domain, location_slug, store_slug)
    print(f"[{store_slug}] Parsed {len(deals)} candidate deals.")
    print(
        f"[{store_slug}] NOTE: this store doesn't publish an exact "
        f"'valid through' date online, so dates shown are an ESTIMATED "
        f"Wednesday-to-Tuesday sale week "
        f"({deals[0]['date_valid_from'] if deals else 'n/a'} to "
        f"{deals[0]['date_valid_to'] if deals else 'n/a'})."
    )

    print(f"\nFirst {min(limit_preview, len(deals))} scraped items:")
    for d in deals[:limit_preview]:
        price_str = f"${d['sale_price']:.2f}"
        unit_str = f"/{d['unit']}" if d["unit"] else ""
        print(f"  - [{d['category']:<7}] {d['item_name']:<50} {price_str}{unit_str}")

    if save_to_db:
        init_db()
        with get_connection() as conn:
            for d in deals:
                insert_deal(conn, d)
        print(f"\n[{store_slug}] Saved {len(deals)} deals to the database.")

    return deals
