"""
nutmeg_scraper.py — Nutmeg Kosher Market (Lakewood, NJ).

Same underlying website platform as Seasons and Kosher West — see
grocery_platform_scraper.py for the shared scraping logic.

UPDATE (2026-08-30): the founder shared Nutmeg's actual current weekly
flyer as four images (Meat specials + Blitz Deals + the main Weekly
Specials sheet). Unlike Seasons' flyer, these prints don't show any
"was" price or "SAVE $X" tag next to any item — just a flat sale price —
so original_price is left blank for all of them rather than guessed;
they're still real, store-published special prices, just without a
comparison point. Every item was transcribed by hand into
sample_data/nutmeg_2026-08-30_specials.txt (114 items). The flyer prints
"08.26.2026-09.01.2026" (Wednesday through Tuesday) — this one DOES
match the Wednesday-to-Tuesday cycle this scraper already assumes, but
CONFIRMED_DATES is still set explicitly below so this is recorded as a
real confirmed date rather than a coincidental estimate.

THIS OVERRIDE IS TIED TO THAT ONE SNAPSHOT, NOT PERMANENT — see
seasons_scraper.py's identical note for what to do once this week's sale
ends. Same applies to build_site.py's STORE_META["nutmeg"].
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scrapers.grocery_platform_scraper import run

DOMAIN = "nutmegkoshermarket.com"
LOCATION_SLUG = "Lakewood-NJ"
STORE_SLUG = "nutmeg"

# See the "UPDATE (2026-08-30)" note above — real dates transcribed
# directly from the store's own printed flyer, not guessed. Set to None
# to go back to the estimated Wednesday-to-Tuesday window.
CONFIRMED_DATES = ("2026-08-26", "2026-09-01")

if __name__ == "__main__":
    run(DOMAIN, LOCATION_SLUG, STORE_SLUG, confirmed_dates=CONFIRMED_DATES)
