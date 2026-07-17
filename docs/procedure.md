# Complete procedure — from zero to a published Stream Deck icon pack

The end-to-end runbook. Ties the reference docs together into one linear
checklist: [spec.md](spec.md) (what the format requires) and
[publishing.md](publishing.md) (container + Icon Pack Man quirks + Maker
Console wizard). Everything here is verified by having done it (2026-07).

## 0. Prerequisites (once)

- **Python 3.9+** with **Pillow** (`pip install pillow`).
- **`rsvg-convert`** for SVG→PNG (macOS: `brew install librsvg`).
- The **sdicons** toolkit cloned (this repo). Run it as `bin/sdicons …` (no
  install), or set it on your `$PATH`.
- For publishing only: an **Elgato account**; first time also create an
  **organization** and sign the **Maker Agreement** at
  <https://maker.elgato.com> (account/legal steps, done in the browser).

## 1. Scaffold the pack

Each pack is its own folder/repo (keep it separate from this tool).

```sh
sdicons new MyPack --name "My Pack" --author "You"
# creates MyPack/{manifest.json, icons.json, icon.svg, license.txt, icons/}
```

Or, for a content repo where the root *is* the pack, just create
`manifest.json`, `tags.json`, `icon.svg`, `license.txt` and a `src/` folder.

## 2. Author the icons (`src/*.svg`)

- One SVG per icon; `viewBox="0 0 144 144"` (the target canvas).
- Filename = the icon's slug (`grand-piano.svg`) — it becomes the icon id and
  the fallback name. Grep-friendly, lowercase-kebab.
- Style is up to you; flat full-colour reads well on a Stream Deck. Keep a
  consistent visual system across the set.
- Static only for a normal pack (animated needs gif/webp + declaring it).

## 3. Metadata

- **`manifest.json`** — `Name`, `Author`, `Version` (`x.y.z`), `Icon`
  (thumbnail, ~56×56), `Description`, `URL`, `License`. Optional `"Id"` sets
  the reverse-domain pack id.
- **`tags.json`** — `{ "<slug>": { "name": "Display Name", "tags": ["…"] } }`.
  Names and **tags** power Stream Deck's icon-library search — invest here.

## 4. Build → validate → package

```sh
sdicons build src/ MyPack --id com.you.mypack
```

`build` runs render → meta (icons.json) → contact sheet → **validate** →
**package**. Output: `dist/com.you.mypack.streamDeckIconPack` — the
**submit-ready** container (a zip wrapping `com.you.mypack.sdIconPack/`; see
[publishing.md](publishing.md#the-container-format-verified)).

- Fix any `validate` error before shipping (144×144, filenames ≤80, required
  manifest fields, icons.json paths resolve, etc.).
- `--id` (or `manifest.Id`) sets the reverse-domain identity; otherwise it's
  derived `com.<author>.<name>`.

## 5. Test-install locally

Double-click `dist/*.streamDeckIconPack` → it installs into Stream Deck. In the
app: set a key's image → **Icon Library** → open your pack. Verify:

- all icons show with **real names**;
- a **tag search** (a term that's a tag but not in the name, e.g. `808`, `jazz`)
  surfaces the right icons → tags are working.

## 6. Generate the Marketplace media

```sh
sdicons maker-media MyPack --subtitle "one-line pitch" \
  --previews slugA,slugB,slugC,slugD,slugE
# → maker-media/ thumbnail-1920x960.png · preview-1..5.png (144×144) · gallery-*.png (1920×960)
```

These match the Maker Console's exact required dimensions (wrong sizes get
rejected).

## 7. Submit on the Maker Console

<https://maker.elgato.com> → **Products → Create product → Icons**, then the
wizard (full detail in [publishing.md](publishing.md#submit-via-maker-console--full-walkthrough-verified-2026-07-12)):

1. **Details** — disclose **AI content** if any; Type/Theme/Color/Style;
   animated **off** for static packs; Free/Paid (locked after submit).
2. **Upload media** — drop `thumbnail`, up to 5 `preview-N`, ≥3 `gallery-N`
   (native file picks — the human does this).
3. **Submit for review** — Stream Deck ID (reverse-domain), **release notes**
   (required), auto-publish toggle. **You click Submit.**

Elgato reviews; with auto-publish on, it goes live afterwards.

## 8. Updating later

Bump `manifest.Version`, rebuild (steps 4–6), and in Maker Console create a
**new version** with release notes. Same id keeps it the same product.

## Appendix — the Icon Pack Man route (optional)

Elgato's [Icon Pack Man](https://iconpackman.elgato.com/) web tool also packages
a pack, but it **drops icon names/tags on import** and stamps `License: MIT`.
If you use it, fix the export:

```sh
sdicons repair ~/Downloads/com.you.mypack.streamDeckIconPack \
  --tags MyPack/tags.json --license CC-BY-4.0 --url https://github.com/you/mypack
```

`sdicons package` produces the same container directly, so this is only for
when the web tool is specifically required. Details:
[publishing.md](publishing.md#icon-pack-man-quirks-if-you-use-the-web-tool).

## When my icons are (partly) animated

Elgato icon packs may mix static and **animated** icons (GIF/WEBP, 144×144,
~10-20 fps, ≤5 s, < 1 MB). A natural use: the animated icon is the **active
state** — on a Stream Deck, wire state 0 = the static icon (idle) and state 1
= the animated one (playing), driven by a MIDI plugin's state feedback. So a
pack can ship both a static and an animated variant of a sound.

**Author the motion.** Make the animation read as *how the instrument is
played*, and clearly visible (not a 2-pixel flicker): a struck drum bounces,
a held wind sways, plucked strings wobble, a cymbal spins, a synth's waveform
scrolls. Two ways to produce the files:

- **From a motion function** — `phase(t) -> svg` for `t` in [0,1); render it
  with the Python API `sdicons.animate.animate_svg(phase, "src/name.webp")`
  (rsvg renders each phase, assembled into a seamless loop). Good for internal
  motion (moving parts, scrolling screens, spinning reels).
- **From frames** — `sdicons animate <frames-dir> --out name.webp --fps 15`
  assembles a folder of frame images.

**Keep it transparent.** Author with no background rect so the icon composites
on the button colour. **WEBP is the right container** — it carries full alpha
(GIF is 1-bit, jagged) and is ~half the size; its frames replace (no ghosting
trail). Drop the `.webp`/`.gif` into `src/` and `sdicons render` resizes it to
144×144; `validate` accepts it and checks the fps/duration/size budget.

**Show the motion on the Marketplace.** The Maker Console **gallery accepts
MP4** — that's where animation belongs (the thumbnail + icon previews stay
static PNG/JPG). Generate an animated gallery from your animated icons:

```sh
sdicons maker-media MyPack --subtitle "…" --animated path/to/animated-icons/
# → also writes maker-media/gallery-animated.mp4 (upload to the gallery) + .webp
```

Then submit as usual (step 7) — upload the static thumbnail/previews plus the
`gallery-animated.mp4` into the gallery so the listing shows the icons alive.
