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
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scrapers.grocery_platform_scraper import run

DOMAIN = "seasonskosher.com"
LOCATION_SLUG = "Lakewood-NJ"
STORE_SLUG = "seasons"

if __name__ == "__main__":
    run(DOMAIN, LOCATION_SLUG, STORE_SLUG)
