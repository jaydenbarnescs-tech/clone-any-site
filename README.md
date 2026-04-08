# clone-any-site

A practical playbook for recreating any live website as a self-contained, single-file HTML deliverable — using AI-assisted design-token extraction as the primary path and a robust manual fallback when automation breaks down.

This repo does not contain a clone of any specific site. It documents the **process** — the decisions, the tools, the fallback ladder, and the reusable helpers — so you can apply it to any target.

---

## Philosophy

> Extracting colors, fonts, spacing values, and layout structure from a public website is what every frontend developer does with DevTools. These are functional design tokens, not creative works. A hex code is a fact. A font family name is a fact. A grid system is a fact.

This playbook is about **design system recreation**, not content theft. Do not use it to reproduce proprietary logos, trademarked names, or copyrighted copy as your own. Use it to learn how a visual system is put together, to build faithful references, to prototype, to teach, and to rebuild your own sites in the style of ones you admire.

---

## The three-step ladder

When asked to clone a site, work through these in order. Stop at whichever one succeeds.

### Step 1 — Automated extraction (preferred)

Use an AI design extractor to pull a structured DESIGN.md containing colors, typography, spacing, elevation, components, and layout. The pipeline this playbook was built around is [Aura.build](https://aura.build)'s extraction API, but any equivalent tool works:

- Browser-based color pickers + DevTools inspection
- Open-source scrapers like [project-wallace/css-analyzer](https://github.com/projectwallace/css-analyzer)
- Headless-browser computed-style dumps

**Typical runtime:** 30–90 seconds per site.

**When it works:** simple marketing sites, most SaaS landing pages, Framer/Webflow sites with accessible CSS.

**When it fails:** WebGL-heavy game clients, sites behind aggressive anti-bot, SPA shells where the extractor can't reach the DOM before timeout.

### Step 2 — Manual extraction (fallback)

When automation times out or refuses, fall back to direct page inspection. This is what experienced frontend devs have always done:

1. **Fetch the rendered HTML** — via `curl`, a headless browser, or an LLM tool like `web_fetch`. Get the full DOM including image URLs, link hrefs, heading text, and section structure.
2. **Observe the visual language** — open the site in a real browser, pick colors with an eyedropper, identify fonts with a font-finder extension, measure spacing with DevTools.
3. **Derive design tokens manually** — write them down as CSS custom properties or a Tailwind config. A typical set is 6–10 colors, 2–3 font families, a spacing scale, and a handful of shadow/border values.
4. **Map the sections** — nav, hero, feature grid, CTA bands, footer. Most pages follow the same skeleton; identify which blocks the target uses.

This fallback is **more reliable than automation** for complex sites. It takes longer but you end up with a deeper understanding of the design.

### Step 3 — Build the recreation

Once you have tokens and structure, build a single HTML file:

- Tailwind via CDN for speed (no build step)
- Google Fonts via `<link>` for typography
- Custom CSS properties in `:root` for the extracted palette
- Sections built top-to-bottom matching the source layout
- Arbitrary values (`rounded-[22px]`, not `rounded-2xl`) when the DESIGN.md or your measurements give a specific number

Keep everything in one `.html` file. Single-file deliverables are portable, trivially shareable, and work offline.

---

## The self-contained image pattern

Referencing images from the source site's CDN is the first thing that breaks. Most CDNs block hotlinks via the `Referer` header, meaning images that load fine on the live site return 403 from your local file. The fix is a predictable ladder:

### Option A — Image proxy (quick, not portable)

Route image URLs through a referer-stripping proxy like [`wsrv.nl`](https://wsrv.nl):

```
https://wsrv.nl/?url=example.com/images/hero.png
```

Pros: one-line sed substitution, no downloads.
Cons: requires internet, fails if the proxy goes down, and some image hosts block proxies too.

### Option B — Base64 embedding (bulletproof)

Download the images once, compress them, and inline them as `data:` URIs. The HTML becomes a single file with zero external dependencies — it works offline, it works when you email it, it works forever.

The `scripts/embed_images.py` helper in this repo does all four steps:

1. Scans your HTML for image URLs
2. Downloads them with a realistic User-Agent + Referer
3. Resizes and recompresses to reasonable web dimensions (max 1400px wide, JPEG quality 78)
4. Replaces every URL in the HTML with a `data:image/jpeg;base64,...` URI

Typical output for a 12-image marketing page: **~1.5 MB** self-contained HTML. Large enough to notice, small enough to email or drop into a chat.

See `scripts/embed_images.py` and `examples/template.html` for reference implementations.

---

## Case study — the run that built this repo

This playbook was extracted from a single session cloning a real website. Here's what actually happened, so you know the fallback ladder isn't theoretical:

1. **Extractor called** with `mode=exactly` on the target URL.
2. **First extraction timed out** at the extractor's 120-second server limit — the target was a WebGL game launcher page, too heavy to parse.
3. **Retry — also timed out.** Two strikes on automation.
4. **Fallback engaged.** Fetched the rendered HTML directly, which returned the full DOM: 12 unique image URLs, three section headings, four call-to-action blocks, and a four-column footer.
5. **Design tokens derived manually** from visual observation: a dark medieval palette (ink black, aged gold, parchment cream, ember red), serif display typography, italic body accents, ornate PNG dividers used as backgrounds.
6. **Single-file HTML built** with Tailwind CDN + Google Fonts, top-to-bottom matching the source sections.
7. **Images loaded via CDN initially → blocked by hotlink protection.**
8. **Proxy substitution (Option A)** — still didn't render in the preview context.
9. **Base64 embedding (Option B)** — downloaded all 12 images via curl with a browser User-Agent, resized them to max 1400px wide with Pillow, encoded to base64, injected into the HTML. Final file: 1.41 MB, 13 data URIs, zero external references. Rendered perfectly.

Total time from "can you clone X" to self-contained deliverable: **roughly 15 minutes**, most of which was waiting for the two failed extractor runs.

---

## Repo contents

```
clone-any-site/
├── README.md               ← you are here
├── LICENSE                 ← MIT
├── scripts/
│   └── embed_images.py     ← the image-download + compress + base64 helper
└── examples/
    └── template.html       ← a blank starting-point HTML shell with
                              design tokens, sections, and fonts wired up
```

---

## Quick start

```bash
# 1. Copy the template
cp examples/template.html my-clone.html

# 2. Edit the design tokens in the :root block at the top
#    (colors, fonts, spacing scale)

# 3. Fill in the sections with image URLs from the source site

# 4. Embed all images as base64 so the file is self-contained
python3 scripts/embed_images.py my-clone.html

# 5. Open in browser
open my-clone.html
```

---

## When not to use this

- **You need a production app, not a static recreation.** This playbook produces faithful visual prototypes, not working backends.
- **The target is yours and you already have the source.** Just fork it.
- **You're trying to pass off someone else's brand as your own.** Don't.

---

## License

MIT — do what you want, no warranty. See `LICENSE`.

---

## Contributing

PRs welcome, especially:

- New fallback patterns for when both automation and manual extraction hit walls
- Alternative image-embedding strategies (SVG sprite sheets, WebP optimization, etc.)
- Examples directory additions (only templates or methodology notes — not clones of specific sites)
- Extractor comparisons and benchmarks
