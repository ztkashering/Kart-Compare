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

# Matches cent-SYMBOL prices, e.g. "89 ¢", "99¢", "99 ¢ lb." — found
# 2026-08-12 while auditing Gourmet Glatt: the flyer's own PDF text uses
# the "¢" glyph for anything under a dollar (not the word "cents"), and
# the old CENTS_RE never matched it. That silently broke the whole
# name/price pairing logic downstream in gourmet_glatt_scraper.py's
# parse_deals(): a "¢" price line wasn't recognized as a price line at
# all, so the item name buffer never flushed there — it just kept
# absorbing the NEXT unrelated item's name text too, and that next
# item's real price got wrongly attached to the merged, garbled name
# while the "¢" item's own real price was silently dropped.
CENTS_SYMBOL_RE = re.compile(r"(\d{1,3})\s*¢")


def parse_flyer_price(token: str) -> float | None:
    """Convert a raw flyer price token into a float dollar amount.

    Examples:
        "$199"   -> 1.99
        "$1999"  -> 19.99
        "$549"   -> 5.49
        "99cents"-> 0.99
        "89 ¢"   -> 0.89
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

    m = CENTS_SYMBOL_RE.search(token)
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

# PLAIN-ENGLISH NOTE on this list (expanded 2026-08-06, restructured
# 2026-08-10 into two tiers — see below): the real stores organize their
# sites into 10-12 departments (Dairy, Meat, Beverages, Household, Health
# & Beauty, etc.) but that department label isn't part of the text we
# scrape from the "Specials" feed — it's only visible if you browse each
# department page separately, which today's scraper doesn't do. So this
# is still a best-effort guess from the item's name.
#
# 2026-08-10 bug fix: the original version checked categories in a fixed
# order and returned on the FIRST keyword match anywhere in the name.
# That silently broke on any product whose flavor/ingredient word
# overlapped a produce word — e.g. "Strawberry Yogurt" matched Produce's
# "strawberr" before ever reaching Dairy's "yogurt", so real dairy, candy,
# beverage, and household items were landing in Produce. Concrete examples
# caught in a full audit of the live site: yogurt cups tagged Produce
# (strawberry/blueberry), grape juice tagged Produce instead of Beverages,
# dish detergent tagged Produce (lemon/green-apple scent names), candy
# (Twizzlers, Jolly Rancher, Fruit Riot, Bissli) tagged Produce because of
# a fruit/veggie flavor name, and sushi RICE (a pantry/dry-goods item)
# tagged Meat & Deli just because the word "sushi" appeared.
#
# The fix: two tiers, checked in order.
#   1. STRONG_CATEGORY_KEYWORDS — product-TYPE words (yogurt, candy,
#      detergent, juice, chips, chicken, etc.) that are basically never
#      wrong regardless of what other words share the name. Checked
#      first, across every category.
#   2. WEAK_CATEGORY_KEYWORDS — plain ingredient/flavor words (apple,
#      onion, cherry, grape...) that are only reliable when nothing more
#      specific is present, since fruit/veggie names double as flavors on
#      everything from yogurt to candy to cleaning spray. Only consulted
#      if nothing in tier 1 matched. In practice this is just Produce.
# Anything that matches neither tier falls into "Pantry" as a safe
# catch-all rather than a wrong guess.
STRONG_CATEGORY_KEYWORDS = {
    "Meat & Deli": [
        "chicken", "beef", "steak", "brisket", "pastrami", "salami",
        "franks", "patties", "nugget", "veal", "turkey", "meat", "rib",
        "flanken", "london broil", "wing", "sausage", "kishka", "arayes",
        "shoulder", "kielbasa", "hot dog",
        "hotdog", "cutlets", "ham", "bratwurst", "tongue", "poultry",
        # "tongue"/"poultry" added 2026-08-30 auditing Seasons' real
        # flyer data — "Tongue" (a real deli item, $64.99/lb on that
        # flyer) had no keyword at all and was landing in Pantry;
        # "KJ Poultry Pretzel Leg Tender" (frozen chicken) had no
        # "chicken"/"turkey" match either and was landing in Candy &
        # Snacks via "pretzel" instead.
        # NOTE: "sushi" and "kugel" were removed from this list on
        # 2026-08-10 — sushi RICE and prepared-food kugels aren't meat,
        # and the old blanket "sushi"/"kugel" match was mislabeling them.
        # NOTE 2026-08-12: "fish"/"salmon"/"tuna"/"flounder"/"sole"/"lox"/
        # "tilapia"/"gefilte" moved OUT to their own new "Fish" category
        # below, per the founder's explicit request — fish and meat were
        # sharing one bucket, which buried fish products (tuna, salmon,
        # etc.) inside "Meat & Deli" where they didn't belong. Also
        # dropped the bare "fillet" keyword entirely: it was ambiguous
        # (fish fillet vs. meat fillet) and every real item that used it
        # already has a more specific word ("Salmon Fillet" has "salmon",
        # "Boneless Fillet Steak" has "steak"), so it added risk without
        # adding coverage.
    ],
    "Fish": [
        "fish", "salmon", "tuna", "flounder", "sole", "lox", "tilapia",
        "gefilte",
    ],
    "Dairy": [
        "cheese", "yogurt", "milk", "leben", "cream cheese", "butter",
        "mozzarella", "muenster", "gouda", "feta", "cottage cheese",
        "sour cream",
    ],
    "Bakery": [
        "bread", "bagel", "cake", "cupcake", "roll", "danish",
        "babka", "challah", "donut", "kichel", "biscuit", "pita",
        "farfel", "matzo", "mezonos", "pie crust", "pastry", "bun",
    ],
    "Beverages": [
        "juice", "soda", "seltzer", "water bottle", " tea", "coffee",
        " cola", "gatorade", "snapple", "sprite", "lemonade", "smart water",
        "fresca", "grape juice", "probiotic water", "ginger ale",
        # "spring water"/"poland spring" added 2026-08-12: real bottled
        # water was falling all the way through to Pantry because bare
        # "water" isn't (and shouldn't be) a keyword here — a bare
        # "water" would wrongly grab "watermelon" too. These specific
        # phrases are unambiguous.
        "spring water", "poland spring",
        # "drink" added 2026-08-30: "Prigat Drinks, ... Strawberry Mango
        # or Grape" (a real Seasons juice-drink special) had no other
        # Beverages keyword and was landing in Produce via the
        # coincidental "grape" flavor word instead.
        "drink",
    ],
    "Frozen": [
        "frozen", "ice pop", "popsicle", "gelato", "ice cream",
        "italian ice", "freeze pop", "jonny pops",
        # 2026-08-12 audit: these are packaged/frozen items that had no
        # keyword to catch them and were defaulting to Pantry.
        "fries", "potato triangle",
    ],
    "Candy & Snacks": [
        "candy", "chocolate", "gummy", "gummies", "licorice", "taffy",
        "marshmallow", "chips", "cookie", "cracker", "wafer", "popcorn",
        "bissli", "sour stick", "fruit leather", "twizzler", "pretzel",
        "snack", "nosh", "dibbitz", "ropes", "fruit riot",
        # 2026-08-12 audit: brand/product names that are always a snack
        # but don't contain any of the generic words above, so they were
        # silently defaulting to Pantry.
        "rice cake", "tortinkle", "cart wheel", "cartwheel", "sizgit",
    ],
    "Household": [
        "paper plate", "plastic cup", "beverage cup", "napkin", "tissue",
        "foil", "detergent", "dish soap", "disposable", "cutlery",
        "aluminum", "trash bag", "garbage bag", "storage bag", "plates,",
        "plate,", "plate", "plastic bowl", "forks", "spoons",
        "pans", "parchment",
        # 2026-08-12 audit: disposable cups/bags/containers that don't
        # use the word "cup"/"bag"/"container" the way the existing
        # keywords expect (e.g. "Hot Cups" not "beverage cup").
        "hot cup", "sandwich bag", "deli container", "container combo",
        "plastico container",
        # 2026-08-20 audit: candles (tea lights, memorial/yahrzeit candles)
        # had no keyword at all here and were silently falling all the way
        # through to the Pantry catch-all — found via "L'hava Tea Lights"
        # and "L'hava 3 Day Memorial Candle Glass" both landing in Pantry.
        # "tea light" is listed explicitly (not just "candle") because the
        # existing " tea" -> Beverages guard already strips "tea light(s)"
        # out of the name before the Beverages check, but nothing was ever
        # added to positively route it to Household afterward.
        "candle", "tea light",
    ],
    "Health & Beauty": [
        "toothpaste", "shampoo", "vitamin", "sunscreen", "deodorant",
        "mouthwash", "floss", "scope", "lotion", "body wash", "hair color",
        "head & shoulder", "head&shoulder",
    ],
}

# Ingredient/flavor words — only trusted once nothing in the strong tier
# matched (see note above). This is effectively the Produce department.
WEAK_CATEGORY_KEYWORDS = {
    "Produce": [
        "avocado", "eggplant", "cucumber", "tomato", "onion", "carrot",
        "mango", "strawberr", "produce", "lettuce", "pepper", "potato",
        "fruit", "vegetable", "grape", "cherries", "cherry", "nectarine",
        "orange ", "oranges", "lemon", "lime", "scallion", "shallot", "turnip",
        "cabbage", "celery", "squash", "parsley", "dill", "cauliflower",
        "broccoli", "apple", "pineapple", "cantaloupe", "watermelon",
        "berries", "berry", "plum", "peach", "banana", "kiwi",
        "honeydew", "fresh corn",
        # "pear", "garlic", "mushroom" added 2026-08-30 auditing Seasons'
        # real flyer data — "Bosc Pears", "Fresh Peeled Garlic", and
        # "Cello Mushrooms" all had no matching keyword at all and were
        # landing in Pantry instead of Produce. Also added the plural
        # "oranges" above (existing "orange " had a trailing space to
        # avoid mid-word collisions, which meant it could never match the
        # plural — "Extra Large Navel Oranges" was landing in Pantry too).
        "pear", "garlic", "mushroom",
    ],
}

# Kept for backwards compatibility with anything importing the old name.
CATEGORY_KEYWORDS = {**STRONG_CATEGORY_KEYWORDS, **WEAK_CATEGORY_KEYWORDS}

# A handful of strong keywords are also substrings of unrelated brand
# names — "turkey" the meat vs. "Turkey Hill" the iced-tea/ice-cream
# brand, "ham" the meat vs. "shampoo" the toiletry. Found during the
# 2026-08-10 audit ("Turkey Hill Decaf Orange Tea" was landing in Meat &
# Deli). This guard strips the colliding brand phrase out of the name
# before testing the keyword, so the bare keyword doesn't fire just
# because the brand name happens to contain it — every other keyword's
# behavior is untouched.
_KEYWORD_COLLISION_GUARDS = {
    "turkey": ["turkey hill"],
    "ham": ["shampoo", "hamburger", "graham"],
    # "butter" the dairy product vs. "peanut butter" / "almond butter" /
    # "cashew butter" the nut spread (not dairy at all) — found 2026-08-10
    # via "Oat Chocolate & Peanut Butter Bar" landing in Dairy.
    "butter": ["peanut butter", "almond butter", "cashew butter", "sunflower butter"],
    # "milk" the dairy product vs. "milk chocolate" the candy descriptor —
    # found 2026-08-12 via "Swiss Milk Chocolate" landing in Dairy instead
    # of Candy & Snacks.
    "milk": ["milk chocolate"],
    # Weak Produce keywords (plain fruit/flavor words) colliding with
    # packaged snack/beverage products that just happen to have a fruit
    # word in the name — found 2026-08-10 auditing a large batch of real
    # Aisle 9 items. None of these are actually fresh produce.
    "mango": ["dried mango"],
    "lemon": ["lemon sparkling water"],
    # "berry" (from weak Produce "berry"/"berries") vs. "cranberry" as a
    # flavor descriptor on packaged granola — not fresh produce. Found
    # 2026-08-20 via "Klein's Naturals Granola Cranberry Pecan" landing in
    # Produce; falls back to Pantry once stripped, which is correct for a
    # shelf-stable granola.
    "berry": ["berry & cherry no color italia", "cranberry pecan"],
    "cherry": ["berry & cherry no color italia"],
    "fruit": ["fruity pebbles", "fruit by the foot"],
    "pepper": ["tortinkles spicy pepper"],
    # " tea" the beverage vs. disposable "tea spoons" (cutlery, not a
    # drink) — found 2026-08-10 via "Deluxe Clear Tea Spoons" landing
    # in Beverages instead of Household.
    " tea": ["tea spoon", "tea spoons", "teaspoon"],
    # "onion" the fresh vegetable vs. prepared appetizers/mixes/snacks
    # that happen to be onion-flavored — not fresh produce. Expanded
    # 2026-08-12 after a full-site audit found onion soup mix and
    # onion-flavored corn snacks tagged Produce.
    "onion": ["onion tempura", "onion ring", "onion soup", "onion garlic"],
    # 2026-08-12 audit fixes below — a full pass over every category on
    # the live site turned up real miscategorizations, not edge cases:
    # "nugget" the chicken/meat product vs. corn/bread "nuggets" snacks.
    "nugget": ["corn nugget", "sourdough nugget"],
    # "shoulder" the cut of meat vs. the "Head & Shoulders" shampoo brand.
    "shoulder": ["head & shoulder", "head&shoulder", "head and shoulder"],
    # "hot dog"/"hotdog" the meat product vs. "hot dog buns" — the bread,
    # not the frankfurter.
    "hot dog": ["hot dog bun"],
    "hotdog": ["hotdog bun"],
    # "bread" the bakery product vs. "breaded" (a coating on a frozen/deli
    # appetizer, not bread itself).
    "bread": ["breaded"],
    # "cake" the bakery product vs. "pancake" (a breakfast/pantry mix, not
    # a cake).
    "cake": ["pancake"],
    # "chicken" the fresh/deli meat vs. packaged pantry items that are
    # merely chicken-flavored (soup mixes, ramen).
    "chicken": ["chicken noodle soup", "chicken flavor", "chicken bouillon"],
    # "nosh" (a snack) vs. "Nish Nosh" — a salad dressing brand name that
    # happens to contain the word.
    "nosh": ["nish nosh"],
    # Weak Produce "tomato"/"potato"/"dill" colliding with condiments,
    # frozen sides, and pickled/jarred goods — none of these are fresh
    # produce.
    "tomato": ["tomato ketchup", "tomato sauce", "tomato flavor"],
    "potato": ["crinkle cut potato", "potato triangles"],
    "dill": ["kosher dill", "dill gherkin"],
    # 2026-08-12 audit fixes below (second pass, prompted by the founder
    # flagging categories were "still bad" after the first pass):
    # "cake" the bakery product vs. "rice cake(s)" (a snack, not baked
    # goods) and "birthday cake" used as a plain flavor/scent descriptor
    # on candy/granola (not an actual cake).
    "cake": ["pancake", "rice cake", "birthday cake"],
    # "cheese" the dairy product vs. a shelf-stable jarred pasta sauce
    # that merely has "cheese" in its name (Tuscanini's other jarred
    # sauces — Alfredo, Vodka — correctly land in Pantry; this one
    # shouldn't be treated differently just because of the word order).
    "cheese": ["mac & cheese sauce", "mac and cheese sauce"],
    # "roll" the bread product vs. sushi roll names from the Gourmet
    # Glatt sushi counter (not bakery items at all).
    # 2026-08-20 audit: the guard only covered Gourmet Glatt's specific
    # roll names — Seasons' "California Sushi Roll" and "Onion Tempura
    # Sushi Roll" were still landing in Bakery via the same "roll" match,
    # so a generic "sushi roll" phrase was added to catch any store's
    # sushi counter. Also found Kosher Village's "Mini Rolls Winkie
    # Candy" landing in Bakery instead of Candy & Snacks — "roll(s)"
    # (Bakery) is checked before "candy" (Candy & Snacks) in keyword-tier
    # order, so the literal word "Candy" in the name was losing to "Rolls".
    "roll": [
        "dragon roll", "tropical roll", "vegetable platter", "sushi roll",
        "rolls winkie",
    ],
    # "pita" the bread (pita bread) vs. "pita chips" — a cracker/snack,
    # not a bakery item. Found 2026-08-20 via "Stacy's Pita Chips, Simply
    # Naked" landing in Bakery instead of Candy & Snacks.
    "pita": ["pita chips"],
}
# "milk" the dairy product vs. "Milk Munch" — a candy bar name, not an
# actual dairy product.
_KEYWORD_COLLISION_GUARDS["milk"].append("milk munch")
# " tea" the beverage vs. "tea light(s)" — a candle, not a drink.
_KEYWORD_COLLISION_GUARDS[" tea"].extend(["tea light", "tea lights"])
# "coffee" the beverage vs. disposable "coffee hot cups" — a party-supply
# item (see the new "hot cup" Household keyword above), not a drink.
_KEYWORD_COLLISION_GUARDS["coffee"] = ["coffee hot cup", "coffee hot cups"]

# A few product names never contain any of the department-level keywords
# above at all (the words are scattered non-contiguously through the
# name, or the product is only identifiable by brand), so no per-keyword
# guard can route them correctly. These are checked as a first pass,
# before the tiered keyword matching below, and only fire on an
# unambiguous brand/product signal.
BRAND_OVERRIDES = {
    # Bodek is exclusively a frozen produce brand (frozen vegetable/fruit
    # cubes and purees) — both of its items in the 2026-08-12 audit had
    # fallen into Pantry/Produce because "frozen" itself never appears
    # in the product name.
    "bodek": "Frozen",
    # Broadway('s) J2 is a frozen kosher pizza brand; "pizza" itself is
    # intentionally NOT a generic Frozen keyword (it would wrongly catch
    # pizza sauce, pizza cheese, and pizza-flavored squares, which are
    # correctly Pantry/Dairy), so this brand is matched specifically.
    "broadway j2 pizza": "Frozen",
    "broadway's j2": "Frozen",
    # Fruit Riot is a candy brand whose flavor names mimic soda flavors
    # ("Vanilla Cola", "Cherry Cola") — the word "cola" was outranking
    # the existing "fruit riot" Candy & Snacks keyword because Beverages
    # is checked earlier in the tier order.
    "fruit riot": "Candy & Snacks",
    # Jolly Rancher is exclusively a candy brand, but its flavor names
    # ("Fruit Mango") are plain weak-tier Produce words with no other
    # Candy & Snacks keyword present in the name — found 2026-08-20 via
    # "Jolly Rancher Fruit Mango, 10 Oz" landing in Produce. (Other Jolly
    # Rancher items already land correctly when they also contain a strong
    # keyword like "ropes".)
    "jolly rancher": "Candy & Snacks",
}


def _keyword_matches(name_lower: str, kw: str) -> bool:
    guarded_phrases = _KEYWORD_COLLISION_GUARDS.get(kw)
    if guarded_phrases:
        for phrase in guarded_phrases:
            name_lower = name_lower.replace(phrase, "")
    return kw in name_lower


def guess_category(item_name: str) -> str:
    """Best-effort keyword match against the item's name (see the note
    above the keyword lists for why this is name-based rather than pulled
    from the store's real department tag, and why it's two tiers). Falls
    back to 'Pantry' (the catch-all for shelf-stable grocery/pantry
    staples) when nothing matches."""
    name_lower = item_name.lower()
    for brand, category in BRAND_OVERRIDES.items():
        if brand in name_lower:
            return category
    for category, keywords in STRONG_CATEGORY_KEYWORDS.items():
        if any(_keyword_matches(name_lower, kw) for kw in keywords):
            return category
    for category, keywords in WEAK_CATEGORY_KEYWORDS.items():
        if any(_keyword_matches(name_lower, kw) for kw in keywords):
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
