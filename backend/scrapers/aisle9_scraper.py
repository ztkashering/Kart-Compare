"""
aisle9_scraper.py — Aisle 9 (951 Madison Ave, Lakewood, NJ).

STATUS AS OF 2026-08-10: added as a real store on the site (shows up in
navigation, gets its own page), but with NO live deals yet — same honest
"coming soon" treatment as Bingo and ShopRite got before their scrapers
were finished. Do not fabricate placeholder items here; leave `run()`
returning an empty list until the blocker below is actually solved.

WHAT WAS FOUND (research notes for whoever picks this up next):

Aisle 9's site (aisle9market.com) runs on the "My Cloud Grocer" online-
ordering platform. Its front-end component classes are IDENTICAL to the
platform the shared grocery_platform_scraper.py already handles for
Seasons/Nutmeg/Kosher West (`a.product-item-link`, `.product-item-title`,
`.product-item-price`, `.product-item-old-price`) — plus one extra class
this platform uses that the others don't:
`.product-item-special-lbl` — a small "Special" badge shown on a product
card when that item is a genuine sale item (confirmed by inspecting the
real DOM; only items actually marked down carry this span, not every
featured item).

THE BLOCKER: unlike Seasons/Nutmeg/Kosher West (where the location cookie
alone unlocks the specials page), Aisle 9's full product catalog —
including `/lakewood/category/specials` — returns ZERO products
(`productsCount: 0` from their own `/api/AjaxFilter/JsonProductsList`
endpoint) until a delivery or pickup time slot is selected in their
checkout flow (confirmed via `/api/DeliveryTimeSlots/GetDeliveryOnStatus`
returning an empty date/time — nothing had been selected). This is a
bigger step than a simple cookie: it likely requires walking through
their actual delivery/pickup scheduling UI, and possibly an account,
before category pages populate. This was not completed as of 2026-08-10
because it needed more interactive exploration than a single session
allowed, and guessing at the flow risked either fabricating data or
accidentally taking a real action (like starting a real order) on the
founder's behalf.

WHAT DID WORK: the site's HOMEPAGE (`/lakewood`) shows a "Featured
Products" carousel that is NOT gated the same way — real product cards
with real prices render there without needing a delivery slot. Out of 24
featured cards checked on 2026-08-10, exactly 1 carried the
`.product-item-special-lbl` "Special" badge: "Gefen Chicken Noodle Soup
No Msg, 2.3 Oz". Its price fields were genuinely ambiguous, though —
`.product-item-price` showed "12 for $16.99" and `.product-item-old-price`
showed "$1.49", which is backwards from every other store's was/now
pattern (the "old" price was lower than the "new" one). That could mean
a case price vs. a new lower single-unit price, or could mean this
platform uses those two CSS classes for something other than was/now
here. Either way, it's one ambiguous data point, not something safe to
publish as a real, currently-accurate weekly deal — do not use it as
sample data as-is; if a future session tests this again, verify the
was/now meaning is actually understood before saving anything.

NEXT STEPS for whoever picks this up:
  1. Try actually completing Aisle 9's pickup-selection flow in a real
     browser (their store address is 951 Madison Ave, Lakewood NJ 08701,
     StoreId 1, StoreSystemName "A9" — from `/api/multistore/
     StoresDialogJSON`) and see if `/category/specials` populates
     afterward.
  2. If it does, `_extract_items_from_source()` in
     grocery_platform_scraper.py can very likely be reused almost as-is
     (same product-item-link/title/price/old-price classes), just with
     an extra check for `.product-item-special-lbl` to make sure only
     genuinely-marked-down items get counted as a deal, since (unlike
     the other three stores) Aisle 9's category browsing appears to
     include regular-price items mixed in, not just sale items.
  3. If the delivery/pickup requirement can't be scripted, the fallback
     is the same as ShopRite: capture it with a live browser session by
     hand periodically instead of a fully automated scraper.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

STORE_SLUG = "aisle-9"
SPECIALS_URL = "https://aisle9market.com/lakewood/category/specials"


def run(save_to_db: bool = True, limit_preview: int = 8) -> list[dict]:
    print(
        f"[{STORE_SLUG}] No live scraper yet — Aisle 9's full catalog is "
        f"gated behind selecting a delivery/pickup time on their site, "
        f"which hasn't been solved yet. See this file's docstring for "
        f"what's been tried. Returning 0 deals (honest 'coming soon' "
        f"state, not a fabricated placeholder)."
    )
    return []


if __name__ == "__main__":
    run()
