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

UPDATE (2026-09-10): refreshed again with the following week's flyer, four
new images (same Meat Specials / Blitz Deals / Weekly Specials layout).
This flyer turned out to have THREE different validity windows at once,
not just the meat-vs-grocery split from last time:
  1. Most of the meat page (Belz-Eckstien, Weissmandl-Marvid-Hisachus,
     Tevya's Ranch, and the regular Gourmet Oven Ready section) prints
     "Weekly Specials 09.09.2026-09.11.2026" — a short Wed-Fri window,
     narrower than this platform's usual Wed-Tue cycle.
  2. The SAME meat page has a distinct red "TWO-DAY SUPER SAVINGS!!
     9/14(MONDAY) & 9/15(TUESDAY) ONLY!!!" sub-section with its own set of
     WOW-tagged items (some brand-new items, like Top of the Rib Roast and
     Classic Cholent Meat; two — Pickled/Pastrami Dark Turkey Roast (KJ)
     — repeat an item from window 1 at the identical price, so those two
     were merged into one row each spanning 09.09-09.15 rather than kept
     as duplicate rows).
  3. The Blitz Deals / Weekly Specials pages (grocery, freezer/fridge,
     nosh, deli, bakery, produce, household) are UNCHANGED from the
     previous flyer and still print "09.02.26-09.11.26" — confirmed by
     comparing every item/price against the prior snapshot line by line.
This is exactly the "meat-vs-grocery date gap" flagged as a to-do in the
previous UPDATE note above, and now that it's recurred with a THIRD window
added on top, it was worth building real per-item date support instead of
another single-range compromise: grocery_platform_scraper.py's
get_page_cached()/scrape_store() now accept an optional per-line date
override (two extra "|||"-delimited fields), so
sample_data/nutmeg_2026-09-09_specials.txt tags the Two-Day items with
their own 2026-09-14/2026-09-15 range and the unchanged grocery items with
their own 2026-09-02/2026-09-11 range, while everything else falls back to
CONFIRMED_DATES below. The Two-Day item names also carry a plain-language
"(Two-Day Special, Mon 9/14 & Tue 9/15 Only)" qualifier as a second,
visible safeguard — as of this same update, build_site.py's client-side JS
also hides any deal whose date_valid_from is still in the future (see its
"isNotYetStartedDeal" note), so those five days from 9/10 to 9/13 they
should be hidden automatically rather than showing early; the in-name
qualifier stays anyway in case that ever needs to be double-checked at a
glance.

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

# See the "UPDATE (2026-09-10)" note above — real dates transcribed
# directly from the store's own printed flyer. This is the default window
# used for any sample-file line that doesn't specify its own per-item
# dates (most of the meat page); the Two-Day and unchanged-grocery items
# override this individually. Set to None to go back to the estimated
# Wednesday-to-Tuesday window.
CONFIRMED_DATES = ("2026-09-09", "2026-09-11")

if __name__ == "__main__":
    run(DOMAIN, LOCATION_SLUG, STORE_SLUG, confirmed_dates=CONFIRMED_DATES)
