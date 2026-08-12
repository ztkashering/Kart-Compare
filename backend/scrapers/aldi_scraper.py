"""
aldi_scraper.py — Aldi (Lakewood-area store: ALDI, 86 NJ Route 70, Toms
River, NJ 08755 — the closest real Aldi to Lakewood).

PLAIN-ENGLISH HISTORY (for whoever reads this later):
  Pass 1 scraped the small homepage preview only (4-8 items/section) — too
  little coverage.
  Pass 2 scraped the full "Weekly Ad Products" + "Price Drops" pages via
  Selenium clicking "Load More" — better coverage, but while hand-copying
  that captured text into a sample file, the "Original Price: ..." lines
  got dropped for most items by mistake. That meant items with a real
  markdown looked IDENTICAL to items that were just Aldi's regular
  everyday price (e.g. Bananas $0.49/lb, Broccoli $2.09/lb — not sales at
  all). The founder caught this directly: "these things are not the
  things that are on sale."

  Pass 3 (this version, 2026-08-07) switches to a completely different,
  more reliable source: Aldi's OFFICIAL weekly ad flyer at
  info.aldi.us/weekly-specials/weekly-ads is rendered by a third-party
  flyer platform called Flipp. That flyer has a clean, structured JSON
  feed behind it:
      https://dam.flippenterprise.net/hosted/publication/{flyer_id}/products
          ?display_type=all&locale=en&access_token={token}
  Every item in that feed carries real fields straight from Aldi's own ad:
    - pre_price_text: literally the string "PRICE DROPS" for genuine
      markdowns, or "" (empty) for everything else. This is a clean,
      unambiguous signal — far better than guessing from a name — so THIS
      is what decides whether something is a real deal now, not a
      before/after price comparison.
    - categories: Aldi's own department tag (e.g. ["Fresh Produce"],
      ["Meat & Seafood"], ["Grocery"], ["Beverage"], ["Household"],
      ["Bread / Bakery"], ["Cheese"], ["Frozen"], ["Deli"]) — no more
      keyword-guessing from the item name.
    - valid_from / valid_to: the flyer's own real confirmed date range.

  IMPORTANT — the flyer_id and access_token are NOT permanent. They're
  generated fresh for each week's flyer, and there's no plain-requests way
  to discover them (they only show up in the page's live network traffic,
  found the first time via Chrome's network-request inspector). So this
  script does NOT fetch Flipp live itself. Instead, each scheduled re-scrape
  run is expected to:
    1. Use a live browser (Chrome MCP tools) to open
       https://info.aldi.us/weekly-specials/weekly-ads, confirm the
       Lakewood-area store (zip 08701, "ALDI, Toms River — 86 NJ Route 70"
       — NOT the similarly-named "80 NJ-70" address, which has no flyer),
       and find the current dam.flippenterprise.net/hosted/publication/
       {flyer_id}/products?...&access_token=... URL (via the network
       requests tool, or by reading the flyer iframe's src).
    2. Fetch that URL directly (a simple fetch() in the browser works
       fine) and save the raw JSON array as
       backend/scrapers/sample_data/aldi_YYYY-MM-DD_flipp.json — no
       trimming needed, parse_deals() below handles the full feed.
    3. Update SAMPLE_PATH below (or just keep the latest-dated file; see
       _find_latest_sample_path()).
  This mirrors how every other store in this project gets its live data:
  a human/browser step captures a fresh snapshot into sample_data/, and
  the Python scraper just parses whatever's there — no Selenium, no
  guessing at login/location flows in headless Python.

CATEGORY RULES (per the founder, still in force):
  ONLY Produce, Eggs, Pantry (canned goods etc.), and Beverages are shown
  from Aldi. Meat/deli/seafood, dairy, bakery, frozen, candy & snacks,
  household, and health & beauty are excluded entirely — no exceptions
  (this replaced an earlier "salmon is OK" rule; salmon is excluded now
  too). Aldi's own categories map onto this allow-list below
  (FLIPP_CATEGORY_MAP). As a defense-in-depth safety net (found necessary
  last time when a name-keyword bug let 3 meat items slip through under
  "Produce"), every item's NAME is also independently checked against the
  full Meat & Deli keyword list and excluded if it matches, regardless of
  what category Aldi itself tagged it with.

  Kosher certification: Aldi's own site tags only a handful of items
  "Kosher" store-wide — far fewer than what actually carries a hechsher
  on the physical package — so that tag isn't reliable enough to filter
  on. Every Aldi page instead carries a disclaimer (see build_site.py's
  STORE_META) telling shoppers to check the package's own kosher symbol.

"LEAVE IT BLANK" RULE (explicit, founder's own words, 2026-08-07): "if
there is a category that does not have sales leave it blank no need to
put random stuff on it." If, in a given week, zero genuine PRICE DROPS
items fall into an allowed category, that category simply shows nothing.
Never pad it with regular-price items to make it look fuller.
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.base_scraper import clean_item_name, CATEGORY_KEYWORDS, _keyword_matches
from db.database import get_connection, init_db, insert_deal

STORE_SLUG = "aldi"
FLYER_PAGE_URL = "https://info.aldi.us/weekly-specials/weekly-ads"
STORE_ZIP = "08701"  # Lakewood-area zip used to confirm the right Aldi store
STORE_NAME_HINT = "ALDI, Toms River — 86 NJ Route 70"  # NOT "80 NJ-70" (no flyer there)
SAMPLE_DIR = Path(__file__).parent / "sample_data"

# The one signal that means "this is a genuine markdown, not just a
# regularly-featured item in the ad." Confirmed 2026-08-07 by checking
# every unique pre_price_text value in a live flyer feed: it's either ""
# (regular) or exactly "PRICE DROPS" (real markdown) — nothing in between.
GENUINE_DEAL_SIGNAL = "PRICE DROPS"

# Aldi's own flyer category tags -> this app's category buckets. Anything
# not listed here (Meat & Seafood, Deli, Bread / Bakery, Cheese, Frozen,
# Household, Health & Beauty, etc.) is excluded by omission.
FLIPP_CATEGORY_MAP = {
    "Fresh Produce": "Produce",
    "Produce": "Produce",
    "Beverage": "Beverages",
    "Beverages": "Beverages",
    "Grocery": "Pantry",
}

# HARD SAFETY NET — do not remove. Even though Aldi's own category tag is
# far more trustworthy than the old name-keyword guesser, this still does
# an independent name check against the full Meat & Deli keyword list and
# excludes on any match, regardless of Aldi's own category tag. The
# founder was explicit and repeated that meat must never appear on this
# page — belt and suspenders. Uses base_scraper's collision-guard-aware
# matcher (fixed 2026-08-10 alongside the same bug in shoprite_scraper.py
# — a plain substring check here would false-flag anything containing
# "ham" as a substring, e.g. "shampoo", as meat/deli).
#
# 2026-08-12: "Fish" was split out of "Meat & Deli" into its own category
# (per the founder's request — tuna/salmon/etc. shouldn't be buried under
# "Meat & Deli"). This safety net must keep excluding fish too, so it now
# checks BOTH keyword lists, not just "Meat & Deli" — otherwise a fish
# item could have silently started slipping through here once its
# keyword moved to a category this check wasn't looking at.
_MEAT_DELI_KEYWORDS = CATEGORY_KEYWORDS["Meat & Deli"] + CATEGORY_KEYWORDS["Fish"]


def _is_meat_or_deli(item_name_lower: str) -> bool:
    return any(_keyword_matches(item_name_lower, kw) for kw in _MEAT_DELI_KEYWORDS)


def _find_latest_sample_path() -> Path | None:
    """Use whichever aldi_*_flipp.json snapshot in sample_data/ is newest
    by filename (they're named aldi_YYYY-MM-DD_flipp.json, so a plain sort
    works), rather than a hardcoded path that goes stale every week."""
    candidates = sorted(SAMPLE_DIR.glob("aldi_*_flipp.json"))
    return candidates[-1] if candidates else None


def parse_deals(flipp_items: list[dict]) -> list[dict]:
    deals = []
    seen_names = set()

    for item in flipp_items:
        name = item.get("name")
        if not name:
            continue
        item_name = clean_item_name(name)
        if not item_name:
            continue

        # GENUINE-DEAL CHECK — the whole reason this rewrite happened.
        # Only items the flyer itself flags as a real markdown count.
        if item.get("pre_price_text") != GENUINE_DEAL_SIGNAL:
            continue

        raw_categories = item.get("categories") or []
        mapped_categories = {
            FLIPP_CATEGORY_MAP[c] for c in raw_categories if c in FLIPP_CATEGORY_MAP
        }
        if not mapped_categories:
            continue  # not Produce/Beverages/Pantry (or an unlabeled junk entry)
        category = sorted(mapped_categories)[0]

        name_lower = item_name.lower()
        # Hard safety net — overrides everything else, even a category
        # Aldi itself tagged as allowed. See comment above _is_meat_or_deli.
        if _is_meat_or_deli(name_lower):
            continue

        price_text = item.get("price_text")
        try:
            sale_price = float(price_text)
        except (TypeError, ValueError):
            continue  # can't confirm a real number, skip rather than guess

        dedupe_key = (item_name.lower(), sale_price)
        if dedupe_key in seen_names:
            continue
        seen_names.add(dedupe_key)

        unit = item.get("post_price_text") or None
        date_from = item.get("valid_from")
        date_to = item.get("valid_to")

        deals.append(
            {
                "store_slug": STORE_SLUG,
                "item_name": item_name,
                "original_price": None,  # the flyer confirms it's a markdown
                                          # via pre_price_text, not a shown
                                          # before-price — see note below
                "sale_price": sale_price,
                "unit": unit,
                "category": category,
                "date_valid_from": date_from,
                "date_valid_to": date_to,
                "raw_text": json.dumps(item)[:300],
            }
        )
    return deals


def run(save_to_db: bool = True, limit_preview: int = 8) -> list[dict]:
    sample_path = _find_latest_sample_path()
    if sample_path is None:
        print(
            f"[{STORE_SLUG}] No cached Flipp snapshot found in sample_data/ "
            f"(expected a file like aldi_YYYY-MM-DD_flipp.json). A live "
            f"browser step needs to fetch the current flyer feed first — "
            f"see this file's docstring. Skipping Aldi for this run."
        )
        return []

    print(f"[{STORE_SLUG}] Source mode: CACHED SNAPSHOT ({sample_path.name})")
    flipp_items = json.loads(sample_path.read_text())

    deals = parse_deals(flipp_items)
    print(
        f"[{STORE_SLUG}] Parsed {len(deals)} genuine PRICE-DROPS deals "
        f"(Produce/Beverages/Pantry only, meat/deli always excluded)."
    )
    if deals:
        print(
            f"[{STORE_SLUG}] Sale window per the flyer itself: "
            f"{deals[0]['date_valid_from']} to {deals[0]['date_valid_to']} "
            f"(these are real confirmed dates, not an estimate)."
        )
    else:
        print(
            f"[{STORE_SLUG}] No qualifying deals this week — pages will "
            f"show empty for any category with nothing genuine, per the "
            f"founder's explicit rule not to pad with regular-price items."
        )

    print(f"\nFirst {min(limit_preview, len(deals))} scraped items:")
    for d in deals[:limit_preview]:
        print(
            f"  - [{d['category']:<10}] {d['item_name']:<45} ${d['sale_price']:.2f}"
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
