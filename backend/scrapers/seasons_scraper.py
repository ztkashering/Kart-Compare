"""
seasons_scraper.py — Seasons (Lakewood, NJ).

Seasons runs on the same website platform as Nutmeg and Kosher West (see
grocery_platform_scraper.py for the shared logic and the full explanation
of how it works and what it can/can't tell us about sale dates).

Bonus fact confirmed during research: Seasons ALSO has a separate digital
flyer at seasonskosher.com/Weekly-Circular showing "PRICES VALID 8/2/26 -
8/7/26" for the current week — but that text is baked into a designed
image, not real webpage text, so a normal scraper can't read it directly
(would need image OCR, which is a heavier, separate feature). The
specials list scraped here is the same underlying sale, just without an
automatically-confirmed end date.

UPDATE (2026-08-30): the founder shared the actual current flyer as two
images (same "designed image, not real text" format described above),
so this one snapshot was read by hand instead — every item, price, and
the store-printed date range transcribed straight off the images into
sample_data/seasons_2026-08-30_specials.txt (70 items). The flyer prints
"PRICES VALID 8/30/26 - 9/4/26" (Sunday through Friday) — notably NOT
the Wednesday-to-Tuesday cycle this scraper otherwise assumes — so
CONFIRMED_DATES below overrides that estimate with the real printed
range for this snapshot specifically (grocery_platform_scraper.py's
scrape_store()/run() gained an optional confirmed_dates parameter for
this; Nutmeg and Kosher West don't pass it, so they're unaffected).

UPDATE (2026-09-06): refreshed again with the following week's flyer
(Rosh Hashana week), same "designed image" format, three images this
time. 73 items transcribed into sample_data/seasons_2026-09-06_specials.txt.
Flyer prints "PRICES VALID 9/6/26 - 9/11/26" (Sunday through Erev Rosh
Hashana Friday) — same Sunday-to-Friday shape as the Aug 30 flyer, so
still not the Wednesday-to-Tuesday default.

UPDATE (2026-09-14): refreshed again with the following week's flyer
(post-Rosh Hashana), two images this time. 70 items transcribed into
sample_data/seasons_2026-09-13_specials.txt. Flyer prints "PRICES VALID
9/13/26 - 9/18/26" (Sunday through Erev Shabbos Friday), same Sunday-to-
Friday shape as the last two flyers.

This flyer also has two small day-specific sub-boxes layered on top of
the main week-long window, the same pattern Nutmeg's flyer needed a
per-item date override for (see nutmeg_scraper.py's "UPDATE (2026-09-10)"
note for the mechanism itself, reused here as-is):
  - "Monday & Tuesday Bakery Deals" (4 items) — valid only Mon 9/14 &
    Tue 9/15, tagged 2026-09-14/2026-09-15 in the sample file.
  - "Shabbos Specials: Thursday & Friday" (4 items) — valid only Thu
    9/17 & Fri 9/18, tagged 2026-09-17/2026-09-18 in the sample file.
Both sets of items also carry a plain-language qualifier in their own
name ("(Monday & Tuesday Bakery Deal)" / "(Shabbos Special, Thursday &
Friday)") as a second, visible safeguard, same reasoning as Nutmeg's
Two-Day items. Everything else on this flyer falls back to
CONFIRMED_DATES below (the full 9/13-9/18 window).

THIS OVERRIDE IS TIED TO THAT ONE SNAPSHOT, NOT PERMANENT: once this
week's sale ends, CONFIRMED_DATES will be describing a stale flyer as if
it were still current. Whoever refreshes Seasons next (a live scrape, or
another hand-transcribed flyer) should either update CONFIRMED_DATES to
the new real range, or remove it to fall back to the honest Wednesday-
to-Tuesday estimate — don't leave a past week's dates in place. Same
applies to build_site.py's STORE_META["seasons"]["dates_confirmed"],
which was flipped to True alongside this. Also note: as of 2026-08-30
export_deals.py and build_site.py auto-drop/hide any deal once its own
date_valid_to passes, so leaving a stale CONFIRMED_DATES here isn't just
inaccurate — the whole page will actually go blank on its own once the
date passes, which is a stronger incentive to keep this current.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scrapers.grocery_platform_scraper import run

DOMAIN = "seasonskosher.com"
LOCATION_SLUG = "Lakewood-NJ"
STORE_SLUG = "seasons"

# See the "UPDATE (2026-09-14)" note above — real dates transcribed
# directly from the store's own printed flyer, not guessed. This is the
# default for any sample-file line without its own per-item date
# override (the two day-specific sub-boxes override it individually).
# Set to None to go back to the estimated Wednesday-to-Tuesday window.
CONFIRMED_DATES = ("2026-09-13", "2026-09-18")

if __name__ == "__main__":
    run(DOMAIN, LOCATION_SLUG, STORE_SLUG, confirmed_dates=CONFIRMED_DATES)
