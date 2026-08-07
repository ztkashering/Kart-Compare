"""
base_scraper.py — shared helpers every store scraper (HTML or PDF) can reuse.

Plain English: flyers write prices in a "squashed" way — "$199" printed on
a circular actually means $1.99 (the original design shows the cents as a
small raised number; once the text is pulled out of the PDF, the decimal
point disappears). This file has the logic to turn that back into a real
price, plus a simple keyword-based guesser that sorts an item into
Produce / Meat / Dairy / Bakery / Pantry.
"""

import re
from datetime import date, timedelta

# --- Sale-week calculation -----------------------------------------------
# PLAIN-ENGLISH NOTE (added 2026-08-06, from the founder's own real-world
# knowledge of these stores): Seasons, Nutmeg, Kosher West, and Kosher
# Village don't publish an exact "sale valid through" date anywhere on
# their site, but their specials actually run on a fixed weekly pattern:
# Wednesday morning through Tuesday night. That's a much better estimate
# than a generic "7 days from whenever we happened to scrape" window,
# which could land in the middle of a cycle and be wrong by several days.
# This still isn't an OFFICIALLY confirmed date (the store itself doesn't
# publish it), so it's still labeled "estimated" on the site — just a
# well-informed estimate instead of a rough guess.


def current_wed_to_tue_window(today: date | None = None) -> tuple[str, str]:
    """Return (date_valid_from, date_valid_to) as ISO date strings for the
    Wednesday-to-Tuesday sale week that `today` falls in."""
    if today is None:
        today = date.today()
    # date.weekday(): Monday=0 ... Wednesday=2 ... Sunday=6
    days_since_wed = (today.weekday() - 2) % 7
    week_start = today - timedelta(days=days_since_wed)
    week_end = week_start + timedelta(days=6)
    return week_start.isoformat(), week_end.isoformat()


# --- Price parsing -----------------------------------------------------

# Matches things like "3/$4", "10/$4", "2/88cents" (multi-buy deals)
MULTI_BUY_RE = re.compile(r"\b(\d{1,2})\s*/\s*\$?(\d+(?:\.\d{2})?)(cents)?\b", re.I)

# Matches flyer-style dollar prices with no decimal point, e.g. "$199", "$1999".
# No trailing \b here on purpose — flyers often glue a unit straight onto the
# price with no space ("$289lb."), and \b would refuse to match right before
# a letter, silently dropping every priced-per-pound item (found this the
# hard way: it was eating the entire Meat & Poultry section).
FLYER_DOLLAR_RE = re.compile(r"\$(\d{2,5})")

# Matches plain cents prices, e.g. "99cents", "88centslb" — same reasoning,
# no trailing \b so a glued-on unit doesn't block the match.
CENTS_RE = re.compile(r"\b(\d{2,3})\s*cents", re.I)


def parse_flyer_price(token: str) -> float | None:
    """Convert a raw flyer price token into a float dollar amount.

    Examples:
        "$199"   -> 1.99
        "$1999"  -> 19.99
        "$549"   -> 5.49
        "99cents"-> 0.99
    Flyer prices always encode the last two digits as cents.
    """
    m = FLYER_DOLLAR_RE.search(token)
    if m:
        digits = m.group(1)
        dollars = digits[:-2] or "0"
        cents = digits[-2:]
        return float(f"{dollars}.{cents}")

    m = CENTS_RE.search(token)
    if m:
        return float(m.group(1)) / 100

    return None


def parse_multi_buy(token: str) -> tuple[int, float] | None:
    """Convert "3/$4" -> (3, 4.00), "2/88cents" -> (2, 0.88)."""
    m = MULTI_BUY_RE.search(token)
    if not m:
        return None
    qty = int(m.group(1))
    amount = float(m.group(2))
    if m.group(3):  # "cents" suffix means amount is already in cents
        amount = amount / 100
    return qty, amount


# --- Category guessing ---------------------------------------------------

# PLAIN-ENGLISH NOTE on this list (expanded 2026-08-06): the real stores
# organize their sites into 10-12 departments (Dairy, Meat, Beverages,
# Household, Health & Beauty, etc.) but that department label isn't part
# of the text we scrape from the "Specials" feed — it's only visible if
# you browse each department page separately, which today's scraper
# doesn't do. So this is still a best-effort guess from the item's name,
# just with a much bigger, more specific keyword list than before (10
# categories instead of 5) to get closer to the real store departments
# without needing a bigger scraping rewrite. It won't be perfect — a
# word like "pretzel" can mean a bakery item or a snack-aisle item — but
# it's a real step up, and anything that doesn't match falls into
# "Pantry" as a safe catch-all rather than a wrong guess.
CATEGORY_KEYWORDS = {
    "Produce": [
        "avocado", "eggplant", "cucumber", "tomato", "onion", "carrot",
        "mango", "strawberr", "produce", "lettuce", "pepper", "potato",
        "fruit", "vegetable", "grape", "cherries", "cherry", "nectarine",
        "orange ", "lemon", "lime", "scallion", "shallot", "turnip",
        "cabbage", "celery", "squash", "parsley", "dill", "cauliflower",
        "broccoli", "apple", "pineapple", "cantaloupe", "watermelon",
        "berries", "berry", "plum", "peach", "banana", "kiwi",
    ],
    "Meat & Deli": [
        "chicken", "beef", "steak", "brisket", "pastrami", "salami",
        "franks", "patties", "nugget", "veal", "turkey", "meat", "rib",
        "flanken", "london broil", "wing", "sausage", "kishka", "arayes",
        "shoulder", "fillet", "fish", "salmon", "tuna", "flounder", "sole",
        "lox", "tilapia", "gefilte", "sushi", "kielbasa", "hot dog",
        "hotdog", "kugel", "cutlets", "ham", "bratwurst", "brisket",
    ],
    "Dairy": [
        "cheese", "yogurt", "milk", "leben", "cream cheese", "butter",
        "mozzarella", "muenster", "gouda", "feta", "cottage cheese",
        "sour cream",
    ],
    "Bakery": [
        "bread", "bagel", "cake", "cupcake", "roll", "danish",
        "babka", "challah", "donut", "kichel", "biscuit", "pita",
        "farfel", "matzo", "mezonos", "pie crust", "pastry",
    ],
    "Beverages": [
        "juice", "soda", "seltzer", "water bottle", " tea", "coffee",
        " cola", "gatorade", "snapple", "sprite", "lemonade", "smart water",
        "fresca", "grape juice", "probiotic water",
    ],
    "Frozen": [
        "frozen", "ice pop", "popsicle", "gelato", "ice cream",
        "italian ice", "freeze pop", "jonny pops",
    ],
    "Candy & Snacks": [
        "candy", "chocolate", "gummy", "gummies", "licorice", "taffy",
        "marshmallow", "chips", "cookie", "cracker", "wafer", "popcorn",
        "bissli", "sour stick", "fruit leather", "twizzlers", "pretzel",
        "snack", "nosh",
    ],
    "Household": [
        "paper plate", "plastic cup", "napkin", "tissue", "foil",
        "detergent", "dish soap", "disposable", "cutlery", "aluminum",
        "trash bag", "plates,", "plastic bowl", "forks", "spoons",
        "pans", "parchment",
    ],
    "Health & Beauty": [
        "toothpaste", "shampoo", "vitamin", "sunscreen", "deodorant",
        "mouthwash", "floss", "scope", "lotion",
    ],
}


def guess_category(item_name: str) -> str:
    """Best-effort keyword match against the item's name (see the note
    above the keyword list for why this is name-based rather than pulled
    from the store's real department tag). Falls back to 'Pantry' (the
    catch-all for shelf-stable grocery/pantry staples) when nothing
    matches."""
    name_lower = item_name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return category
    return "Pantry"


# --- Standard (non-flyer) price parsing --------------------------------
# Used by store websites that show normal decimal prices, e.g. "$4.69",
# "$11.99 / lb", "3 for $3.00" — unlike the flyer-PDF stores, these
# already have a decimal point so no "squashing" correction is needed.

STANDARD_MULTI_BUY_RE = re.compile(r"(\d{1,2})\s*for\s*\$(\d+(?:\.\d{2})?)", re.I)
STANDARD_PRICE_RE = re.compile(r"\$(\d+(?:\.\d{2})?)")
STANDARD_UNIT_RE = re.compile(r"/\s*(lb|each|ea)\b", re.I)


def parse_standard_price(text: str) -> tuple[float | None, str | None]:
    """Parse a normal (already-decimal) price string into (price, unit).

    Examples:
        "$4.69"          -> (4.69, None)
        "$11.99 / lb"    -> (11.99, "lb")
        "$6.99 / each"   -> (6.99, "each")
        "3 for $3.00"    -> (1.00, "3 for $3.00")
    """
    if not text:
        return None, None
    text = text.strip()

    multi = STANDARD_MULTI_BUY_RE.search(text)
    if multi:
        qty = int(multi.group(1))
        total = float(multi.group(2))
        return round(total / qty, 2), f"{qty} for ${total:.2f}"

    price_match = STANDARD_PRICE_RE.search(text)
    if not price_match:
        return None, None
    price = float(price_match.group(1))

    unit_match = STANDARD_UNIT_RE.search(text)
    unit = unit_match.group(1).lower() if unit_match else None
    return price, unit


def clean_item_name(raw: str) -> str:
    """Collapse whitespace/newlines from a multi-line flyer chunk into one
    readable line, and strip stray punctuation left over from dot-leaders."""
    text = re.sub(r"\.{2,}", " ", raw)          # dot leaders "...."
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" -.")
    return text
