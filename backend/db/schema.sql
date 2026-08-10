-- Lakewood Deals Aggregator — Database Schema (SQLite)
-- Plain-English summary of each table is in the comment above it.

PRAGMA foreign_keys = ON;

-- One row per store we scrape (grocery today; wine stores are the next
-- category planned — that's why store_type and lat/lng exist already,
-- even though every row right now is 'grocery' with no coordinates).
CREATE TABLE IF NOT EXISTS stores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,          -- e.g. "Gourmet Glatt"
    slug        TEXT NOT NULL UNIQUE,          -- e.g. "gourmet-glatt" (used in URLs/code)
    source_type TEXT NOT NULL CHECK (source_type IN ('html', 'pdf')),  -- how we scrape it
    source_url  TEXT,                          -- the page we scrape
    store_type  TEXT NOT NULL DEFAULT 'grocery' CHECK (store_type IN ('grocery', 'wine')),
    latitude    REAL,                          -- filled in once we add store locations/maps
    longitude   REAL,                          -- (needed for "wine stores near this grocer")
    address     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Fixed list of categories used for filtering.
CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE                  -- Produce, Meat, Dairy, Bakery, Pantry
);

-- The actual deals. One row per scraped item, per scrape date.
CREATE TABLE IF NOT EXISTS deals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id        INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    item_name       TEXT NOT NULL,
    original_price  REAL,                      -- NULL if the flyer only shows the sale price
    sale_price      REAL NOT NULL,
    unit            TEXT,                      -- e.g. "lb", "ea", "16 oz" — kept as free text
    category_id     INTEGER REFERENCES categories(id),
    date_valid_from TEXT NOT NULL,             -- ISO date the sale starts
    date_valid_to   TEXT NOT NULL,             -- ISO date the sale ends
    raw_text        TEXT,                      -- original scraped snippet, for debugging
    scraped_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_deals_store ON deals(store_id);
CREATE INDEX IF NOT EXISTS idx_deals_category ON deals(category_id);
CREATE INDEX IF NOT EXISTS idx_deals_item_name ON deals(item_name);
CREATE INDEX IF NOT EXISTS idx_deals_date_valid ON deals(date_valid_from, date_valid_to);

-- User accounts (Step 3+ feature — created now so the schema is stable from day one).
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,               -- never store plain-text passwords
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- A user's saved "Shopping List" items — links a user to a specific deal.
CREATE TABLE IF NOT EXISTS shopping_list_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    deal_id    INTEGER NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    added_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, deal_id)
);

-- Seed the fixed category list (expanded 2026-08-06 from 5 to 10 categories
-- to better match the real departments each store's own site uses).
INSERT OR IGNORE INTO categories (name) VALUES
    ('Produce'), ('Meat & Deli'), ('Dairy'), ('Bakery'), ('Beverages'),
    ('Frozen'), ('Candy & Snacks'), ('Household'), ('Health & Beauty'), ('Pantry');

-- Seed the stores the founder wants tracked.
-- ShopRite and Aldi (added 2026-08-07) are general supermarkets, not
-- dedicated kosher grocers like the other six — see build_site.py's
-- STORE_META for the kosher-certification disclaimer shown on their
-- pages, and base_scraper.py's NON_KOSHER_FRIENDLY_EXCLUDE handling for
-- why meat is filtered out of their scraped deals entirely.
INSERT OR IGNORE INTO stores (name, slug, source_type, source_url) VALUES
    ('Gourmet Glatt',   'gourmet-glatt',   'pdf',  'https://gourmetglatt.com/lakewood-njersey/specials'),
    ('Seasons',         'seasons',         'html', NULL),
    ('Nutmeg',          'nutmeg',          'html', NULL),
    ('Kosher West',     'kosher-west',     'html', NULL),
    ('Kosher Village',  'kosher-village',  'html', NULL),
    ('Bingo',           'bingo',           'pdf',  NULL),
    ('ShopRite',        'shoprite',        'html', 'https://www.shoprite.com/circulars'),
    ('Aldi',            'aldi',            'html', 'https://www.aldi.us/en/weekly-specials/'),
    ('Aisle 9',         'aisle-9',         'html', 'https://aisle9market.com/lakewood/category/specials');
