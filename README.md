# Kart Compare

*Compare grocery deals across Lakewood — all in one cart.*

## For Dummies: what to actually do with these files

**Important change from before:** double-clicking `docs/index.html` will now show a "couldn't load deal data" message instead of the site. That's expected, not broken — explained in the P1 fix below. The real way to view and test this now is:

1. Once it's hosted (see "Website vs. app — what it would actually cost" below), just visit the real web address. That's the normal way anyone will use it.
2. To preview it yourself before hosting it: open a terminal in the `docs/` folder and run `python3 -m http.server 8000`, then open `http://localhost:8000` in a browser. This runs a tiny local web server on your own computer for a minute so the page can load its data — completely normal for testing websites, not something you need to leave running.
3. Search, filter by store or category, click into any store's own page.
4. Click "+ Add" on a deal to save it, then the orange **Shopping List** button (bottom-right) to see your list and hit **"Find cheapest store for this list"**.

Everything else (`backend/`, `build_site.py`, `.json` files) is the engine room that produced `docs/`. You won't need to touch it — the data now refreshes itself automatically (see "Automatic updates are now on" below).

**Note on the folder name:** the built website lives in a folder called `docs` (not `site`). That's not a typo — GitHub's free hosting (Pages) only knows how to serve a website from the repo's root folder or a folder specifically named `docs`, so naming it that now means turning on hosting later is a two-click process instead of a restructure.

## What's new in this pass (launch-readiness audit fixes)

Straight from the audit report — everything marked P0 and P1 there is done:

- **Mobile now actually works.** There was no mobile viewport tag at all before, so phones rendered a shrunk-down desktop layout. Fixed, plus real responsive layout rules for phone-sized screens.
- **The header no longer overlaps content while scrolling.** Only the search/filter bar stays pinned now, not the header too — removes the whole class of "two sticky things fighting" bugs on narrow screens.
- **Favicon, browser-tab icon, and real link previews.** Sharing a Kart Compare link in WhatsApp/iMessage/Facebook now shows a real title, description, and image card instead of a bare blank link. (The icon and preview image right now are a simple placeholder "KC" monogram, generated automatically — swap them for the real logo whenever that's ready; see `gen_assets.py`.)
- **The "how fresh is this" date is front and center on every page**, not just the homepage, since specials have been proven to change within days.
- **Every page is dramatically smaller.** Store pages used to embed the entire 437-item dataset (about 114KB) even when only showing 10 items. Now every page shares one `deals.json` file, loaded once. Store pages went from ~140–175KB down to ~31KB each. **The trade-off**: this is why double-clicking no longer works directly — see point 1 above.
- **10 categories instead of 5**, much closer to the real store departments (Produce, Meat & Deli, Dairy, Bakery, Beverages, Frozen, Candy & Snacks, Household, Health & Beauty, Pantry) — still a name-based best guess, not pulled from the store's own department tag (that would need a bigger scraping change), but a real step up in usefulness.
- **"Report a wrong price" link** in the footer of every page (emails you directly).
- **New About page** (`about.html`) explaining what this is, how the data is gathered, and — importantly — a clear "this is independent and unofficial, not affiliated with the stores listed" disclaimer. Worth reading the Legal section of the audit report for why that line matters.
- **Installable like an app** — see "Website vs. app" below.
- **Analytics wired in, just needs your account** — see below.

## What's new in the previous pass

- **Second, much bigger scrape-coverage fix**: after the first fix, you said it still looked incomplete — and digging in with a real live browser proved you right again, for a different reason than before. Seasons is a multi-location chain, and it turns out this platform decides which store's inventory to show you based on a cookie set during a ZIP-code confirmation step, not just the web address — visiting the "Lakewood" page directly could silently serve a different location's (e.g. Queens) deals with no error or warning. I fixed the scraper to explicitly confirm the Lakewood ZIP (08701) before reading anything, the same way a real shopper would. I also found the specials lists are much deeper than previously captured once properly located. New counts: Seasons 139 (up from 56), Nutmeg 94 (up from 49), Kosher West 120 (up from 64). Kosher Village re-confirmed at 10 (no pagination, genuinely that small). **Total went from 253 to 437 real deals.**
- **Smarter search, no AI backend required**: the search bar now forgives typos (e.g. "choclate" still finds "Chocolate") and understands basic plurals and a handful of common grocery nicknames (e.g. "chix" finds "Chicken"). This runs entirely inside the page itself — no internet connection or server needed beyond opening the file. A search bar that understands full intent, not just fuzzy spelling, would need a real AI service and real hosting — see "Is this scraper live?" below for what that would take.
- **Visual redesign**: new color scheme (indigo/orange instead of the teal/amber you didn't like), a proper hero section on the homepage with live stats, a sticky header with the search bar built in, category filters as clickable pills instead of a dropdown, savings-percentage badges on discounted items, and general spacing/typography polish so it reads as a real product instead of a plain list.
- **Shopping List price-optimizer**: the "put in your list, find out where it's cheapest" feature. Add items from any store, then click "Find cheapest store for this list" — it looks across all 437 scraped deals for similar items at other stores (matching by shared words in the product name, since stores don't use identical names for the same product) and ranks stores by how many of your items they cover and the total cost.
- **Database now has room for wine stores**: added `store_type` (grocery/wine), `latitude`, `longitude`, and `address` columns to the stores table, unused today but in place for when wine stores get added.

### A hard truth found while fixing this: specials change, even within the same day

While re-checking Kosher Village, the same specials page returned a completely different set of 10 items than it had four days earlier. Nothing was scraped wrong either time — the store's own site had just moved on. That means any snapshot, however complete when it's taken, starts going stale the moment the store updates their page. The real fix for that isn't scraping harder once, it's re-scraping regularly. See the automation note below.

### What "all products, not just specials" would take

You asked for every product each store sells, not just this week's deals, so a shopping list could be priced out at every store like a maps app comparing routes. Checking each store's real site directly: Seasons, Nutmeg, Kosher West, and Kosher Village all have real online catalogs with dozens of categories (Dairy, Meat, Produce, etc.) — full-catalog scraping is realistic there, but it's a much bigger job, likely thousands of items per store instead of hundreds. Gourmet Glatt's entire website is just this week's PDF flyer — there is no online catalog to scrape. Bingo's website is a membership sign-up page — no online store at all. Those two could only ever contribute "what's on sale this week," never a full catalog. Let me know if you want me to start on the full catalog for the four stores that have one.

### Automatic updates are now on

Two scheduled tasks are set up and running: every **Sunday at 12:00 PM** and every **Wednesday at 12:00 PM**, it re-checks all six stores live (using the same ZIP-confirmation, click-through-every-page approach that found the real numbers this time), rebuilds the site, and redeploys it — with an explicit instruction to triple-check page counts against the previous run and flag anything that looks wrong rather than silently under-reporting. You'll get a notification each time it finishes. You can view, pause, or edit these from the "Scheduled" section of the app sidebar (task names: `kart-compare-rescrape` for Sunday, `kart-compare-rescrape-wed` for Wednesday).

## Website vs. app — what it would actually cost

You asked how much harder/more expensive a real app would be versus a website. Here's the honest comparison:

**Website (what this is), hosted for real:**
A domain name runs roughly $10–15/year. Hosting on GitHub Pages, like you were already planning, is free. That's the entire ongoing cost — a few dollars a year, nothing else.

**A real native app (App Store + Google Play):**
Apple charges $99/year just to be allowed to publish on the App Store — mandatory, recurring, whether anyone downloads it or not. Google Play is a one-time $25 fee. That's before any actual development — building a real app (even a simple one) is a meaningfully bigger technical project than a website: app store review, provisioning/signing certificates, ongoing OS update maintenance, and either learning native iOS/Android development or a cross-platform framework. Realistically, that's real money if you hire someone, or a genuinely difficult multi-month undertaking to do yourself even with AI help.

**The middle ground — already built into this pass:** the site is now a **PWA (Progressive Web App)** — `manifest.json` and a small offline-caching service worker were added. On a phone, a visitor can tap "Add to Home Screen" (Safari/Chrome both support this) and get a real icon on their home screen that opens full-screen, no browser address bar, feels like an app. It won't show up in App Store search, and it can't send push notifications the way a native app can — but it gets you most of what "having an app" actually means to a user, at the website's cost, not the app's.

**My recommendation as your consultant:** stay with the website + installable-PWA approach. Revisit a real native app only if usage genuinely grows and you specifically need App Store discovery or push notifications — right now that would be $99/year plus real development cost for benefits you don't need yet.

## Analytics — one signup away from working

A GoatCounter script tag is already wired into every page (`build_site.py`'s `ANALYTICS_SNIPPET`) — it's free forever for a site this size, doesn't track individuals, and needs no cookie-consent banner. Right now it's inert (points at a placeholder site code). To turn it on:

1. Go to https://www.goatcounter.com and click "Sign up" (free, no credit card).
2. Pick a site code (e.g. `kartcompare`) — that becomes your dashboard URL.
3. Open `build_site.py`, find the line `GOATCOUNTER_CODE = "YOURCODE"` near the top, and replace `YOURCODE` with your real site code.
4. Re-run `python3 build_site.py` and redeploy.

That's it — no other setup, and you'll be able to see visit counts, which stores get clicked, and what people search for.

## Is this scraper "live"?

As of this pass, closer to yes. Every number on the site was verified against each store's real, live website using an actual browser (not guessed or estimated), and it now re-checks itself automatically twice a week (see "Automatic updates are now on" above) rather than needing you or me to re-run it by hand. The one honest caveat: my own dev sandbox still doesn't have a browser installed, so *between* those scheduled runs, if you manually re-run the scrapers yourself from a terminal, they'll fall back to the most recent saved snapshot rather than fetching live — that's fine, since the scheduled task is what's actually keeping the real data current now.

## Your vision — where this is headed, and the honest state of each piece

You described three things: wine stores, wine-store-to-grocery-store proximity, and a shopping list that finds the cheapest place to buy it. Here's where each stands:

1. **Shopping list → cheapest store**: built today, working, described above. It's a first pass (word-matching, not true product-matching — a hard problem even big grocery-comparison companies invest heavily in), but it's real and uses your real data.
2. **Wine stores**: not started. Needs the same process as the six grocery stores — find each wine store's real website, figure out if it's HTML or PDF, build a scraper. I'd tackle this the same careful way (check the real site before writing code) once you give me a list of which wine stores to include.
3. **"Which wine store is near which grocery store"**: needs two things neither store's data currently has — actual addresses and map coordinates (latitude/longitude) for every store, and a way to calculate distance between them. The database is ready for this (see the new `store_type`/`latitude`/`longitude`/`address` columns), but populating it means geocoding each store's address (turning an address into map coordinates), which is its own small feature.
4. **AI-powered "understands what I mean" search**: realistic, but it needs a small backend making a real AI call — it can't safely live inside a plain HTML file (that would mean putting a private API key in code anyone can view). This fits naturally once the Flask/FastAPI backend exists.

## GitHub — plan for when you're ready

You asked to hold off on actually doing this until the site/branding is settled, so nothing's been pushed anywhere yet. When you're ready, here's the plain-English plan: I'll organize everything into a clean folder structure with a `.gitignore` (a file that tells git which files to ignore, like temporary junk) and a proper top-level README, then walk you through **GitHub Desktop** — a point-and-click app, no command line needed — to create the repository and upload it. Just say the word.

## The stores, honestly (updated 2026-08-10)

| Store | What their site actually is | Deals found |
|---|---|---|
| Gourmet Glatt | Now has a real "Specials" page (redesigned since launch) linking to a PDF flyer, 2 pages this week | 113 |
| Seasons | Full online store, specials spread across many pages, multi-location (needs explicit ZIP confirmation to get the right store) | 109 |
| Nutmeg | Full online store, specials spread across many pages | 80 |
| Kosher West | Full online store, specials spread across many pages | 121 |
| Kosher Village | Full online store, specials page has no pagination — genuinely just 10 right now | 10 |
| Aldi | Real weekly ad via the Flipp flyer platform, filtered to genuine "Price Drops" only (Produce/Beverages/Pantry) | 6 |
| Bingo | Now has an "Offers > Weekly Deals" nav item, but it's still empty — no flyer posted yet | 0 |
| ShopRite (Jackson, NJ) | Not built yet — scraper doesn't exist in the repo | pending |
| Aisle 9 (Lakewood) | Own online-ordering site; every category page (including Specials) is gated behind account login — no guest/zip browsing like the other stores — so this covers real, verified markdowns from their homepage carousel plus the Meat/Dairy/Grocery/Household & Beyond/Produce/Sushi departments of their Specials page, not yet every department | 92 |

**531 real deals total.**

Seasons and Nutmeg both dropped from the prior snapshot (Seasons 139→109, Nutmeg 94→80) — re-verified live against 2-3 random pages each before trusting the lower numbers; the drop is real, not a scraping miss. Gourmet Glatt jumped 74→113 because the store's own website was redesigned with a bigger 2-page flyer this week.

## About "when is the sale valid from/to"

- **Gourmet Glatt**: the flyer itself prints exact dates. Confirmed, shown with a green banner.
- **Seasons**: their site does show exact dates, but only baked into a flyer image, not real text — reading it needs image OCR, a separate feature. Amber "estimated" banner (7-day window) shown instead of a guessed exact date.
- **Nutmeg, Kosher West, Kosher Village**: none publish an exact end date anywhere on their site. Same amber estimated banner.
- **Bingo**: no flyer currently posted, so no dates to show.
- **Aisle 9**: no end date published anywhere on their site either. Same amber estimated banner.

I'd rather show an honest "estimated" label than quietly guess.

## Technical details (optional reading)

- Database: SQLite, `backend/db/schema.sql` — tables for stores, categories (now 10), deals, users, shopping list.
- `backend/scrapers/base_scraper.py` — shared price-parsing and category-guessing logic.
- `backend/scrapers/grocery_platform_scraper.py` — the one shared scraper behind Seasons/Nutmeg/Kosher West (same underlying website software, discovered while researching them), including the ZIP-confirmation location fix.
- `build_site.py` — turns the database export into the actual webpages, including branding, the shopping-list optimizer, the About page, and the PWA/manifest files.
- `gen_assets.py` — generates the placeholder favicon, app icons, and social-share image (run this after `build_site.py`, or whenever you swap in the real logo).
- `backend/db/deals_all_stores.db` — the full combined database, 437 deals.
- `docs/deals.json` — the one shared data file every page fetches (instead of each page embedding its own copy).
- `docs/manifest.json`, `docs/sw.js` — what makes the site installable as a PWA.
- `docs/about.html` — the About/disclaimer page.

### Re-running everything

```bash
cd backend
pip install -r requirements.txt
python3 -m scrapers.gourmet_glatt_scraper
python3 -m scrapers.seasons_scraper
python3 -m scrapers.nutmeg_scraper
python3 -m scrapers.kosher_west_scraper
python3 -m scrapers.kosher_village_scraper
python3 -m scrapers.bingo_scraper
cd ..
python3 export_deals.py
python3 build_site.py
python3 gen_assets.py
```

Then, to preview locally: `cd site && python3 -m http.server 8000` and open `http://localhost:8000` (see "For Dummies" above for why double-clicking the HTML file directly no longer works).
