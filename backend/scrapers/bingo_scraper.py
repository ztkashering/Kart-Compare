"""
bingo_scraper.py — Bingo Wholesale (Lakewood, NJ).

PLAIN-ENGLISH NOTE ON WHAT I FOUND: Bingo's "Weekly Deals" page
(bingowholesale.com/weeklydeals) is a Wix website with a "PDF Viewer Pro"
widget embedded in it — so, like Gourmet Glatt, their flyer is a PDF, not
a text list. This scraper follows the same pattern: use a real/headless
browser to load the page, find the PDF inside that widget, download it,
and read its text with PyMuPDF.

HOWEVER — as of when this was built, checking the live page showed the
widget rendered completely blank. That most likely means Bingo simply
hasn't uploaded a current flyer to it (rather than the scraper being
broken). Because there's no real flyer to capture right now, this
scraper has no cached "known-good" sample to fall back on the way
Gourmet Glatt's does — I'm not going to invent fake grocery items. It
will report honestly that zero deals were found until Bingo posts a new
flyer, at which point this same code should pick it up automatically
(rerun it any time to check).
"""

import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.gourmet_glatt_scraper import parse_deals as parse_flyer_deals
from db.database import get_connection, init_db, insert_deal

STORE_SLUG = "bingo"
WEEKLY_DEALS_URL = "https://www.bingowholesale.com/weeklydeals"


def find_pdf_url_live() -> str | None:
    """Load the weekly deals page and look inside the 'PDF Viewer Pro'
    widget for an actual PDF link. Returns None if no browser is
    available, or if the widget has no flyer loaded."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError as e:
        print(f"[bingo] Live mode unavailable, missing package: {e}")
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(WEEKLY_DEALS_URL)
        driver.implicitly_wait(5)

        pdf_url = None
        for entry in driver.execute_script(
            "return performance.getEntriesByType('resource').map(e => e.name)"
        ):
            if entry.lower().endswith(".pdf"):
                pdf_url = entry
                break

        if not pdf_url:
            print(
                "[bingo] No PDF found in the weekly-deals widget — "
                "the store likely hasn't posted a current flyer."
            )
        return pdf_url
    except Exception as e:
        print(f"[bingo] Live fetch failed ({e}).")
        return None
    finally:
        if driver:
            driver.quit()


def run(save_to_db: bool = True, limit_preview: int = 8) -> list[dict]:
    try:
        import requests
        import fitz  # PyMuPDF
    except ImportError as e:
        print(f"[bingo] Missing package for PDF extraction: {e}")
        return []

    pdf_url = find_pdf_url_live()
    deals = []

    if pdf_url:
        try:
            resp = requests.get(pdf_url, timeout=20)
            resp.raise_for_status()
            doc = fitz.open(stream=resp.content, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            deals = parse_flyer_deals(text)
            for d in deals:
                d["store_slug"] = STORE_SLUG
        except Exception as e:
            print(f"[bingo] Failed to download/parse PDF: {e}")

    print(f"[{STORE_SLUG}] Parsed {len(deals)} candidate deals.")
    if not deals:
        print(
            f"[{STORE_SLUG}] No active flyer found right now — this is a "
            f"live check of the real site, not a bug. Re-run this scraper "
            f"once Bingo posts a new weekly flyer to bingowholesale.com/weeklydeals."
        )

    print(f"\nFirst {min(limit_preview, len(deals))} scraped items:")
    for d in deals[:limit_preview]:
        price_str = f"${d['sale_price']:.2f}"
        unit_str = f"/{d['unit']}" if d.get("unit") else ""
        print(f"  - [{d['category']:<7}] {d['item_name']:<45} {price_str}{unit_str}")

    if save_to_db:
        init_db()
        with get_connection() as conn:
            for d in deals:
                insert_deal(conn, d)
        print(f"\n[{STORE_SLUG}] Saved {len(deals)} deals to the database.")

    return deals


if __name__ == "__main__":
    run()
