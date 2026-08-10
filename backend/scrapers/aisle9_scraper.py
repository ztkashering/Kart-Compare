"""
aisle9_scraper.py — Aisle 9 (951 Madison Ave, Lakewood, NJ).

STATUS AS OF 2026-08-10: real, verified deals — but a SMALL, PARTIAL set,
not a comprehensive weekly specials list like the other stores. Read on
for why, and what to do about it on the next rescrape.

BACKGROUND: Aisle 9 runs on the "My Cloud Grocer" online-ordering
platform. Its product-card HTML is the same shape grocery_platform_scraper.py
already parses for Seasons/Nutmeg/Kosher West (`a.product-item-link` /
`.product-item-title` / `.product-item-price` / `.product-item-old-price`),
plus one extra marker this platform has that those don't:
`.product-item-special-lbl` — a "Special" badge that appears ONLY on
genuinely marked-down cards, not every card. Confirmed real by checking
the actual rendered DOM, not guessed.

THE BLOCKER (still not solved as of 2026-08-10): Aisle 9's full catalog —
including the dedicated `/lakewood/category/specials` page — returns
zero products from their own `/api/AjaxFilter/JsonProductsList` endpoint
until a delivery or pickup time slot is selected in their checkout flow.
That step was not completed (it risked either fabricating data or
accidentally taking a real action on the founder's behalf), so the full
specials category still isn't reachable.

WHAT DID WORK: the homepage (`/lakewood`) shows a "Featured Products"
carousel that is NOT gated the same way. Real product cards with real
prices render there without a delivery slot. Checked all 24 cards on
2026-08-10 and found exactly 3 carrying the genuine "Special" badge —
those 3 are what's saved below. This is a curated homepage sample, not
Aisle 9's full weekly sale — there are certainly more real specials that
just aren't reachable yet.

PRICE FORMAT — IMPORTANT, this looks backwards at first glance but isn't:
`.product-item-price` shows a MULTI-BUY offer ("12 for $16.99"), and
`.product-item-old-price` shows the REGULAR SINGLE-UNIT price ("$1.49").
Despite the CSS class name "old-price", this is NOT a was/now pair in
the usual sense — it's "buy this many for this total" vs. "the regular
each-price if you don't." Verified this reading is right by checking the
unit math on all 3 items found: in every case, the multi-buy price is
genuinely lower per unit than the regular price (Gefen Soup: $16.99/12 =
$1.42 vs. $1.49 regular; Oat Bar: $5.00/5 = $1.00 vs. $2.69 regular; Tuna:
$5.00/3 = $1.67 vs. $1.99 regular) — a real discount either way, so
original_price = the "old-price" field, sale_price = the parsed per-unit
value of the "price" field. base_scraper.py's parse_standard_price()
already handles "N for $X" strings correctly, so it's reused as-is here.

DATES: no valid-through date is shown anywhere on Aisle 9's site for
these specials (checked the homepage card, the individual product page,
and the ProductDetailsJSON API response — none carry one). Same
situation as Nutmeg/Kosher West/Kosher Village, so — same treatment —
deals are tagged with the real Wednesday-to-Tuesday sale week these
Lakewood kosher stores run on, clearly marked "estimated" rather than
a store-confirmed date.

NEXT RESCRAPE: check backend/scrapers/sample_data/aisle9_*_specials.txt
for the newest snapshot. To refresh it, open a live browser to
https://aisle9market.com/lakewood, read every `a.product-item-link` card
on the homepage's Featured Products carousel, keep ONLY the ones with a
`.product-item-special-lbl` child, and save name / bulk price / regular
price as new pipe-delimited lines. If someone manages to get past the
delivery/pickup gate and `/lakewood/category/specials` populates for
real, that's the better, more complete source — switch to it and update
this docstring.
"""

import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.base_scraper import (
    parse_standard_price, guess_category, clean_item_name, current_wed_to_tue_window,
)
from db.database import get_connection, init_db, insert_deal

STORE_SLUG = "aisle-9"
SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"


def _latest_sample_path() -> Path | None:
    matches = sorted(SAMPLE_DATA_DIR.glob("aisle9_*_specials.txt"))
    return matches[-1] if matches else None


def parse_deals(raw_text: str) -> list[dict]:
    date_from, date_to = current_wed_to_tue_window()

    deals = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|||")
        if len(parts) != 3:
            continue
        raw_name, bulk_text, regular_text = parts
        name = clean_item_name(raw_name)
        if not name:
            continue

        # "old-price" field = the regular single-unit price on this
        # platform (see module docstring for why the CSS class name is
        # misleading).
        original_price, _ = parse_standard_price(regular_text.strip())
        # "price" field = the multi-buy offer, e.g. "12 for $16.99" —
        # parse_standard_price() already converts that into a real
        # per-unit dollar amount plus a human-readable unit label.
        sale_price, unit = parse_standard_price(bulk_text.strip())

        if sale_price is None:
            continue
        if original_price is None:
            original_price = sale_price  # fallback: shouldn't happen given the sample format

        deals.append(
            {
                "store_slug": STORE_SLUG,
                "item_name": name,
                "original_price": original_price,
                "sale_price": sale_price,
                "unit": unit,
                "category": guess_category(name),
                "date_valid_from": date_from,
                "date_valid_to": date_to,
                "raw_text": line,
            }
        )
    return deals


def run(save_to_db: bool = True, limit_preview: int = 8) -> list[dict]:
    sample_path = _latest_sample_path()
    if sample_path is None:
        print(
            f"[{STORE_SLUG}] No sample data file found "
            f"(backend/scrapers/sample_data/aisle9_*_specials.txt) — "
            f"returning 0 deals rather than guessing."
        )
        return []

    print(f"[{STORE_SLUG}] Source mode: CACHED SNAPSHOT ({sample_path.name})")
    print(
        f"[{STORE_SLUG}] NOTE: this is a small, partial sample from Aisle 9's "
        f"homepage 'Special' badges, not their full weekly specials — the "
        f"complete specials category page is gated behind a delivery/pickup "
        f"selection step that hasn't been solved yet. See this file's "
        f"docstring for details."
    )

    deals = parse_deals(sample_path.read_text())
    print(f"[{STORE_SLUG}] Parsed {len(deals)} candidate deals.")
    print(
        f"[{STORE_SLUG}] NOTE: no valid-through date is published anywhere on "
        f"Aisle 9's site for these, so dates shown are an ESTIMATED "
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
