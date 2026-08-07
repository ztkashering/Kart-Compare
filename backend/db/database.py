"""
database.py — tiny helper module for talking to the SQLite database.

Plain English: this file knows how to (1) create the database file the
first time the app runs, using schema.sql, and (2) hand out a connection
any other script can use to read/write deals.
"""

import os
import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).parent
# Allow overriding where the .db file lives via an env var. Some synced /
# cloud-mounted folders don't support the file-locking SQLite needs, which
# shows up as "disk I/O error" — if you hit that, point DEALS_DB_PATH at a
# plain local folder instead.
DB_PATH = Path(os.environ.get("DEALS_DB_PATH", str(DB_DIR / "deals_all_stores.db")))
SCHEMA_PATH = DB_DIR / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Open (or create) the SQLite database file and return a connection.

    Foreign keys are off by default in SQLite, so we turn them on. Row
    factory is set to sqlite3.Row so query results behave like dicts
    (row["item_name"] instead of row[1]).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all tables (if they don't already exist) and seed lookup
    data (categories, stores). Safe to run every time the app starts —
    it won't wipe existing deals."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
    print(f"[database] Ready at {DB_PATH}")


def get_store_id(conn: sqlite3.Connection, slug: str) -> int:
    row = conn.execute("SELECT id FROM stores WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise ValueError(f"Unknown store slug: {slug!r}. Add it to schema.sql first.")
    return row["id"]


def get_category_id(conn: sqlite3.Connection, category_name: str) -> int:
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ?", (category_name,)
    ).fetchone()
    if row is not None:
        return row["id"]
    # A brand new category name (e.g. the keyword list in base_scraper.py
    # grew a new bucket) shouldn't crash the whole scrape run — add it on
    # the fly instead of requiring a manual schema.sql edit every time.
    conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category_name,))
    row = conn.execute(
        "SELECT id FROM categories WHERE name = ?", (category_name,)
    ).fetchone()
    return row["id"]


def clear_store_deals(conn: sqlite3.Connection, store_slug: str) -> None:
    """Delete all existing deal rows for one store.

    Every scraper's run() calls this right before re-inserting its fresh
    results. Without it, re-running a scraper (which the twice-weekly
    scheduled task does, forever) would just keep appending duplicate
    rows on top of the previous run's, instead of replacing them —
    found 2026-08-07 when a few manual re-runs of the Aldi scraper while
    testing left duplicate rows sitting in the live database.
    """
    store_id = get_store_id(conn, store_slug)
    conn.execute("DELETE FROM deals WHERE store_id = ?", (store_id,))
    conn.commit()


def insert_deal(conn: sqlite3.Connection, deal: dict) -> int:
    """Insert one deal row. `deal` must have keys:
    store_slug, item_name, sale_price, date_valid_from, date_valid_to
    and may have: original_price, unit, category, raw_text.
    Returns the new row's id.
    """
    store_id = get_store_id(conn, deal["store_slug"])
    category_id = (
        get_category_id(conn, deal["category"]) if deal.get("category") else None
    )
    cur = conn.execute(
        """
        INSERT INTO deals
            (store_id, item_name, original_price, sale_price, unit,
             category_id, date_valid_from, date_valid_to, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            store_id,
            deal["item_name"],
            deal.get("original_price"),
            deal["sale_price"],
            deal.get("unit"),
            category_id,
            deal["date_valid_from"],
            deal["date_valid_to"],
            deal.get("raw_text"),
        ),
    )
    conn.commit()
    return cur.lastrowid


if __name__ == "__main__":
    init_db()
