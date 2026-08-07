"""
nutmeg_scraper.py — Nutmeg Kosher Market (Lakewood, NJ).

Same underlying website platform as Seasons and Kosher West — see
grocery_platform_scraper.py for the shared scraping logic.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scrapers.grocery_platform_scraper import run

DOMAIN = "nutmegkoshermarket.com"
LOCATION_SLUG = "Lakewood-NJ"
STORE_SLUG = "nutmeg"

if __name__ == "__main__":
    run(DOMAIN, LOCATION_SLUG, STORE_SLUG)
