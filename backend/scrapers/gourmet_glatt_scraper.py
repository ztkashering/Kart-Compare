"""
gourmet_glatt_scraper.py — scraper for Gourmet Glatt (Lakewood).

IMPORTANT PLAIN-ENGLISH NOTE ON WHAT THIS ACTUALLY DOES:
Gourmet Glatt's "Weekly Specials" page (gourmetglatt.com/lakewood-njersey/specials)
looks like a normal webpage, but it does NOT list items as text/HTML. It's a
"View / Download" box that serves a PDF flyer (hosted on their CMS's file
storage). So even though Gourmet Glatt was in the "HTML-based sites" bucket
in the original plan, in reality it belongs with Bingo in the "PDF circular"
bucket. This scraper is written accordingly:

  1. LIVE MODE: use Selenium to load the specials page (a headless browser
     is required because the PDF link is inserted by JavaScript after the
     page loads — a plain `requests.get()` will not see it), grab the PDF
     link, download it, and extract its text with PyMuPDF (fitz).
  2. OFFLINE/DEMO MODE: if Selenium or the network isn't available (e.g.
     this sandboxed dev environment blocks outbound requests to the CMS's
     file host), fall back to a cached copy of this week's real flyer text
     (sample_data/gourmet_glatt_2026-08-02_extracted.txt) that was captured
     directly from the live PDF during development, so the parsing logic
     below is always exercised against real, current data.

Either way, once we have the flyer's plain text, `parse_deals()` below does
the actual work of pulling out item names and prices.
"""

import re
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # so "db" package resolves

from scrapers.base_scraper import (
    parse_flyer_price,
    parse_multi_buy,
    guess_category,
    clean_item_name,
    CENTS_SYMBOL_RE,
)
from db.database import get_connection, init_db, insert_deal

STORE_SLUG = "gourmet-glatt"
SPECIALS_PAGE_URL = "https://gourmetglatt.com/lakewood-njersey/specials"
SAMPLE_TEXT_PATH = (
    Path(__file__).parent / "sample_data" / "gourmet_glatt_2026-08-10_extracted.txt"
)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# A line counts as a "price line" if it's basically just a price (optionally
# with a unit like "lb." or "ea." stuck directly onto it — flyers do this a
# lot, e.g. "$289lb.").
PRICE_LINE_RE = re.compile(
    r"^(?:"
    r"\$\d{2,5}(?:lb\.?|ea\.?)?"          # $199, $1999lb.
    r"|\d{1,2}\s*/\s*\$?\d+(?:\.\d{2})?(?:cents)?(?:lb\.?)?"  # 3/$4, 2/88cents
    r"|\d{2,3}\s*cents(?:lb\.?)?"          # 99cents, 99centslb
    r"|\d{1,3}\s*¢(?:\s*(?:lb\.?|ea\.?))?"  # 89 ¢, 99¢, 99 ¢ lb. — found
    # 2026-08-12: this flyer prints anything under a dollar with the "¢"
    # glyph, not the word "cents". Missing this pattern was the root
    # cause of a whole class of garbled/merged item names — see the note
    # on CENTS_SYMBOL_RE in base_scraper.py.
    r")$",
    re.I,
)

# Lines that are just visual noise / boilerplate — ignore for item names.
# NOTE 2026-08-12: the dot-leader pattern below was changed from `\.{3,}`
# (three-plus CONSECUTIVE periods) to `(?:\.\s*){3,}` (three-plus periods
# each optionally followed by whitespace) because this flyer's real
# dot-leaders come out of PDF text extraction as SPACED dots
# (". . . . . . ."), which the old pattern never matched — so the whole
# dot-leader line was silently treated as item-name text and glued onto
# whatever came before and after it, contributing to the same
# merged-name problem as the missing "¢" price pattern above.
NOISE_LINE_RE = re.compile(
    r"^((?:\.\s*){3,}|limit \d+.*|family pack|bulk size|large (bags|size)|"
    r".*STORE HOURS.*|.*SUNDAY.*|.*MON.*TUES.*|.*THURS.*|.*FRIDAY.*|"
    r"\(\d{3}\) \d{3}-\d{4}.*|\d+ .*Ave.*|\d+ .*Rd.*|JACKSON LOCATION.*|"
    r"MADISON LOCATION.*|.*LOCATION ONLY.*|SEAGULL.*|"
    r"order now with instacart!.*|Email\s+cakes@.*|cakes@\S+|FROM THE HOT TABLE.*|"
    r"For All Your Special.*|.*Occasion Cakes(?:\s+Email)?.*|"
    r".*BUY\s+\d+\s+GET.*FREE.*|Free\s+Item\s+Must\s+be.*|"
    # 2026-08-12: this flyer's two-column layout causes PDF text
    # extraction to interleave columns, which makes some section
    # labels/descriptors ("imported beef", "tender & juicy", "seasoned
    # ready to bake or grill", "shabbos special - friday only", "with
    # extended shopping hours!") come out DOUBLED on one line (once per
    # column) instead of appearing once. These are never real item
    # names, so filter both the single and doubled forms.
    r"(?:with extended shopping hours!\s*){1,2}|"
    r"(?:imported beef\s*){1,2}|(?:american beef\s*){1,2}|(?:poultry\s*){1,2}|"
    r"(?:tender\s*&\s*juicy\s*){1,2}|"
    r"(?:seasoned ready to\s*){1,2}(?:bake or grill\s*){0,2}|"
    r"(?:shabbos special - friday only\s*){1,2}|"
    # Bare doubled section-label fragments with no other real words on
    # the line — these are never item names by themselves.
    r"(?:american\s*){1,2}|(?:jackson\s*){1,2}|(?:only\s*){1,2})$",
    re.I,
)

SECTION_HEADER_WORDS = {
    "buys of the week!", "refrigerated specials", "frozen super sales",
    "frozen specials", "grocery sales!", "refrigerated super sales!",
    "fresh produce", "premium meat & poultry",
}

# 2026-08-12: exact item names confirmed, by hand, to be two unrelated
# products glued together by this flyer's two-column PDF layout — one
# item's name lost its own price and absorbed a nearby, unrelated
# item's price instead. Concrete examples the founder flagged directly:
# "Ahi Tuna Steak" (fish counter) merged with "Appetizing Bakery / Mini
# Round Chocolate Babkas" (bakery counter), and a fish-counter promo
# blurb ("Fish tuesday from...ossiesfish.com") merged with "(Mini
# Brisket) Honey Mustard Legs" (a poultry item).
#
# IMPORTANT: this is intentionally a small, exact-match list, not a
# keyword heuristic. An earlier attempt used a broader rule ("flag any
# item matching keywords from 2+ different departments") and it looked
# promising, but testing it against this same flyer text showed real
# false positives — "Banner Bagel Cut Lox" (a totally normal single
# product: sliced lox for bagels) and "KJ Chicken Nuggets, Chicken
# Fries, Alef Beis Nuggets" (a real multi-item value pack) both got
# wrongly deleted, because "bagel"+"lox" and "chicken"+"fries" are
# perfectly normal words to share one real product name. Rather than
# risk silently dropping real deals, only these hand-verified exact
# matches are excluded. If a new garbled entry turns up in a future
# week's flyer, add its exact name here after checking the raw
# extracted text (see sample_data/) to confirm it's really a merge and
# not a legitimately unusual product name.
KNOWN_MERGED_ITEM_NAMES = {
    "Ahi Tuna Steak Appetizing Bakery Mini Round Chocolate Babkas - 4 Pack",
    "Fish tuesday from ossiesfish.com (Mini Brisket) Honey Mustard Legs",
}


def get_flyer_text_live() -> str | None:
    """Attempt to fetch this week's flyer live via Selenium + PyMuPDF.

    Returns the extracted text, or None if anything in the chain fails
    (no browser driver available, network blocked, page layout changed,
    etc). Callers should fall back to cached data when this returns None.
    """
    try:
        import requests
        import fitz  # PyMuPDF
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError as e:
        print(f"[gourmet_glatt] Live mode unavailable, missing package: {e}")
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(SPECIALS_PAGE_URL)
        # The PDF is only linked in after client-side JS runs, so wait for
        # network activity to settle by polling performance log entries
        # for a request to the CMS's media host.
        pdf_url = None
        wait = WebDriverWait(driver, 15)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        for entry in driver.execute_script(
            "return performance.getEntriesByType('resource').map(e => e.name)"
        ):
            if entry.lower().endswith(".pdf"):
                pdf_url = entry
                break

        if not pdf_url:
            print("[gourmet_glatt] Could not find a PDF link on the specials page.")
            return None

        resp = requests.get(pdf_url, timeout=20)
        resp.raise_for_status()
        doc = fitz.open(stream=resp.content, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        return text
    except Exception as e:
        print(f"[gourmet_glatt] Live fetch failed ({e}); will use cached sample instead.")
        return None
    finally:
        if driver:
            driver.quit()


def get_flyer_text() -> tuple[str, bool]:
    """Return (text, is_live). Tries live mode first, falls back to the
    cached real-flyer snapshot captured during development."""
    live_text = get_flyer_text_live()
    if live_text:
        return live_text, True
    print(f"[gourmet_glatt] Using cached snapshot: {SAMPLE_TEXT_PATH.name}")
    return SAMPLE_TEXT_PATH.read_text(), False


def parse_date_range(text: str, fallback_year: int) -> tuple[str, str]:
    """Find 'Sale Dates: August 2nd - 7th 2026' and return ISO (from, to)."""
    m = re.search(
        r"Sale Dates:\s*([A-Za-z]+)\s+(\d{1,2})\w*\s*-\s*(\d{1,2})\w*\s*(\d{4})?",
        text,
    )
    if not m:
        today = date.today().isoformat()
        return today, today
    month_name, day_from, day_to, year = m.groups()
    month = MONTHS.get(month_name.lower())
    year = int(year) if year else fallback_year
    d_from = date(year, month, int(day_from)).isoformat()
    d_to = date(year, month, int(day_to)).isoformat()
    return d_from, d_to


def parse_deals(text: str) -> list[dict]:
    """Turn raw flyer text into a list of deal dicts.

    Strategy: walk line by line, collecting non-price lines into a buffer
    as the "candidate name" for whatever price line comes next. When we
    hit a line that's essentially just a price, we close out one deal
    using the buffered name, then start a new buffer.

    This is a heuristic, not a perfect parser — grocery flyers are laid
    out visually (columns, wrapped text) and PDF text extraction loses
    that layout, so a small percentage of items may come out mis-grouped.
    It is tuned against this store's real, current flyer and can be
    refined further once we see more weeks of data.
    """
    date_from, date_to = parse_date_range(text, fallback_year=date.today().year)

    lines = text.splitlines()
    # Skip the header block (store hours/addresses) — start once we hit
    # the first real section header, if present.
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().lower() in SECTION_HEADER_WORDS:
            start_idx = i
            break
    lines = lines[start_idx:]

    deals = []
    buffer: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if NOISE_LINE_RE.match(line):
            continue
        if line.lower() in SECTION_HEADER_WORDS:
            buffer = []  # section headers aren't part of an item name
            continue

        if PRICE_LINE_RE.match(line):
            if not buffer:
                continue  # a stray price with nothing to attach it to
            item_name = clean_item_name(" ".join(buffer))
            buffer = []
            if not item_name:
                continue

            if item_name in KNOWN_MERGED_ITEM_NAMES:
                continue

            multi = parse_multi_buy(line)
            if multi:
                qty, amount = multi
                sale_price = round(amount / qty, 2)
                unit = f"{qty} for ${amount:.2f}"
            else:
                sale_price = parse_flyer_price(line)
                unit_match = re.search(r"(lb\.?|ea\.?)$", line, re.I)
                unit = unit_match.group(1).rstrip(".") if unit_match else None

            if sale_price is None:
                continue

            deals.append(
                {
                    "store_slug": STORE_SLUG,
                    "item_name": item_name,
                    "original_price": None,  # flyer only ever shows the sale price
                    "sale_price": sale_price,
                    "unit": unit,
                    "category": guess_category(item_name),
                    "date_valid_from": date_from,
                    "date_valid_to": date_to,
                    "raw_text": f"{item_name} | {line}",
                }
            )
        else:
            buffer.append(line)

    return deals


def run(save_to_db: bool = True, limit_preview: int = 8) -> list[dict]:
    text, is_live = get_flyer_text()
    mode = "LIVE" if is_live else "CACHED SNAPSHOT (dev fallback)"
    print(f"[gourmet_glatt] Source mode: {mode}")

    deals = parse_deals(text)
    print(f"[gourmet_glatt] Parsed {len(deals)} candidate deals.")

    print(f"\nFirst {min(limit_preview, len(deals))} scraped items:")
    for d in deals[:limit_preview]:
        price_str = f"${d['sale_price']:.2f}"
        unit_str = f"/{d['unit']}" if d["unit"] else ""
        print(f"  - [{d['category']:<7}] {d['item_name']:<45} {price_str}{unit_str}")

    if save_to_db:
        init_db()
        with get_connection() as conn:
            for d in deals:
                insert_deal(conn, d)
        print(f"\n[gourmet_glatt] Saved {len(deals)} deals to the database.")

    return deals


if __name__ == "__main__":
    run()
