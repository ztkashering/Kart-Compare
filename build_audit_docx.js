const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, AlignmentType, LevelFormat, convertInchesToTwip,
} = require("docx");

const BRAND = "4F46E5";
const DARK = "111827";
const MUTED = "6B7280";
const P0_RED = "B91C1C";
const P0_BG = "FEE2E2";
const P1_AMBER = "92600A";
const P1_BG = "FEF3C7";
const P2_GREEN = "036B4A";
const P2_BG = "ECFDF5";
const BORDER_GREY = "D1D5DB";

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    children: [new TextRun({ text, bold: true, color: BRAND, size: 28 })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 120 },
    children: [new TextRun({ text, bold: true, color: DARK, size: 24 })],
  });
}
function body(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 160, line: 300 },
    children: [new TextRun({ text, size: 21, color: DARK, ...opts })],
  });
}
function bullet(text, opts = {}) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 100, line: 290 },
    children: [new TextRun({ text, size: 21, color: DARK, ...opts })],
  });
}
function bulletBold(lead, rest) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 100, line: 290 },
    children: [
      new TextRun({ text: lead, bold: true, size: 21, color: DARK }),
      new TextRun({ text: rest, size: 21, color: DARK }),
    ],
  });
}
function tag(text, fg, bg) {
  return new TextRun({ text: " " + text + " ", bold: true, size: 18, color: fg, shading: { type: ShadingType.CLEAR, fill: bg } });
}

function cell(children, opts = {}) {
  return new TableCell({
    width: { size: opts.width || 2000, type: WidthType.DXA },
    shading: opts.fill ? { type: ShadingType.CLEAR, fill: opts.fill } : undefined,
    margins: { top: 100, bottom: 100, left: 120, right: 120 },
    verticalAlign: "center",
    children,
  });
}
function headerCell(text, width) {
  return cell([new Paragraph({ children: [new TextRun({ text, bold: true, size: 19, color: "FFFFFF" })] })], { width, fill: BRAND });
}
function textCell(text, width, opts = {}) {
  return cell([new Paragraph({ children: [new TextRun({ text, size: 19, color: DARK, bold: opts.bold || false })] })], { width, fill: opts.fill });
}

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: convertInchesToTwip(0.35), hanging: convertInchesToTwip(0.18) } } } },
        ],
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 },
        },
      },
      children: [
        // ---------- Title ----------
        new Paragraph({
          spacing: { after: 40 },
          children: [new TextRun({ text: "Kart Compare", bold: true, size: 48, color: BRAND })],
        }),
        new Paragraph({
          spacing: { after: 60 },
          children: [new TextRun({ text: "Website Audit & Launch-Readiness Review", size: 28, color: DARK })],
        }),
        new Paragraph({
          spacing: { after: 360 },
          children: [new TextRun({ text: "Prepared for FREEZY  ·  August 6, 2026  ·  Phase 1 review, pre-logo / pre-launch", size: 19, color: MUTED, italics: true })],
        }),

        // ---------- Executive summary ----------
        h1("Executive Summary"),
        body(
          "You have a real product, not a mockup: 437 verified deals scraped live from six actual Lakewood stores, an honest date-confidence system, and a working shopping-list price comparison. That's the hard part, and it's done. What's not yet done is the set of things that separate a working prototype from something you'd feel comfortable posting publicly and pointing strangers to on their phones."
        ),
        body(
          "The short version: the site will look broken on a phone right now (no mobile viewport tag), it will look unfinished when someone shares the link (no logo, no favicon, no link preview), and it will quietly go stale the day after you post it unless the update process is automated. None of these are hard fixes — they're the kind of thing a consultant flags before launch, not after. Below is the full audit, organized by what breaks the experience first."
        ),
        new Paragraph({
          spacing: { before: 100, after: 200 },
          children: [
            tag("P0 = fix before you post this publicly", P0_RED, P0_BG),
          ],
        }),
        new Paragraph({
          spacing: { after: 200 },
          children: [
            tag("P1 = fix in the first update after launch", P1_AMBER, P1_BG),
          ],
        }),
        new Paragraph({
          spacing: { after: 260 },
          children: [
            tag("P2 = strategic, plan for it but not urgent", P2_GREEN, P2_BG),
          ],
        }),

        // ---------- What's working ----------
        h1("What's Already Working"),
        body("Worth saying plainly, because it's the part most people underestimate:"),
        bulletBold("Real data, not filler. ", "437 deals, verified against the live stores this week, with an honest label on every store page for whether the sale dates are confirmed or estimated. Most local “deals” sites fake this."),
        bulletBold("The shopping-list comparison is a genuine differentiator. ", "“Which store is cheapest for my whole list” is the actual product idea you described — maps-style price routing — and a first version of it already works."),
        bulletBold("The design read as a real product, not a spreadsheet. ", "Hero stats, category pills, savings badges, and a sticky search bar all land well on desktop."),
        bulletBold("You're already being honest about limitations. ", "The footer discloses that prices can change, and store pages explain when a date is confirmed vs. estimated. That honesty will matter more than most features once real customers are relying on it."),

        // ---------- P0 ----------
        h1("Before You Post This Publicly (P0)"),
        h2("1. It will look broken on a phone"),
        body("There is no mobile viewport tag anywhere in the site (verified in the code — zero instances, zero responsive breakpoints). Without it, phones render the page as a shrunk-down desktop layout: tiny text, forced pinch-to-zoom. Given this will most likely spread through WhatsApp and community groups, the majority of first opens will be on a phone. This is a one-line fix, but it's the single highest-impact thing on this list — nothing else matters if the first impression is an unreadable page."),
        h2("2. The sticky search bar can cover content on small screens"),
        body("The search toolbar is pinned a fixed distance below the header, based on the header staying one line tall. On a narrow phone screen the header will wrap to two lines, and the toolbar's fixed position doesn't know that happened — it can end up overlapping the row underneath it. This only shows up once the viewport fix above is in place, which is exactly why it needs to be tested together, not assumed fixed."),
        h2("3. Nothing renders when the link is shared"),
        body("There's no favicon, no page description, and no link-preview tags (what WhatsApp, iMessage, and Facebook read to build that preview card when a link is pasted). Right now, sharing the link in a family or community group produces a bare blue link with no image, no title card, and no blank browser-tab icon. For a site whose growth is realistically going to be word-of-mouth sharing, this materially hurts whether people click through."),
        h2("4. The data will look current even after it's gone stale"),
        body("This matters more than it sounds: while re-verifying stores this week, the same store's specials page returned a completely different set of items than it had shown four days earlier — same store, same page, no scraping error, the sale had just moved on. A static file posted today will look exactly as fresh in three weeks as it does now, with nothing on the page warning a visitor that the prices might be old. Before this goes live publicly, it needs either an automatic recurring re-scrape (realistic — already discussed) or, at minimum, a loud, honest “data as of [date]” marker on every single page, not just the homepage."),

        // ---------- P1 ----------
        h1("Fix Soon After Launch (P1)"),
        bulletBold("Every page loads the entire dataset, even when it doesn't need to. ", "Every store page — including ones with 10 items — embeds the full 437-item, ~114KB dataset for the shopping-list feature. That's the majority of the page's weight on a mobile connection for data the page isn't even displaying. Worth trimming to just what each page needs, plus loading the comparison data only when the shopping-list panel is actually opened."),
        bulletBold("The category system is now underselling your own data. ", "The site buckets everything into 5 categories (Produce, Meat, Dairy, Bakery, Pantry), but the real stores expose 10–12 categories each (Beverages, Household, Health & Beauty, Frozen, Candy & Sweets, and so on) — that detail is being thrown away during scraping. Worth using it; a shopper looking for “Household” or “Frozen” currently has no way to filter for that."),
        bulletBold("No way for a visitor to flag a wrong price. ", "Since this mirrors other people's live pricing, some mismatches are inevitable. Right now there's no feedback path — a wrong price just sits there looking official. Even a simple “report this” link or an email address builds real trust and gives you an early-warning system."),
        bulletBold("No “About / How this works” page. ", "For a site that is not the stores' own official pricing, a short page explaining what this is, how often it updates, and that it's unofficial does real trust-building work — and heads off confusion or complaints before they happen."),
        bulletBold("The shopping list only lives in one browser, on one device. ", "It's saved with localStorage, so a list built on a phone in the store doesn't show up on a laptop at home. This was in your original spec as “basic accounts” — still a reasonable phase-2 item, not urgent, but worth knowing it's the reason the list doesn't follow the shopper around."),

        // ---------- Legal / trust ----------
        h1("Legal & Trust — Read Before You Post Publicly"),
        body("I'm not a lawyer, and this isn't legal advice — but as a consultant, three things are worth having a real answer to before this has a public URL and a real audience:"),
        bulletBold("Scraping and republishing another business's pricing. ", "Most retail websites' terms of service technically prohibit automated scraping, even of public pages. In practice, price-comparison sites (Flipp, Basket, RetailMeNot, and similar) operate this way constantly and the realistic downside if a store objects is a cease-and-desist letter or their site blocking your scraper — not criminal exposure — but it is a real possibility worth being mentally prepared for, especially once a store notices its name and prices on a site it didn't build."),
        bulletBold("Using the stores' names. ", "Referring to “Seasons,” “Gourmet Glatt,” etc. by name to describe where a deal is from is normal, low-risk, descriptive use — the same way any price-comparison site names retailers. The one thing worth avoiding is any wording or design that could read as the stores endorsing or partnering with Kart Compare, since that crosses from description into implied affiliation. A one-line disclaimer (“Kart Compare is an independent, unofficial price aggregator and is not affiliated with the stores listed”) is cheap insurance and standard practice for this category of site."),
        bulletBold("Privacy. ", "Low exposure today — there's no server, no accounts, no data collection beyond a browser's local storage. Still standard practice to have one short privacy paragraph once this has a real public domain, especially once analytics gets added (see below)."),

        // ---------- Business readiness ----------
        h1("Launch Readiness (P2, Strategic)"),
        bulletBold("No hosting or domain yet. ", "“Posting it” needs a real place for it to live — a domain name and static hosting (this kind of site is cheap and simple to host; no server required for the site itself)."),
        bulletBold("No analytics. ", "Once it's public, you'll want to know which stores get the most clicks, what people search for, and whether the shopping-list feature actually gets used — all invisible right now. A lightweight, privacy-respecting analytics tool is a small addition."),
        bulletBold("The update process is currently manual. ", "Today, refreshing the data means a live session re-scraping every store by hand. That's fine for development; it will not survive being a real public site people check regularly. This needs to become a scheduled, automatic job before or shortly after launch — otherwise the P0 staleness problem above comes back within days."),
        bulletBold("No stated reason for this to exist financially. ", "Not a defect — plenty of good local tools are community projects with no monetization — but worth deciding on purpose rather than by default. If this grows, the realistic paths are affiliate/referral links, optional store sponsorship, or simply treating it as a community goodwill project. Doesn't need an answer today, but it's worth having thought about before it's asked."),

        // ---------- Branding note ----------
        h1("Branding — Acknowledging What You Already Flagged"),
        body("You already know you want a logo, and that's correctly scoped as its own phase rather than something to rush. Two related, smaller items worth bundling into that same pass since they're cheap once a designer or design tool is already involved: a favicon (the small browser-tab icon) and swapping the current emoji category icons for a small set of matching custom icons. Neither blocks anything above — they're cosmetic polish, not launch blockers — but they're natural to batch with the logo work rather than doing three separate design passes."),

        // ---------- Action plan table ----------
        h1("Prioritized Action Plan"),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1100, 4200, 2560, 1500],
          rows: [
            new TableRow({
              tableHeader: true,
              children: [
                headerCell("Priority", 1100),
                headerCell("Item", 4200),
                headerCell("Why it matters", 2560),
                headerCell("Effort", 1500),
              ],
            }),
            new TableRow({ children: [textCell("P0", 1100, { fill: P0_BG, bold: true }), textCell("Add a mobile viewport tag + test responsive layout", 4200), textCell("Most visitors will open this on a phone", 2560), textCell("Very low", 1500)] }),
            new TableRow({ children: [textCell("P0", 1100, { fill: P0_BG, bold: true }), textCell("Fix sticky toolbar overlap on wrapped mobile header", 4200), textCell("Search bar can hide content once mobile is fixed", 2560), textCell("Low", 1500)] }),
            new TableRow({ children: [textCell("P0", 1100, { fill: P0_BG, bold: true }), textCell("Add favicon, meta description, and share-link preview tags", 4200), textCell("Link looks broken/blank when shared — hurts click-through", 2560), textCell("Very low", 1500)] }),
            new TableRow({ children: [textCell("P0", 1100, { fill: P0_BG, bold: true }), textCell("Automate re-scraping on a schedule (or show a loud “data as of” date everywhere)", 4200), textCell("Specials proven to change within days; static data goes stale silently", 2560), textCell("Medium", 1500)] }),
            new TableRow({ children: [textCell("P1", 1100, { fill: P1_BG, bold: true }), textCell("Stop embedding the full dataset on every page; load comparison data on demand", 4200), textCell("Cuts page weight substantially, especially on mobile data", 2560), textCell("Medium", 1500)] }),
            new TableRow({ children: [textCell("P1", 1100, { fill: P1_BG, bold: true }), textCell("Use the real 10–12 store categories instead of 5 generic buckets", 4200), textCell("Real filtering data already exists and is being discarded", 2560), textCell("Medium", 1500)] }),
            new TableRow({ children: [textCell("P1", 1100, { fill: P1_BG, bold: true }), textCell("Add a “report a wrong price” link or contact email", 4200), textCell("Builds trust; gives you an early-warning system for bad data", 2560), textCell("Low", 1500)] }),
            new TableRow({ children: [textCell("P1", 1100, { fill: P1_BG, bold: true }), textCell("Add a short “About / how this works” page with an unaffiliated-disclaimer", 4200), textCell("Trust, transparency, and legal cover in one page", 2560), textCell("Low", 1500)] }),
            new TableRow({ children: [textCell("P2", 1100, { fill: P2_BG, bold: true }), textCell("Buy domain + set up real hosting", 4200), textCell("Required to actually “post it”", 2560), textCell("Low", 1500)] }),
            new TableRow({ children: [textCell("P2", 1100, { fill: P2_BG, bold: true }), textCell("Add lightweight analytics", 4200), textCell("Currently flying blind on what people use", 2560), textCell("Low", 1500)] }),
            new TableRow({ children: [textCell("P2", 1100, { fill: P2_BG, bold: true }), textCell("Logo + favicon + custom category icon set", 4200), textCell("You've already correctly scoped this as its own phase", 2560), textCell("Design pass", 1500)] }),
            new TableRow({ children: [textCell("P2", 1100, { fill: P2_BG, bold: true }), textCell("Decide monetization stance (or explicitly “none”)", 4200), textCell("Better decided on purpose than by default", 2560), textCell("Decision only", 1500)] }),
          ],
        }),

        // ---------- Bottom line ----------
        new Paragraph({ spacing: { before: 320 }, children: [] }),
        h1("Bottom Line"),
        body(
          "This isn't a “start over” situation — the hard, valuable part (real scraped data, an honest freshness system, a working price comparison) is already built and works. What's between here and “I'd feel good sending this to my whole community” is a short, concrete punch list, not a redesign: fix mobile, fix sharing, fix staleness, then layer the logo and polish on top. I'd treat the four P0 items as a single next work session — they're all small individually, and together they're the difference between “works for me testing it” and “works for a stranger who taps a link on their phone.”"
        ),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  require("fs").writeFileSync("/tmp/audit/Kart_Compare_Website_Audit.docx", buf);
  console.log("wrote docx, bytes:", buf.length);
});
