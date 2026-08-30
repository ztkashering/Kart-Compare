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

UPDATE (2026-08-30): the founder shared the actual current flyer images
directly (the two pages of the real printed circular), so this scraper's
"can't OCR the flyer image" limitation was worked around by hand this
once — a person (well, Claude, reading the images) transcribed every
item, price, and the store-printed date range straight from those
images into sample_data/seasons_2026-08-30_specials.txt. The flyer
itself prints "PRICES VALID 8/30/26 - 9/4/26" (Sunday through Friday) —
notably NOT the Wednesday-to-Tuesday cycle this scraper otherwise
assumes, so CONFIRMED_DATES below overrides that estimate with the real
printed range for this snapshot specifically.

THIS OVERRIDE IS TIED TO THAT ONE SNAPSHOT, NOT PERMANENT: once this
week's sale ends, CONFIRMED_DATES will be describing a stale flyer as if
it were still current. Whoever refreshes this next (a live scrape, or
another hand-transcribed flyer) should either update CONFIRMED_DATES to
the new real range, or remove it entirely to fall back to the honest
Wednesday-to-Tuesday estimate — don't leave a past week's dates in place.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scrapers.grocery_platform_scraper import run

DOMAIN = "seasonskosher.com"
LOCATION_SLUG = "Lakewood-NJ"
STORE_SLUG = "seasons"

# See the "UPDATE (2026-08-30)" note above — real dates transcribed
# directly from the store's own printed flyer, not guessed. Set to None
# to go back to the estimated Wednesday-to-Tuesday window.
CONFIRMED_DATES = ("2026-08-30", "2026-09-04")

if __name__ == "__main__":
    run(DOMAIN, LOCATION_SLUG, STORE_SLUG, confirmed_dates=CONFIRMED_DATES)
