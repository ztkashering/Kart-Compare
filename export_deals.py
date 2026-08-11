"""
export_deals.py — reads backend/db/deals.db and writes all_deals_export.json,
which build_site.py then turns into the actual webpages.

Run order for a full refresh:
    cd backend && python3 -m scrapers.gourmet_glatt_scraper (and the other 5)
    cd ..
    python3 export_deals.py
    python3 build_site.py
"""

import json
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
# Match database.py's path logic exactly (same env var, same default
# filename) — these used to disagree (this file pointed at a "deals.db"
# that doesn't exist; the real file is "deals_all_stores.db"), which would
# have silently exported zero deals the next time this ran standalone.
DB_PATH = Path(
    os.environ.get("DEALS_DB_PATH", str(BASE_DIR / "backend" / "db" / "deals_all_stores.db"))
)
OUT_PATH = BASE_DIR / "all_deals_export.json"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    deals = [
        dict(r)
        for r in conn.execute(
            """
            select d.id, d.item_name, d.sale_price, d.original_price, d.unit,
                   c.name as category, s.name as store, s.slug as store_slug,
                   d.date_valid_from, d.date_valid_to, d.kosher_flag
            from deals d
            join categories c on c.id = d.category_id
            join stores s on s.id = d.store_id
            order by s.name, d.item_name
            """
        )
    ]
    stores = [
        dict(r)
        for r in conn.execute(
            "select name, slug, source_type, source_url from stores order by name"
        )
    ]

    OUT_PATH.write_text(json.dumps({"deals": deals, "stores": stores}, indent=2))
    print(f"Exported {len(deals)} deals across {len(stores)} stores to {OUT_PATH.name}")


if __name__ == "__main__":
    main()
