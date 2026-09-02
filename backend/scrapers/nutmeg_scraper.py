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
comparison point.

UPDATE (2026-09-02): refreshed with the following week's flyer, same
format (four images, no "was" price anywhere). 118 items transcribed
into sample_data/nutmeg_2026-09-02_specials.txt. NOTE: this flyer prints
TWO different date ranges — the meat specials page says
"09.02.2026-09.08.2026" (Wed-Tue), while the Blitz Deals / Weekly
Specials pages (grocery, freezer/fridge, nosh, deli, bakery, produce,
household) say "09.02.26-09.11.26" (through the following Friday, 3
days longer). grocery_platform_scraper.py's confirmed_dates is one
single range for the whole scrape, not per-item, so this deliberately
uses the SHORTER, more conservative range (through 9/8) for everything
rather than building per-item date support for a 3-day difference — it
means the non-meat items technically get pulled off the site a few days
before they'd technically still be on sale, never the other way around.
If this meat-vs-grocery date gap keeps recurring, it's worth adding real
per-item date support (see shoprite_scraper.py's sample format for a
working example of that pattern).

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

# See the "UPDATE (2026-09-02)" note above — real dates transcribed
# directly from the store's own printed flyer (the shorter, meat-page
# range, used conservatively for the whole snapshot), not guessed. Set
# to None to go back to the estimated Wednesday-to-Tuesday window.
CONFIRMED_DATES = ("2026-09-02", "2026-09-08")

if __name__ == "__main__":
    run(DOMAIN, LOCATION_SLUG, STORE_SLUG, confirmed_dates=CONFIRMED_DATES)
