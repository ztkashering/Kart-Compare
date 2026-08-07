"""
kosher_west_scraper.py — Kosher West (Lakewood, NJ).

Same underlying website platform as Seasons and Nutmeg — see
grocery_platform_scraper.py for the shared scraping logic.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scrapers.grocery_platform_scraper import run

DOMAIN = "kosherwest.com"
LOCATION_SLUG = "Lakewood-NJ"
STORE_SLUG = "kosher-west"

if __name__ == "__main__":
    run(DOMAIN, LOCATION_SLUG, STORE_SLUG)
