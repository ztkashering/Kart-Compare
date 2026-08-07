"""
build_site.py — generates the "Kart Compare" website from all_deals_export.json.

Reads:  all_deals_export.json  (produced by export_deals.py from deals.db)
Writes: site/index.html, site/<store-slug>.html for every store, site/about.html,
        site/deals.json, site/manifest.json, site/sw.js
        (site/favicon.ico, icon-192.png, icon-512.png, apple-touch-icon.png,
        og-image.png are produced separately by gen_assets.py)

Brand: Kart Compare — "Compare grocery deals across Lakewood, all in one cart."

CHANGES IN THIS PASS (mobile/launch-readiness audit fixes):
  - Mobile viewport tag + responsive CSS — the site was unreadable on a
    phone before this (no viewport meta tag at all).
  - The header no longer stays pinned while scrolling — only the search/
    filter toolbar does. Two stacked sticky elements is what was causing
    the toolbar to overlap content once the header wrapped to two lines
    on a narrow phone screen; removing the header's own "stickiness"
    removes that failure mode entirely, on any screen size.
  - Favicon, meta description, and Open Graph / Twitter share tags, so
    the browser tab has an icon and a shared link shows a real preview
    card instead of a blank one.
  - The "when was this last checked" date is now shown more prominently
    on every page, since specials have been proven (during testing) to
    change within days — a stale static page shouldn't look as fresh as
    a just-updated one.
  - Every page used to embed the ENTIRE 437-item dataset inline, even
    store pages only showing 10-139 of them. Now there's a single shared
    deals.json file that every page fetches once. IMPORTANT TRADE-OFF:
    this means the site can no longer be opened by just double-clicking
    the HTML file — browsers block a plain local file from loading
    another local file for security reasons. It needs to be served by an
    actual web server, which is exactly what GitHub Pages (or any real
    hosting) does automatically. See README.md for a one-line way to
    preview it locally before pushing.
  - 10 categories instead of 5, matching the real store departments much
    more closely (see base_scraper.py's CATEGORY_KEYWORDS).
  - A "Report a wrong price" contact link in the footer.
  - A new About page explaining what this is, how it's built, and that
    it's an independent, unofficial project (not affiliated with the
    stores listed).
  - Basic PWA support (manifest.json + a small service worker) so it can
    be "Added to Home Screen" on a phone and opened like an app, without
    the cost or complexity of building and publishing an actual native
    app.
  - A placeholder analytics tag (GoatCounter — free, privacy-friendly,
    no cookie banner needed) — swap in your own site code once you sign
    up; see README.md.

No external packages needed for this script itself — plain Python
standard library + HTML/CSS/JS. (gen_assets.py, run separately, does use
Pillow to draw the placeholder icons/share image.)
"""

import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "all_deals_export.json"
SITE_DIR = BASE_DIR / "docs"

BRAND_NAME = "Kart Compare"
BRAND_TAGLINE = "Compare grocery deals across Lakewood — all in one cart."
SITE_URL_PLACEHOLDER = "https://example.com"  # swap for the real domain once you have one
CONTACT_EMAIL = "practicer247@gmail.com"

# GoatCounter is a free, privacy-friendly analytics service (no cookie
# banner needed since it doesn't track individuals). Sign up free at
# https://www.goatcounter.com, pick a site code, and replace
# "YOURCODE" below with it. Until you do, this line simply does nothing.
GOATCOUNTER_CODE = "YOURCODE"

ICONS = {
    "Produce": "\U0001F34E",
    "Meat & Deli": "\U0001F357",
    "Dairy": "\U0001F9C0",
    "Bakery": "\U0001F950",
    "Beverages": "\U0001F964",
    "Frozen": "\U0001F9CA",
    "Candy & Snacks": "\U0001F36C",
    "Household": "\U0001F9FB",
    "Health & Beauty": "\U0001F9F4",
    "Pantry": "\U0001F6D2",
}

STORE_META = {
    "gourmet-glatt": {
        "dates_confirmed": True,
        "note": "Dates confirmed directly from this week's real flyer text.",
    },
    "seasons": {
        "dates_confirmed": False,
        "note": (
            "This store's exact sale dates are shown on their site as part of "
            "a flyer image, which today's scraper can't read automatically "
            "(would need image OCR). Dates below reflect this store's real "
            "Wednesday-morning-to-Tuesday-night sale week, not a store-"
            "published exact date."
        ),
    },
    "nutmeg": {
        "dates_confirmed": False,
        "note": (
            "This store doesn't publish an exact valid-through date online. "
            "Dates below reflect this store's real Wednesday-morning-to-"
            "Tuesday-night sale week, not a store-published exact date."
        ),
    },
    "kosher-west": {
        "dates_confirmed": False,
        "note": (
            "This store doesn't publish an exact valid-through date online. "
            "Dates below reflect this store's real Wednesday-morning-to-"
            "Tuesday-night sale week, not a store-published exact date."
        ),
    },
    "kosher-village": {
        "dates_confirmed": False,
        "note": (
            "This store doesn't publish an exact valid-through date online. "
            "Dates below reflect the same Wednesday-to-Tuesday sale week as "
            "the other estimated stores, not a store-published exact date."
        ),
    },
    "bingo": {
        "dates_confirmed": False,
        "note": (
            "No current flyer was found on Bingo's site at the time of the "
            "last scrape — this page will fill in automatically once they "
            "post one."
        ),
    },
    "aldi": {
        "dates_confirmed": True,
        "note": (
            "An earlier pass showed items here that turned out to just be "
            "Aldi's regular everyday prices, not real markdowns — that's "
            "been caught and fixed (2026-08-07). This page is now built "
            "directly from Aldi's own official weekly flyer, using its "
            "\"Price Drops\" tag as the only signal for a genuine sale — "
            "if the flyer doesn't mark it as a Price Drop, it isn't shown "
            "here, even if it appears elsewhere on Aldi's site. If a "
            "category has no genuine Price Drops this week, it's shown "
            "empty rather than padded with regular-price items."
        ),
        "kosher_note": (
            "Aldi is a general supermarket, not a dedicated kosher grocer. "
            "This page only shows Produce, Eggs, Pantry (including canned "
            "goods), and Beverages — meat, deli, seafood, dairy, bakery, "
            "frozen, and snack items are left off entirely, no exceptions. "
            "Please still check the package's own kosher certification "
            "(hechsher) before buying — Aldi does tag a small number of "
            "items \"Kosher\" on their own site, but far fewer than what "
            "actually carries a hechsher in store, so this site can't rely "
            "on that tag and can't verify certification automatically."
        ),
    },
    "shoprite": {
        "dates_confirmed": False,
        "note": (
            "ShopRite's weekly ad setup for the Jackson, NJ location "
            "(the closest working store to Lakewood) is in progress — this "
            "page will fill in with real deals once that's finished."
        ),
        "kosher_note": (
            "ShopRite is a general supermarket, not a dedicated kosher "
            "grocer. Once live, this page will only show Produce, Eggs, "
            "Pantry (including canned goods), and Beverages — meat, deli, "
            "seafood, dairy, bakery, frozen, and snack items will be left "
            "off entirely, no exceptions. Please still check the package's "
            "own kosher certification (hechsher) before buying — this site "
            "can't verify that automatically."
        ),
    },
}

LOGO_SVG = """
<svg width="32" height="32" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="2" width="44" height="44" rx="13" fill="var(--brand)"/>
  <path d="M12 15h3l3.2 14.5a2 2 0 0 0 2 1.6h11a2 2 0 0 0 1.95-1.55L35.5 19H18" stroke="white" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <circle cx="21" cy="35" r="2" fill="white"/>
  <circle cx="30" cy="35" r="2" fill="white"/>
  <circle cx="34" cy="14" r="7" fill="var(--accent)"/>
  <path d="M31.6 14l1.6 1.6L36.6 12" stroke="white" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>
"""

FONT_LINK = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/inter-ui/3.19.3/inter.min.css">'

# --- Shared <head> tags: favicon, mobile viewport, SEO + share previews, PWA ---
def head_tags(page_title, page_description, page_url_path):
    og_image = "og-image.png"
    canonical = f"{SITE_URL_PLACEHOLDER}/{page_url_path}"
    return f"""<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{page_title}</title>
<meta name="description" content="{page_description}">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#4F46E5">
<meta property="og:type" content="website">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="{page_description}">
<meta property="og:image" content="{og_image}">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{page_title}">
<meta name="twitter:description" content="{page_description}">
<meta name="twitter:image" content="{og_image}">
{FONT_LINK}"""


ANALYTICS_SNIPPET = f"""<script data-goatcounter="https://{GOATCOUNTER_CODE}.goatcounter.com/count"
  async src="//gc.zgo.at/count.js"></script>
<!-- Free, privacy-friendly analytics (no cookie banner needed). Sign up at
     https://www.goatcounter.com and replace GOATCOUNTER_CODE in build_site.py
     with your own site code — until then this line quietly does nothing. -->"""

PWA_REGISTER_JS = """
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}
"""

BASE_CSS = """
:root {
  --brand: #4F46E5;
  --brand-dark: #383096;
  --brand-darker: #26205e;
  --brand-light: #EEF2FF;
  --accent: #F97316;
  --accent-dark: #C2410C;
  --success: #059669;
  --success-light: #ECFDF5;
  --bg: #F7F7FB;
  --card-bg: #ffffff;
  --border: #E5E7EB;
  --text: #111827;
  --muted: #6B7280;
  --amber-bg: #FFFBEB;
  --amber-border: #FDE68A;
  --amber-text: #92600A;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}
a { color: inherit; }
.wrap { max-width: 1140px; margin: 0 auto; padding: 0 20px; }

/* ---------- Header (NOT sticky — see build_site.py notes on why) ---------- */
.site-header {
  background: var(--brand);
  color: white;
  box-shadow: 0 2px 10px rgba(17,24,39,0.12);
}
.header-top {
  max-width: 1140px; margin: 0 auto; padding: 12px 20px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
}
.brand-row { display: flex; align-items: center; gap: 10px; text-decoration: none; }
.brand-row .wordmark { font-size: 19px; font-weight: 800; letter-spacing: -0.02em; color: white; }
.header-search {
  flex: 1; min-width: 200px; max-width: 420px;
  display: flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.28);
  border-radius: 10px; padding: 8px 12px;
}
.header-search input {
  border: none; background: transparent; outline: none; color: white; font-size: 16px; width: 100%;
}
.header-search input::placeholder { color: rgba(255,255,255,0.75); }
.header-search svg { flex-shrink: 0; opacity: 0.85; }
.nav-links { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; }
.nav-links a { text-decoration: none; opacity: 0.82; padding-bottom: 2px; }
.nav-links a.current { opacity: 1; font-weight: 700; border-bottom: 2px solid var(--accent); }
.nav-links a:hover { opacity: 1; }
.header-bottom {
  border-top: 1px solid rgba(255,255,255,0.14);
}
.header-bottom .wrap { padding: 8px 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; }
.page-sub { font-size: 13px; opacity: 0.9; font-weight: 600; }

/* ---------- Hero (homepage only) ---------- */
.hero {
  background: linear-gradient(160deg, var(--brand) 0%, var(--brand-dark) 65%, var(--brand-darker) 100%);
  color: white;
  padding: 40px 20px 34px;
}
.hero .wrap { text-align: center; }
.hero h1 { margin: 0 0 10px; font-size: 32px; font-weight: 800; letter-spacing: -0.03em; }
.hero p.sub { margin: 0 auto; max-width: 560px; font-size: 15px; opacity: 0.9; line-height: 1.5; }
.stat-row { display: flex; justify-content: center; gap: 10px; margin-top: 22px; flex-wrap: wrap; }
.stat-chip {
  background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.22);
  border-radius: 999px; padding: 8px 16px; font-size: 13px; font-weight: 600;
}
.stat-chip strong { font-weight: 800; }
.stat-chip.fresh { background: var(--accent); border-color: var(--accent); }

/* ---------- Page header (store pages) ---------- */
.page-header { background: var(--card-bg); border-bottom: 1px solid var(--border); padding: 22px 20px; }
.page-header h1 { margin: 0 0 6px; font-size: 24px; font-weight: 800; letter-spacing: -0.02em; }
.page-header .sub { color: var(--text); font-size: 14px; font-weight: 600; }
.page-header .sub .muted-part { color: var(--muted); font-weight: 400; }

/* ---------- Date banner ---------- */
.date-banner {
  margin: 16px auto 0; padding: 12px 18px; border-radius: 10px; font-size: 13px;
  display: flex; flex-direction: column; gap: 4px;
}
.date-banner.confirmed { background: var(--success-light); color: #036b4a; border: 1px solid #b8e6d2; }
.date-banner.estimated { background: var(--amber-bg); color: var(--amber-text); border: 1px solid var(--amber-border); }
.date-banner .big { font-size: 15px; font-weight: 800; }

/* ---------- Sticky toolbar: filters (the ONLY sticky element on the page) ---------- */
.toolbar {
  position: sticky; top: 0; z-index: 30;
  background: rgba(247,247,251,0.95); backdrop-filter: blur(6px);
  border-bottom: 1px solid var(--border);
  padding: 12px 0;
}
.toolbar-inner { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.toolbar select {
  padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px;
  font-size: 13.5px; background: white; color: var(--text); font-family: inherit;
}
.pill-row { display: flex; gap: 6px; flex-wrap: wrap; }
.pill {
  border: 1px solid var(--border); background: white; color: var(--text);
  border-radius: 999px; padding: 7px 14px; font-size: 13px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all .12s ease;
}
.pill:hover { border-color: var(--brand); }
.pill.active { background: var(--brand); border-color: var(--brand); color: white; }
.count { padding: 10px 0 0; font-size: 13px; color: var(--muted); }

/* ---------- Deals grid ---------- */
.grid {
  margin: 14px 0 50px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(232px, 1fr));
  gap: 16px;
}
.card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  position: relative;
  transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(17,24,39,0.08); border-color: #d7d9e6; }
.card .icon-row { display: flex; align-items: center; justify-content: space-between; }
.card .icon-badge {
  width: 40px; height: 40px; border-radius: 10px; background: var(--brand-light);
  display: flex; align-items: center; justify-content: center; font-size: 20px;
}
.card .savings-badge {
  background: var(--success-light); color: var(--success);
  font-size: 11px; font-weight: 800; padding: 4px 8px; border-radius: 999px;
}
.card .cat-tag {
  font-size: 11px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em;
}
.card .name {
  font-size: 14.5px; font-weight: 700; line-height: 1.35; min-height: 40px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.card .store-tag {
  font-size: 12px; color: var(--brand); font-weight: 600; background: var(--brand-light);
  display: inline-block; padding: 2px 8px; border-radius: 6px; width: fit-content;
}
.card .price-row { display: flex; align-items: baseline; gap: 8px; margin-top: auto; }
.card .sale-price { font-size: 21px; font-weight: 800; color: var(--text); letter-spacing: -0.02em; }
.card .old-price { font-size: 13px; color: var(--muted); text-decoration: line-through; }
.card .unit-note { font-size: 12px; color: var(--muted); margin-top: -4px; }
.card .add-btn {
  margin-top: 4px; border: 1.5px solid var(--brand); background: white; color: var(--brand);
  border-radius: 8px; padding: 10px 10px; font-size: 13px; cursor: pointer; font-weight: 700;
  font-family: inherit; transition: all .12s ease;
}
.card .add-btn:hover { background: var(--brand-light); }
.card .add-btn.added { background: var(--brand); color: white; }
.empty { max-width: 1140px; margin: 60px auto; text-align: center; color: var(--muted); padding: 0 20px; line-height: 1.6; }

/* ---------- Store cards (homepage browse section) ---------- */
.store-grid {
  margin: 16px 0 0;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px;
}
.store-card {
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px;
  padding: 18px; text-decoration: none; display: flex; flex-direction: column; gap: 8px;
  transition: transform .12s ease, box-shadow .12s ease;
}
.store-card:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(17,24,39,0.08); }
.store-card .avatar {
  width: 38px; height: 38px; border-radius: 10px; background: var(--brand-light); color: var(--brand);
  display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 15px;
}
.store-card h3 { margin: 0; font-size: 16px; color: var(--text); font-weight: 700; }
.store-card .n { font-size: 13px; color: var(--muted); }
.store-card .d { font-size: 12px; font-weight: 600; }
.store-card .d.confirmed { color: var(--success); }
.store-card .d.estimated { color: var(--amber-text); }

.section-title { margin: 34px 0 4px; font-size: 18px; font-weight: 800; letter-spacing: -0.01em; }
.section-sub { margin: 0 0 4px; font-size: 13px; color: var(--muted); }

.roadmap-banner {
  margin: 28px 0 0; padding: 16px 18px;
  background: var(--card-bg); border: 1px dashed #c7c9e0; border-radius: 12px;
  font-size: 13px; color: var(--muted); line-height: 1.5;
}
.roadmap-banner strong { color: var(--text); }

/* ---------- About page ---------- */
.about-body { max-width: 720px; margin: 0 auto; padding: 36px 20px 60px; line-height: 1.7; font-size: 15px; }
.about-body h1 { font-size: 28px; font-weight: 800; margin: 0 0 6px; letter-spacing: -0.02em; }
.about-body h2 { font-size: 18px; font-weight: 800; margin: 32px 0 10px; }
.about-body p { margin: 0 0 14px; color: var(--text); }
.about-body .lead { color: var(--muted); font-size: 15px; margin-bottom: 28px; }
.about-body a.btn {
  display: inline-block; margin-top: 6px; background: var(--brand); color: white;
  text-decoration: none; padding: 10px 18px; border-radius: 8px; font-weight: 700; font-size: 14px;
}
.disclaimer-box {
  background: var(--amber-bg); border: 1px solid var(--amber-border); color: var(--amber-text);
  border-radius: 10px; padding: 16px 18px; font-size: 13.5px; margin: 20px 0; line-height: 1.6;
}

/* ---------- Footer ---------- */
.site-footer {
  margin-top: 40px;
  background: var(--brand-darker);
  color: rgba(255,255,255,0.75);
  padding: 30px 20px 24px;
  font-size: 13px;
}
.site-footer .wrap { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 8px; }
.site-footer .fb { font-weight: 800; color: white; font-size: 15px; }
.site-footer .footer-links { display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; margin-top: 6px; }
.site-footer .footer-links a { text-decoration: none; opacity: 0.85; }
.site-footer .footer-links a:hover { opacity: 1; }
.site-footer .fine-print { font-size: 11.5px; opacity: 0.6; margin-top: 10px; max-width: 560px; }

/* ---------- Shopping list ---------- */
.shopping-list-toggle {
  position: fixed; bottom: 20px; right: 20px; z-index: 45;
  background: var(--accent); color: white; border: none; border-radius: 999px;
  padding: 14px 22px; font-size: 14px; font-weight: 700; cursor: pointer; font-family: inherit;
  box-shadow: 0 6px 18px rgba(194,65,12,0.35);
}
.shopping-list-toggle:hover { background: var(--accent-dark); }
.shopping-list-panel {
  position: fixed; bottom: 0; right: 0; width: 380px; max-width: 94vw; max-height: 80vh;
  background: white; border-radius: 16px 0 0 0; box-shadow: 0 -6px 24px rgba(17,24,39,0.18);
  padding: 18px; overflow-y: auto; display: none; z-index: 46;
}
.shopping-list-panel.open { display: block; }
.shopping-list-panel h3 { margin: 0 0 12px; font-size: 16px; font-weight: 800; }
.shopping-list-panel .sl-item {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 13px; padding: 8px 0; border-bottom: 1px solid var(--border);
}
.shopping-list-panel .sl-remove {
  border: none; background: var(--brand-light); color: var(--brand); cursor: pointer;
  font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 6px;
}
.shopping-list-panel .sl-empty { color: var(--muted); font-size: 13px; }
.compare-btn {
  width: 100%; margin-top: 14px; padding: 11px; border: none; border-radius: 10px;
  background: var(--accent); color: white; font-weight: 700; font-size: 13.5px; cursor: pointer;
  font-family: inherit;
}
.compare-btn:hover { background: var(--accent-dark); }
.compare-results { margin-top: 14px; border-top: 1px solid var(--border); padding-top: 10px; }
.compare-results .store-result { display: flex; justify-content: space-between; font-size: 13px; padding: 7px 0; }
.compare-results .store-result.best {
  font-weight: 800; color: var(--success); background: var(--success-light);
  margin: 0 -8px; padding: 7px 8px; border-radius: 8px;
}
.compare-results .coverage { color: var(--muted); font-size: 11px; font-weight: 400; }
.compare-note { font-size: 11px; color: var(--muted); margin-top: 8px; line-height: 1.5; }

/* ============================================================
   Mobile responsive rules — the site had NONE of these before
   the launch-readiness audit; without a viewport tag + these
   rules, phones were rendering a shrunk-down desktop layout.
   ============================================================ */
@media (max-width: 720px) {
  .header-top { padding: 10px 14px; gap: 10px; }
  .brand-row .wordmark { font-size: 17px; }
  .header-search { order: 3; max-width: 100%; flex-basis: 100%; }
  .nav-links { order: 2; font-size: 12.5px; gap: 12px; }
  .header-bottom .wrap { padding: 7px 14px; }

  .hero { padding: 28px 14px 26px; }
  .hero h1 { font-size: 25px; }
  .hero p.sub { font-size: 13.5px; }
  .stat-row { gap: 8px; }
  .stat-chip { font-size: 12px; padding: 7px 12px; }

  .page-header { padding: 16px 14px; }
  .page-header h1 { font-size: 20px; }

  .wrap { padding: 0 14px; }
  .toolbar-inner { gap: 8px; }
  .toolbar select { flex: 1; min-width: 0; }
  .pill-row { width: 100%; overflow-x: auto; flex-wrap: nowrap; padding-bottom: 2px; }
  .pill { flex-shrink: 0; }

  .grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
  .card { padding: 12px; }
  .card .name { font-size: 13.5px; min-height: 36px; }
  .card .sale-price { font-size: 18px; }

  .shopping-list-toggle { bottom: 14px; right: 14px; padding: 12px 18px; font-size: 13px; }
  .shopping-list-panel { width: 100%; max-width: 100vw; border-radius: 16px 16px 0 0; }

  .about-body { padding: 24px 16px 48px; }
  .about-body h1 { font-size: 23px; }
}
"""

# --- Shared JS: the smarter, typo-tolerant search (no AI backend needed) ---
# PLAIN-ENGLISH NOTE: this is NOT a call to an AI service — it runs entirely
# in the page itself, no internet connection or server needed beyond the
# file you already opened. It forgives typos (spelling something 1-2
# letters wrong still matches, via "edit distance") and understands basic
# plurals and a handful of common grocery nicknames (e.g. "chix" -> chicken,
# "soda" -> cola). A search bar that truly understands intent, not just
# fuzzy spelling, would need a real AI backend — see the roadmap banner.
SMART_SEARCH_JS = """
const SEARCH_SYNONYMS = {
  chix: "chicken", chkn: "chicken", poultry: "chicken", hen: "chicken",
  soda: "cola", pop: "cola", coke: "cola",
  veggie: "vegetable", veggies: "vegetable", veg: "vegetable",
  cookies: "cookie", crackers: "cracker",
  choc: "chocolate", chox: "chocolate",
  bev: "beverage", drink: "beverage", drinks: "beverage",
  sweets: "candy", candies: "candy",
  bagel: "bagel", bagels: "bagel",
  taters: "potato", tots: "potato",
  bud: "produce", veges: "vegetable",
};

function levenshtein(a, b) {
  if (a === b) return 0;
  const al = a.length, bl = b.length;
  if (al === 0) return bl;
  if (bl === 0) return al;
  let prev = [];
  for (let j = 0; j <= bl; j++) prev[j] = j;
  for (let i = 1; i <= al; i++) {
    const cur = [i];
    for (let j = 1; j <= bl; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
    }
    prev = cur;
  }
  return prev[bl];
}

function normalizeSearchToken(t) {
  t = t.toLowerCase();
  if (SEARCH_SYNONYMS[t]) return SEARCH_SYNONYMS[t];
  if (t.length > 4 && t.endsWith("ies")) return t.slice(0, -3) + "y";
  if (t.length > 4 && t.endsWith("es")) return t.slice(0, -2);
  if (t.length > 3 && t.endsWith("s") && !t.endsWith("ss")) return t.slice(0, -1);
  return t;
}

function tokenizeSearch(text) {
  return text.toLowerCase().replace(/[^a-z0-9\\s]/g, " ").split(/\\s+/)
    .filter(Boolean).map(normalizeSearchToken);
}

function fuzzyMatchesQuery(itemName, query) {
  const qTokens = tokenizeSearch(query);
  if (qTokens.length === 0) return true;
  const itemTokens = tokenizeSearch(itemName);
  return qTokens.every(qt => {
    const maxDist = qt.length <= 4 ? 1 : 2;
    return itemTokens.some(it => {
      if (it.startsWith(qt) || qt.startsWith(it)) return true;
      return levenshtein(qt, it) <= maxDist;
    });
  });
}
"""

# --- Shared JS: shopping list storage + the price-comparison "optimizer" ---
SHOPPING_LIST_JS = """
const LIST_KEY = "kartcompare_shopping_list";
const STOPWORDS = new Set(["oz","lb","lbs","pk","pack","ct","count","all","the","and","or",
  "with","varieties","variety","each","ea","family","bag","box","bottle","can","jar","only",
  "original","imported","american","fresh","large","small","mini","super","sale","special"]);

function getList() {
  try { return JSON.parse(localStorage.getItem(LIST_KEY)) || []; }
  catch (e) { return []; }
}
function saveList(list) { localStorage.setItem(LIST_KEY, JSON.stringify(list)); }
function isInList(id) { return getList().some(x => x.id === id); }
function toggleListItem(deal) {
  let list = getList();
  const idx = list.findIndex(x => x.id === deal.id);
  if (idx === -1) list.push(deal);
  else list.splice(idx, 1);
  saveList(list);
  renderShoppingListPanel();
  return idx === -1;
}

function tokenize(name) {
  return name.toLowerCase()
    .replace(/[^a-z0-9\\s]/g, " ")
    .split(/\\s+/)
    .filter(w => w.length >= 3 && !STOPWORDS.has(w) && isNaN(w));
}

function matchScore(tokensA, tokensB) {
  const setB = new Set(tokensB);
  let shared = 0;
  tokensA.forEach(t => { if (setB.has(t)) shared++; });
  return shared;
}

function toggleListPanel() { document.getElementById("slPanel").classList.toggle("open"); }

function compareCheapestStores() {
  const list = getList();
  const resultsEl = document.getElementById("compareResults");
  if (!resultsEl) return;
  if (list.length === 0) {
    resultsEl.innerHTML = '<div class="sl-empty">Add a few items first.</div>';
    return;
  }
  if (!window.ALL_DEALS || window.ALL_DEALS.length === 0) {
    resultsEl.innerHTML = '<div class="sl-empty">Still loading deal data\\u2026 try again in a second.</div>';
    return;
  }

  // For each saved item, find the best (lowest-price) match at every store
  // that has something with overlapping meaningful words.
  const perItemMatches = list.map(item => {
    const itemTokens = tokenize(item.item_name);
    const matches = window.ALL_DEALS
      .map(d => ({ deal: d, score: matchScore(itemTokens, tokenize(d.item_name)) }))
      .filter(m => m.score > 0)
      .sort((a, b) => (b.score - a.score) || (a.deal.sale_price - b.deal.sale_price));
    return { item, matches };
  });

  // Tally per store: cheapest matching price per item, only counting a
  // store once per item (its best match for that item).
  const storeTotals = {};
  perItemMatches.forEach(({ item, matches }) => {
    const seenStores = new Set();
    matches.forEach(m => {
      if (seenStores.has(m.deal.store)) return;
      seenStores.add(m.deal.store);
      if (!storeTotals[m.deal.store]) storeTotals[m.deal.store] = { total: 0, count: 0 };
      storeTotals[m.deal.store].total += m.deal.sale_price;
      storeTotals[m.deal.store].count += 1;
    });
  });

  const ranked = Object.entries(storeTotals)
    .map(([store, v]) => ({ store, total: v.total, count: v.count }))
    .sort((a, b) => (b.count - a.count) || (a.total - b.total));

  if (ranked.length === 0) {
    resultsEl.innerHTML = '<div class="sl-empty">No similar items found at any store yet — try more generic item names (e.g. "chicken", "milk").</div>';
    return;
  }

  resultsEl.innerHTML = '<div style="font-weight:700;font-size:12px;margin-bottom:6px;">Cheapest match by store:</div>' +
    ranked.map((r, i) => `
      <div class="store-result ${i === 0 ? 'best' : ''}">
        <span>${r.store} <span class="coverage">(${r.count} of ${list.length} items matched)</span></span>
        <span>$${r.total.toFixed(2)}</span>
      </div>
    `).join("") +
    '<div class="compare-note">Matching is based on shared words in the product name (a first pass, not exact product matching) — coverage shows how many of your items that store had something similar for. Store with the most items covered is ranked first, cheapest total breaks ties.</div>';
}

function renderShoppingListPanel() {
  const panel = document.getElementById("slPanel");
  const list = getList();
  const countEl = document.getElementById("slCount");
  if (countEl) countEl.textContent = list.length;
  if (!panel) return;
  const body = panel.querySelector(".sl-body");
  if (list.length === 0) {
    body.innerHTML = '<div class="sl-empty">No items saved yet. Click "+ Add" on any deal.</div>';
  } else {
    body.innerHTML = list.map(item => `
      <div class="sl-item">
        <span>${item.item_name} <strong>$${item.sale_price.toFixed(2)}</strong> <em style="color:#999">(${item.store})</em></span>
        <button class="sl-remove" data-id="${item.id}">remove</button>
      </div>
    `).join("");
    body.querySelectorAll(".sl-remove").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = Number(btn.dataset.id);
        let list = getList().filter(x => x.id !== id);
        saveList(list);
        renderShoppingListPanel();
      });
    });
  }
  const resultsEl = document.getElementById("compareResults");
  if (resultsEl) resultsEl.innerHTML = "";
}
document.addEventListener("DOMContentLoaded", renderShoppingListPanel);
"""

SHOPPING_LIST_HTML = """
<button class="shopping-list-toggle" onclick="toggleListPanel()">Shopping List (<span id="slCount">0</span>)</button>
<div class="shopping-list-panel" id="slPanel">
  <h3>My Shopping List</h3>
  <div class="sl-body"></div>
  <button class="compare-btn" onclick="compareCheapestStores()">Find cheapest store for this list</button>
  <div class="compare-results" id="compareResults"></div>
</div>
"""

ROADMAP_HTML = f"""
<div class="roadmap-banner">
  <strong>Coming next for {BRAND_NAME}:</strong> wine store deals alongside groceries, showing which wine
  shops are nearest each grocery store on your list, plus a smarter search bar that understands what you
  mean (not just keyword matches). The "Find cheapest store for this list" tool above is the first version
  of the full cart-comparison feature.
</div>
"""


def store_nav_links(stores, current_slug=None):
    links = []
    for s in stores:
        cls = ' class="current"' if s["slug"] == current_slug else ""
        links.append(f'<a href="{s["slug"]}.html"{cls}>{s["name"]}</a>')
    return "".join(links)


def nav_block(stores, current_slug=None, about_current=False):
    home_cls = ' class="current"' if current_slug is None and not about_current else ""
    about_cls = ' class="current"' if about_current else ""
    return (
        f'<a href="index.html"{home_cls}>Home</a>'
        f'<a href="about.html"{about_cls}>About</a>'
        f'{store_nav_links(stores, current_slug=current_slug)}'
    )


def footer_html(stores, current_slug=None, about_current=False):
    return f"""
<div class="site-footer">
  <div class="wrap">
    <div class="fb">{BRAND_NAME}</div>
    <div>{BRAND_TAGLINE}</div>
    <div class="footer-links">
      {nav_block(stores, current_slug=current_slug, about_current=about_current)}
      <a href="mailto:{CONTACT_EMAIL}?subject=Wrong%20price%20on%20Kart%20Compare">Report a wrong price</a>
    </div>
    <div class="fine-print">Prices and sale dates are scraped from each store's own site and may change without notice. Always confirm at checkout. {BRAND_NAME} is an independent, unofficial project and is not affiliated with the stores listed.</div>
  </div>
</div>"""


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
{head_tags}
<style>{css}</style>
</head>
<body>
<div class="site-header">
  <div class="header-top">
    <a class="brand-row" href="index.html">
      {logo}
      <span class="wordmark">{brand_name}</span>
    </a>
    <div class="header-search">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" id="search" placeholder="Search all items (typos OK)...">
    </div>
    <div class="nav-links">
      {nav}
    </div>
  </div>
  <div class="header-bottom">
    <div class="wrap"><span class="page-sub">{nav_right}</span></div>
  </div>
</div>
{hero_section}
<div class="wrap">
{date_banner}
{extra_body}
<div class="toolbar">
  <div class="toolbar-inner">
    {store_filter}
    <div class="pill-row" id="categoryPills"></div>
  </div>
  <div class="count" id="count"></div>
</div>
<div class="grid" id="grid"></div>
<div class="empty" id="empty" style="display:none;">No deals match your search/filters.</div>
</div>
{shopping_list_html}
{footer}
{analytics}
<script>
const ICONS = {icons_json};
const CURRENT_STORE_SLUG = "{store_slug_js}"; // "" means show every store (homepage)
window.ALL_DEALS = [];
let DEALS = [];

const grid = document.getElementById("grid");
const searchInput = document.getElementById("search");
const storeSelect = document.getElementById("storeFilter");
const countEl = document.getElementById("count");
const emptyEl = document.getElementById("empty");
let activeCategory = "";

{smart_search_js}

{toggle_list_js}

function populateSelect(select, values) {{
  if (!select) return;
  [...new Set(values)].sort().forEach(v => {{
    const opt = document.createElement("option");
    opt.value = v; opt.textContent = v;
    select.appendChild(opt);
  }});
}}

function populateCategoryPills(values) {{
  const pillRow = document.getElementById("categoryPills");
  if (!pillRow) return;
  const cats = [...new Set(values)].sort();
  let html = '<button type="button" class="pill active" data-cat="">All</button>';
  cats.forEach(c => {{
    html += `<button type="button" class="pill" data-cat="${{c}}">${{ICONS[c] || ""}} ${{c}}</button>`;
  }});
  pillRow.innerHTML = html;
  pillRow.querySelectorAll(".pill").forEach(btn => {{
    btn.addEventListener("click", () => {{
      pillRow.querySelectorAll(".pill").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeCategory = btn.dataset.cat;
      render();
    }});
  }});
}}

function render() {{
  const q = searchInput.value.trim().toLowerCase();
  const store = storeSelect ? storeSelect.value : "";
  const category = activeCategory;
  const filtered = DEALS.filter(d => {{
    if (store && d.store !== store) return false;
    if (category && d.category !== category) return false;
    if (q && !fuzzyMatchesQuery(d.item_name, q)) return false;
    return true;
  }});
  grid.innerHTML = "";
  countEl.textContent = filtered.length + " of " + DEALS.length + " deals";
  emptyEl.style.display = filtered.length ? "none" : "block";
  filtered.forEach(d => {{
    const card = document.createElement("div");
    card.className = "card";
    const unitNote = d.unit ? `<div class="unit-note">${{d.unit}}</div>` : "";
    const oldPrice = d.original_price ? `<span class="old-price">$${{d.original_price.toFixed(2)}}</span>` : "";
    const pctOff = d.original_price && d.original_price > d.sale_price
      ? Math.round((1 - d.sale_price / d.original_price) * 100) : null;
    const savingsBadge = pctOff ? `<span class="savings-badge">-${{pctOff}}%</span>` : "";
    const storeTag = {show_store_js} ? `<div class="store-tag">${{d.store}}</div>` : "";
    const already = isInList(d.id);
    card.innerHTML = `
      <div class="icon-row">
        <span class="icon-badge">${{ICONS[d.category] || "\U0001F6D2"}}</span>
        ${{savingsBadge}}
      </div>
      <span class="cat-tag">${{d.category}}</span>
      <div class="name">${{d.item_name}}</div>
      ${{storeTag}}
      <div class="price-row">
        <span class="sale-price">$${{d.sale_price.toFixed(2)}}</span>
        ${{oldPrice}}
      </div>
      ${{unitNote}}
      <button class="add-btn ${{already ? 'added' : ''}}" data-id="${{d.id}}">${{already ? '\\u2713 Added' : '+ Add'}}</button>
    `;
    card.querySelector(".add-btn").addEventListener("click", function() {{
      const added = toggleListItem(d);
      this.classList.toggle("added", added);
      this.textContent = added ? "\\u2713 Added" : "+ Add";
    }});
    grid.appendChild(card);
  }});
}}

fetch("deals.json")
  .then(r => {{ if (!r.ok) throw new Error("bad response " + r.status); return r.json(); }})
  .then(data => {{
    window.ALL_DEALS = data.deals;
    DEALS = CURRENT_STORE_SLUG ? window.ALL_DEALS.filter(d => d.store_slug === CURRENT_STORE_SLUG) : window.ALL_DEALS;
    if (storeSelect) populateSelect(storeSelect, DEALS.map(d => d.store));
    populateCategoryPills(DEALS.map(d => d.category));
    render();
  }})
  .catch(err => {{
    countEl.textContent = "";
    grid.innerHTML = "";
    emptyEl.style.display = "block";
    emptyEl.innerHTML = "Couldn't load deal data (" + err.message + "). If you opened this file by double-clicking it instead of through a real website, that's expected \\u2014 browsers block a local file from loading its data file for security reasons. This works normally once it's hosted (e.g. on GitHub Pages) or if you run a local preview server \\u2014 see the About page.";
  }});

searchInput.addEventListener("input", render);
if (storeSelect) storeSelect.addEventListener("change", render);
{pwa_register_js}
</script>
</body>
</html>
"""


ABOUT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
{head_tags}
<style>{css}</style>
</head>
<body>
<div class="site-header">
  <div class="header-top">
    <a class="brand-row" href="index.html">
      {logo}
      <span class="wordmark">{brand_name}</span>
    </a>
    <div class="nav-links">
      {nav}
    </div>
  </div>
</div>
<div class="about-body">
  <h1>About {brand_name}</h1>
  <p class="lead">{tagline}</p>

  <div class="disclaimer-box">
    <strong>{brand_name} is an independent, unofficial project.</strong> It is not built, run, endorsed,
    or affiliated with any of the stores listed. It exists to make it easier to compare public sale prices
    that each store already publishes on their own website.
  </div>

  <h2>What this is</h2>
  <p>{brand_name} collects this week's sale prices directly from each store's own public website and lays
  them out side by side, with search, category filters, and a shopping-list tool that estimates which store
  is cheapest for a whole list of items.</p>

  <h2>How the data gets here</h2>
  <p>Every price on this site is read directly from the store's own website or published flyer &mdash;
  nothing is estimated or made up. Some stores publish an exact "sale valid through" date; where they
  don't, this site shows an honest estimated window instead of guessing at a date, clearly labeled either way.</p>

  <h2>How fresh is this?</h2>
  <p>Every page shows when its prices were last checked. Sale prices can and do change without notice,
  sometimes within just a few days &mdash; always treat the price at checkout as the real one.</p>

  <h2>Something look wrong?</h2>
  <p>If a price looks off, or a store's page seems out of date, please let us know &mdash; it helps keep
  this useful for everyone.</p>
  <a class="btn" href="mailto:{contact_email}?subject=Wrong%20price%20on%20Kart%20Compare">Report a wrong price</a>

  <h2>Where this is headed</h2>
  <p>Wine store deals alongside groceries, a smarter search that understands what you mean rather than just
  matching keywords, and a more complete shopping-list price comparison across full store catalogs, not just
  this week's specials.</p>
</div>
{footer}
{analytics}
</body>
</html>
"""


def render_date_banner(store_slug, deals):
    meta = STORE_META[store_slug]
    if not deals:
        return f"""
        <div class="date-banner estimated">
          <span class="big">No deals currently available</span>
          <span>{meta['note']}</span>
        </div>"""
    d_from, d_to = deals[0]["date_valid_from"], deals[0]["date_valid_to"]
    cls = "confirmed" if meta["dates_confirmed"] else "estimated"
    label = "Confirmed sale dates" if meta["dates_confirmed"] else "Estimated sale window"
    return f"""
    <div class="date-banner {cls}">
      <span class="big">Data last checked {date.today().isoformat()} &middot; {label}: {d_from} to {d_to}</span>
      <span>{meta['note']}</span>
    </div>"""


def build_store_page(store_slug, store_name, deals, stores):
    banner = render_date_banner(store_slug, deals)
    meta = STORE_META[store_slug]
    if meta.get("kosher_note"):
        banner += f"""
    <div class="date-banner estimated">
      <span class="big">Not a dedicated kosher grocer</span>
      <span>{meta['kosher_note']}</span>
    </div>"""
    date_note = "confirmed sale dates" if meta["dates_confirmed"] else "an estimated sale window"
    page_header = f"""
    <div class="page-header">
      <div class="wrap">
        <h1>{store_name} deals</h1>
        <div class="sub">{len(deals)} current specials &middot; {date_note} &middot; <span class="muted-part">data last checked {date.today().isoformat()}</span></div>
      </div>
    </div>"""
    description = f"{len(deals)} current sale prices at {store_name} in Lakewood, NJ, compared side by side on {BRAND_NAME}."
    html = PAGE_TEMPLATE.format(
        head_tags=head_tags(f"{store_name} Deals — {BRAND_NAME}", description, f"{store_slug}.html"),
        css=BASE_CSS,
        logo=LOGO_SVG,
        brand_name=BRAND_NAME,
        nav=nav_block(stores, current_slug=store_slug),
        nav_right=f"{len(deals)} deals at {store_name}",
        hero_section=page_header,
        date_banner=banner,
        store_filter="",
        extra_body="",
        shopping_list_html=SHOPPING_LIST_HTML,
        footer=footer_html(stores, current_slug=store_slug),
        analytics=ANALYTICS_SNIPPET,
        icons_json=json.dumps(ICONS),
        store_slug_js=store_slug,
        toggle_list_js=SHOPPING_LIST_JS,
        smart_search_js=SMART_SEARCH_JS,
        pwa_register_js=PWA_REGISTER_JS,
        show_store_js="false",
    )
    return html


def build_homepage(all_deals, stores):
    store_cards = []
    for i, s in enumerate(stores):
        slug = s["slug"]
        store_deals = [d for d in all_deals if d["store_slug"] == slug]
        meta = STORE_META[slug]
        initial = s["name"][0].upper()
        if store_deals:
            d_from, d_to = store_deals[0]["date_valid_from"], store_deals[0]["date_valid_to"]
            cls = "confirmed" if meta["dates_confirmed"] else "estimated"
            date_line = f'<span class="d {cls}">{d_from} &ndash; {d_to}</span>'
        else:
            date_line = '<span class="d estimated">No current deals</span>'
        store_cards.append(f"""
        <a class="store-card" href="{slug}.html">
          <span class="avatar">{initial}</span>
          <h3>{s['name']}</h3>
          <span class="n">{len(store_deals)} deals</span>
          {date_line}
        </a>""")

    hero = f"""
    <div class="hero">
      <div class="wrap">
        <h1>{BRAND_NAME}</h1>
        <p class="sub">{BRAND_TAGLINE}</p>
        <div class="stat-row">
          <span class="stat-chip"><strong>{len(all_deals)}</strong> deals tracked</span>
          <span class="stat-chip"><strong>{len(stores)}</strong> Lakewood stores</span>
          <span class="stat-chip fresh">Data last checked <strong>{date.today().isoformat()}</strong></span>
        </div>
      </div>
    </div>"""

    banner = """
    <div class="date-banner confirmed">
      <span class="big">Real deals, scraped directly from each store</span>
      <span>Some stores publish exact sale-valid dates; others don't — check each store's page for details.</span>
    </div>"""

    extra_body = f"""
    <div class="section-title">Browse by store</div>
    <div class="section-sub">Jump straight to a store's full list of specials.</div>
    <div class="store-grid">{''.join(store_cards)}</div>
    {ROADMAP_HTML}
    <div class="section-title">All deals</div>
    <div class="section-sub">Search, filter by store or category, or build a shopping list below.</div>
    """

    html = PAGE_TEMPLATE.format(
        head_tags=head_tags(f"{BRAND_NAME} — {BRAND_TAGLINE}", BRAND_TAGLINE, "index.html"),
        css=BASE_CSS,
        logo=LOGO_SVG,
        brand_name=BRAND_NAME,
        nav=nav_block(stores, current_slug=None),
        nav_right="Home",
        hero_section=hero,
        date_banner=banner,
        store_filter='<select id="storeFilter"><option value="">All Stores</option></select>',
        extra_body=extra_body,
        shopping_list_html=SHOPPING_LIST_HTML,
        footer=footer_html(stores, current_slug=None),
        analytics=ANALYTICS_SNIPPET,
        icons_json=json.dumps(ICONS),
        store_slug_js="",
        toggle_list_js=SHOPPING_LIST_JS,
        smart_search_js=SMART_SEARCH_JS,
        pwa_register_js=PWA_REGISTER_JS,
        show_store_js="true",
    )
    return html


def build_about_page(stores):
    description = f"What {BRAND_NAME} is, how the data is gathered, and how to report a wrong price. An independent, unofficial project."
    html = ABOUT_TEMPLATE.format(
        head_tags=head_tags(f"About — {BRAND_NAME}", description, "about.html"),
        css=BASE_CSS,
        logo=LOGO_SVG,
        brand_name=BRAND_NAME,
        tagline=BRAND_TAGLINE,
        nav=nav_block(stores, current_slug=None, about_current=True),
        footer=footer_html(stores, current_slug=None, about_current=True),
        analytics=ANALYTICS_SNIPPET,
        contact_email=CONTACT_EMAIL,
    )
    return html


MANIFEST_JSON = json.dumps({
    "name": BRAND_NAME,
    "short_name": BRAND_NAME,
    "description": BRAND_TAGLINE,
    "start_url": "index.html",
    "scope": ".",
    "display": "standalone",
    "background_color": "#F7F7FB",
    "theme_color": "#4F46E5",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
    ],
}, indent=2)

# Minimal service worker: caches the app shell so a second visit (and basic
# offline access) is fast, without adding real complexity. It does NOT try
# to cache deals.json, so prices are always fetched fresh over the network.
SERVICE_WORKER_JS = """
const CACHE_NAME = "kartcompare-shell-v1";
const SHELL_FILES = ["index.html", "manifest.json", "icon-192.png", "icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Never cache the live deals data -- always go to the network for that.
  if (event.request.url.includes("deals.json")) return;
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
"""


def main():
    data = json.loads(DATA_PATH.read_text())
    all_deals = data["deals"]
    stores = data["stores"]

    SITE_DIR.mkdir(exist_ok=True)

    # One shared data file, fetched by every page, instead of the whole
    # dataset being duplicated inline on every single HTML file.
    (SITE_DIR / "deals.json").write_text(json.dumps({"deals": all_deals, "stores": stores}))
    print(f"Built site/deals.json ({len(all_deals)} deals, shared by every page)")

    (SITE_DIR / "manifest.json").write_text(MANIFEST_JSON)
    print("Built site/manifest.json")
    (SITE_DIR / "sw.js").write_text(SERVICE_WORKER_JS)
    print("Built site/sw.js")

    for s in stores:
        slug = s["slug"]
        store_deals = [d for d in all_deals if d["store_slug"] == slug]
        html = build_store_page(slug, s["name"], store_deals, stores)
        (SITE_DIR / f"{slug}.html").write_text(html)
        print(f"Built site/{slug}.html ({len(store_deals)} deals)")

    homepage_html = build_homepage(all_deals, stores)
    (SITE_DIR / "index.html").write_text(homepage_html)
    print(f"Built site/index.html ({len(all_deals)} deals total)")

    about_html = build_about_page(stores)
    (SITE_DIR / "about.html").write_text(about_html)
    print("Built site/about.html")


if __name__ == "__main__":
    main()
