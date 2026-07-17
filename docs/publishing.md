# Publishing an icon pack to the Elgato Marketplace

Everything below is **verified** by actually doing it (2026-07-12): building
a pack, exporting through Elgato's Icon Pack Man, inspecting the bytes, and
submitting. The gotchas are real and cost hours the first time — they're
encoded here (and in `sdicons` itself) so the next palette is a one-liner.

> **This file is the icon-**pack** track** (`.streamDeckIconPack`). Publishing a
> **plugin** (`.streamDeckPlugin`) is a different container + review — its
> rejection log + checklist live in
> [MARKETPLACE-REVIEW.md](MARKETPLACE-REVIEW.md).
> The **Maker Console media** rules below (1920×960 content-fit, RGBA previews,
> release-notes Unicode) are shared — plugin galleries hit the same traps.

## TL;DR — the fast path (Icon Pack Man not required)

`sdicons package` now emits the **exact container Elgato expects**, so for a
pack built with this toolkit you can skip the Icon Pack Man web tool:

```sh
sdicons build src/ MyPack --id com.you.mypack
# → dist/com.you.mypack.streamDeckIconPack  (double-click to install; upload to Maker Console)
```

Then just submit that file (see "Maker Console" below). Use the Icon Pack Man
route only if you *want* the official web tool in the loop — in which case
read the quirks section, because it will mangle your names and tags.

## The container format (verified)

The shippable file is a **ZIP** named `<id>.streamDeckIconPack` whose single
top-level entry is a **wrapper folder** `<id>.sdIconPack/`:

```
com.you.mypack.streamDeckIconPack        ← zip, this is what you ship
└── com.you.mypack.sdIconPack/           ← REQUIRED wrapper (Stream Deck reads the id from this name)
    ├── manifest.json
    ├── icons.json
    ├── icon.svg                         ← pack thumbnail (manifest.Icon)
    ├── license.txt
    ├── icons/        (144×144 png/svg/…)
    └── previews/     (optional, up to 3 store previews, png/jpg)
```

- `<id>` is **reverse-domain**, lowercase alnum, e.g. `com.beennnn.stagekeys`.
- The wrapper folder is **not optional**. Our first packager put files at the
  zip root with no wrapper — that is NOT what Icon Pack Man produces and does
  not install cleanly. `sdicons package` now writes the wrapper (see
  `sdicons/package.py`).
- Set the id with `--id`, a `"Id"` key in `manifest.json`, or let it derive
  as `com.<author>.<name>`.

## manifest.json / icons.json

See [spec.md](spec.md). Key point for icons.json: each entry is
`{ "path": "<file>.png", "name": "<display name>", "tags": ["…"] }`, `path`
relative to `icons/`. Tags drive Stream Deck's icon-library search — worth
getting right.

## Store previews

Put up to **3** PNG/JPG images in a `previews/` folder inside the pack. Icon
Pack Man *does* pick these up on drag, and `sdicons package` includes them.
They're the marketing images on the Marketplace listing.

## Icon Pack Man quirks (if you use the web tool)

<https://iconpackman.elgato.com/> is client-side (no login). It works, but:

1. **It ignores `name` and `tags` from a dragged-in `icons.json`.** On import
   every icon's name becomes its **filename** (`trombone.png`) and tags come
   out **empty** — even though your icons.json is valid and matches the exact
   schema it exports. The "Mapping file loaded" line shows a **red ✗** (zero
   matches). Flattening the folder vs using an `icons/` subfolder makes no
   difference — it just doesn't apply them on import.
2. **It stamps `"License": "MIT"`** into the exported manifest.json by default,
   regardless of what you typed. Fix it after export (or with `sdicons repair`).
3. **It does read `manifest.json`** (Name/Version/Description/Author/URL/Icon
   populate correctly) and **does read `previews/`**.
4. Loose-file dragging is a native Finder→page drag — it **cannot be
   automated** by browser tools, and the native folder picker ("Open Icon
   Pack…") can't be driven either. This step is inherently manual.

### Fixing an Icon Pack Man export

Export from Icon Pack Man (set the IconPack ID + drag a thumbnail onto the
"Icon" box first), then repair the names/tags/license in place:

```sh
sdicons repair ~/Downloads/com.you.mypack.streamDeckIconPack \
  --tags MyPack/tags.json --license CC-BY-4.0 --url https://github.com/you/mypack
```

It re-injects `name` + `tags` by matching each icon's filename stem to your
`tags.json`, fixes the manifest License/URL, and re-zips preserving the
wrapper. Verified round-trip in `sdicons/repair.py`.

## Install & test locally

Double-click the `.streamDeckIconPack` → it installs into Stream Deck. In the
app: set a key's image → **Icon Library** → open your pack → confirm the icons
have real **names** and that a **tag search** (e.g. "organ", "sax", "808")
surfaces the right ones.

## Submit via Maker Console — full walkthrough (verified 2026-07-12)

The submission portal is **<https://maker.elgato.com>** (NOT `console.elgato.com`,
which errors). Requires an Elgato login. First-time makers must also **create an
organization** and **sign the Maker Agreement** — account/legal steps only the
human can do.

**Generate the required media first** (exact dimensions matter — the wizard
rejects wrong sizes):

```sh
sdicons maker-media MyPack --subtitle "one-line pitch" \
  --previews slug1,slug2,slug3,slug4,slug5
# → maker-media/  thumbnail-1920x960.png · preview-1..5.png (144×144) · gallery-*.png (1920×960)
```

Then in the console, **Products → Create product → Icons**, and walk the wizard:

1. **Details about your product**
   - **Does the product contain AI generated content?** — a required, honest
     disclosure. If an AI produced the artwork (even parametric SVG authored by
     an assistant), **check it**. Elgato allows AI content *with* disclosure;
     hiding it violates the terms.
   - **Type / Theme / Color** — multi-select dropdowns (they re-open on outside
     clicks and re-toggle stray rows — click carefully). No "Music" option:
     for instrument icons, Type = *Artistic, Creative Tools*; Theme = *Symbol,
     Technology*; Color = *Multicolor*.
   - **Style** — *Illustrated* for flat full-colour art (not 2D/Minimal/Pixel).
   - **Is your product animated?** — leave **unchecked** for static PNG packs.
   - **Set a price** — Free/Paid; **cannot be changed after submitting**.
   - **Additional links** — optional; add a "Community" link to your project /
     the sdicons toolkit if you want it on the listing.
2. **Upload media**
   - **Thumbnail**: 1× `thumbnail-1920x960.png` (2:1, ≤5 MB).
   - **Icon previews**: up to 5× `preview-N.png` (144×144, ≤2 MB).
   - **Gallery**: **≥3** images `gallery-N.png` (1920×960, ≤10 MB) or **mp4**
     (≤50 MB) — for an animated pack, upload `gallery-animated.mp4` (from
     `sdicons maker-media --animated`) here to show the icons in motion.
   - These are native file drops — must be done by the human (a tool driving
     the browser can't pick local files).
   - ⚠️ **"1920×960" means the CONTENT must fit, not just the file.** Both WLED
     packs were rejected 2026-07-14 for "cropping of information" even though the
     files were exactly 1920×960 — the gallery's bottom row overflowed the 960 px
     canvas and got sliced. `sdicons maker-media` now sizes tiles to fit; after
     any layout change, eyeball `gallery-2.png` — the bottom row must sit clear of
     the edge. File-dimension checks (`sips`) do NOT catch overflowing content.
3. **Submit for review**
   - Summary shows Name / Stream Deck ID (reverse-domain, e.g.
     `com.you.mypack`) / Version.
   - **Release notes** are **required** (≤1500 chars).
   - **Automatically publish after being approved** — on = goes live right
     after review; off = you release manually on a chosen date.
   - **Submit** is the final publish action — the human clicks it.

Review by Elgato follows; then (if auto-publish) it goes live on Marketplace.
Product & branding guidelines: <https://docs.elgato.com/guidelines/stream-deck/icons/>.
General docs: <https://docs.elgato.com/stream-deck/icons/getting-started/>.

## Updating a published product — new version (verified 2026-07-16)

Shipping an update to an ALREADY-published product is a different, smaller flow
than the first-submission wizard above. Learned shipping Stage Keys v1.2.

- **Where**: Products → *your product* → **Versions** tab → **Create version**.
  The modal is minimal: a `.streamDeckIconPack` drop zone (≤500 MB) + **Release
  notes** (required, ≤1500 chars) + **Automatically publish after being
  approved** toggle + **Submit for review**. No Details/Media steps here.
- **"Create version" is disabled only while a prior version is *Pending
  review*.** A **Published** product accepts a new version immediately; the new
  version stacks (e.g. a never-submitted 1.1 is simply superseded by 1.2).
- **Media is product-level, not version-level.** Thumbnail / icon previews /
  gallery live on the **Media** tab and can be updated **any time** — including
  while a version is Pending review. They are NOT part of the Create-version
  modal, so update them separately.
- **Release-notes editor rejects some Unicode.** The rich-text field dropped a
  paste containing em-dashes (`—`) silently (counter stayed 0). Use ASCII
  hyphens; verify the char counter moved before trusting it.

## Media gotchas — the two that bit us (verified 2026-07-16)

Both surfaced building the Stage Keys v1.2 media (`sdicons maker-media`). Fixed
in `makermedia.py`; documented here so the next pack doesn't relearn them.

- **Icon previews MUST be transparent PNG (RGBA), never opaque RGB.** The
  console's "Icon previews" slot **silently rejects an opaque upload** — the
  drop appears to take, then the slot **blanks out** ("the previews
  disappear"). It wants the transparent icon art and renders it on its own
  tile. `maker-media` used to bake a dark tile and `convert("RGB")` the
  preview (no alpha) → rejected. Now it emits the icon resized to 144×144 in
  **RGBA** (alpha preserved). The hero thumbnail and gallery banners stay
  opaque RGB — those are flat banners, not icon slots, so they're fine.
- **Static+animated packs duplicate every montage tile.** A pack shipping both
  `<x>.png` and its animated `<x>-playing.webp` active-state variant listed
  BOTH in the thumbnail/gallery montages (identical on a frozen frame) → every
  icon appeared **twice**. `_icons()` now collapses to one tile per base icon
  (strips a `-playing` suffix, dedupes same-stem static/animated), preferring
  the static file. The animated gallery is built from the separate `animated`
  source dir, so it never had the dup and is unaffected.

## Animated icons must be GIF, not PIL-optimised WebP (verified 2026-07-16 — a rejection)

Stage Keys v1.2 was **rejected**: *"we aren't able to get the animated icons
working when assigning them to keys. Please ensure that animated icons are GIF
and/or WebP."* The animated icons were **WebP** produced by PIL — *technically*
valid (webpmux showed 24 frames, 83 ms, loop 0, transparency) but encoded as
**partial-frame** (sub-rectangle + dispose/blend) optimised WebP that **Stream
Deck's key decoder does not play**. Cross-check clinched it: every OTHER
published pack of ours uses GIF for animation (WLED Effects — 216 GIFs, live &
working); none ship WebP. WebP was the one outlier, and it's the one that failed.

- **Ship animated icons as GIF** (`<slug>-playing.gif`). `save_animated` picks
  format by output extension; the build now writes `.gif`.
- **GIF transparency must be applied per-frame.** A raw RGBA GIF save keeps
  alpha only on frame 0 — the palette key colour then flashes opaque mid-loop.
  `save_animated`'s GIF branch routes every frame through `render._rgba_to_p`
  (quantise to 255 colours + reserve index 255 as transparent + `transparency=`
  + `disposal=2`). Verify: seek every frame, the transparent-corner alpha must
  be 0 on all of them (not just frame 0).
- GIF is 1-bit alpha (edges thresholded at ~50%) — fine on the dark key
  background, and flat icon art stays within 255 colours. Frame count collapses
  where states repeat (an arpeggio's 4 steps → 4 held frames), which reads as a
  deliberate slow loop, not a bug. Sizes stay ≤~80 KB, well under the 1 MB cap.

## Pre-submission checklist

- [ ] Every icon is 144 × 144 px (`sdicons validate` enforces).
- [ ] `manifest.json`: real Name / Author / URL / Version (`x.y.z`) / License.
- [ ] `icon.svg` thumbnail is on-brand (~56 × 56).
- [ ] Every icon has meaningful `tags` (Marketplace search).
- [ ] `previews/` has up to 3 attractive images.
- [ ] Pack installs by double-click and shows names + tags in Stream Deck.
