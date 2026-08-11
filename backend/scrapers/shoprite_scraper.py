"""
shoprite_scraper.py — ShopRite (Brick, NJ area).

SOURCE, 2026-08-10: the founder uploaded ShopRite's own printed weekly
circular PDF directly ("104_Region1_stitched...06Aug2026...pdf" — the
region-wide flyer covering ShopRite stores in Monmouth and Ocean County,
NJ, which includes Brick). ShopRite's flyer platform (RedPepper) only
serves flyer *images*, never structured price data (confirmed earlier in
this project — see README's "still pending" history for this store), so
this is genuinely the only way to get real ShopRite prices into the site:
a human sends the actual flyer, and this scraper reads what was manually
verified off it page by page. That verified read is saved as pipe-
delimited lines in sample_data/shoprite_*_flyer.txt:
    item_name|||sale_price|||original_price|||unit|||date_from|||date_to
This is NOT a live/automatic scrape — there's no reliable automatic
source for this store yet. Re-running this scraper just re-parses
whatever's in the newest sample file. To refresh: get a new flyer PDF (or
photos) from the founder, read it page by page, and add verified lines
following the same rule as every other store in this project — only a
line with a clearly-stated regular price AND a real "SAVE $X" amount
becomes a deal, never a guess.

KOSHER POLICY — same rule as Aldi (see aldi_scraper.py and this store's
own STORE_META note in build_site.py), applied even more strictly here
since fresh flyer items don't carry any hechsher info at all:
  ONLY Produce is included. No meat, poultry, fish/seafood, dairy,
  bakery, frozen, deli, candy/snacks, household, or health & beauty —
  no exceptions, regardless of brand. A fresh, whole, uncut fruit or
  vegetable needs no certification to be kosher; virtually everything
  else on a ShopRite flyer does, and this site has no way to check for
  an actual hechsher symbol on a package from a flyer page. (An earlier
  draft of this pass also considered including a fresh salmon fillet —
  fish don't require ritual slaughter, only fins+scales — but that's
  inconsistent with the Aldi precedent this project already committed
  to ("this replaced an earlier 'salmon is OK' rule; salmon is excluded
  now too"), so it was left out here too, for the same reason.)

PRICE-VERIFICATION RULE (same as every other store here): this flyer
shows plenty of items at a flat "sale" price with NO stated regular
price anywhere nearby — those were skipped, not guessed. Only items
carrying an explicit "SAVE $X.XX" (or "SAVE $X.XX/LB") tag next to the
price were kept, since that's the flyer's own confirmation of a real
discount amount, letting original_price = sale_price + save_amount be
computed with certainty rather than assumed.

WHAT WAS ACTUALLY ON THE FLYER (2026-08-09 through 2026-08-15, 12 pages,
read in full): out of ~120 distinct items across produce, meat, dairy,
frozen, snacks, beverages, pantry, deli, and household categories, only
5 were BOTH (a) fresh whole produce and (b) carrying a verified "SAVE"
discount tag: Bowl & Basket Jumbo Avocados, Red & Black Seedless Grapes
(a "3 Days Only" Thu 8/13-Sat 8/15 special), Blueberries (also 3-Days-
Only), Whole Seedless Watermelon, and Sweet Cantaloupes. Everything else
on the flyer was either not produce (meat, dairy, packaged snacks,
household goods, etc. — excluded by the kosher policy above regardless
of price) or produce with no stated regular price to compare against
(fresh corn, cucumbers, peppers, plums, papayas, pineapples, broccoli,
eggplant, potatoes, carrots, celery, organic grapes/peaches/nectarines,
figs, limes — real items, just not verifiable as an actual markdown from
what the flyer shows, so left out rather than guessed).
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.base_scraper import clean_item_name, guess_category, CATEGORY_KEYWORDS
from db.database import get_connection, init_db, insert_deal

STORE_SLUG = "shoprite"
SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"

# Only these categories are ever allowed onto the ShopRite page — see the
# KOSHER POLICY note above. Produce only (even Aldi allows Eggs/Pantry/
# Beverages too; this store is stricter since nothing here has been
# checked against an actual package hechsher).
ALLOWED_CATEGORIES = {"Produce"}

# Hard safety net, same pattern as aldi_scraper.py: independently checked
# against the full Meat & Deli keyword list regardless of anything else,
# so a future bad line in the sample file can never sneak meat/fish onto
# this page.
_MEAT_DELI_KEYWORDS = CATEGORY_KEYWORDS["Meat & Deli"]


def _is_meat_or_deli(name_lower: str) -> bool:
    return any(kw in name_lower for kw in _MEAT_DELI_KEYWORDS)


def _latest_sample_path() -> Path | None:
    matches = sorted(SAMPLE_DATA_DIR.glob("shoprite_*_flyer.txt"))
    return matches[-1] if matches else None


def parse_deals(raw_text: str) -> list[dict]:
    deals = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|||")
        if len(parts) != 6:
            continue
        raw_name, sale_text, orig_text, unit_text, date_from, date_to = parts
        name = clean_item_name(raw_name)
        if not name:
            continue

        try:
            sale_price = float(sale_text.strip())
            original_price = float(orig_text.strip())
        except ValueError:
            continue  # can't confirm real numbers, skip rather than guess

        if not (sale_price < original_price):
            continue  # not an actual discount, skip rather than guess

        name_lower = name.lower()
        if _is_meat_or_deli(name_lower):
            continue  # hard safety net, see module docstring

        category = guess_category(name)
        if category not in ALLOWED_CATEGORIES:
            continue  # kosher policy — Produce only, no exceptions

        unit = unit_text.strip() or None

        deals.append(
            {
                "store_slug": STORE_SLUG,
                "item_name": name,
                "original_price": original_price,
                "sale_price": sale_price,
                "unit": unit,
                "category": category,
                "date_valid_from": date_from.strip(),
                "date_valid_to": date_to.strip(),
                "raw_text": line,
            }
        )
    return deals


def run(save_to_db: bool = True, limit_preview: int = 8) -> list[dict]:
    sample_path = _latest_sample_path()
    if sample_path is None:
        print(
            f"[{STORE_SLUG}] No sample data file found "
            f"(backend/scrapers/sample_data/shoprite_*_flyer.txt) — "
            f"returning 0 deals rather than guessing."
        )
        return []

    print(f"[{STORE_SLUG}] Source mode: CACHED FLYER READ ({sample_path.name})")
    print(
        f"[{STORE_SLUG}] KOSHER POLICY: Produce only, no exceptions. See "
        f"this file's docstring for why (same rule as Aldi)."
    )

    deals = parse_deals(sample_path.read_text())
    print(f"[{STORE_SLUG}] Parsed {len(deals)} verified deals.")

    print(f"\nFirst {min(limit_preview, len(deals))} scraped items:")
    for d in deals[:limit_preview]:
        print(
            f"  - [{d['category']:<7}] {d['item_name']:<40} "
            f"${d['sale_price']:.2f} (was ${d['original_price']:.2f}) "
            f"{d['date_valid_from']} to {d['date_valid_to']}"
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
