# Getting a plugin through Elgato Marketplace review

The review is done by a human at Elgato, and the same handful of things get a
plugin bounced every time. This is the **rejection log + the fixes**, so the next
submission passes on the first pass. It complements the toolkit
[README](../README.md) (build/pack/ship) — this file is *what the reviewer
actually checks and rejects.*

> **Two tracks, two homes.** This file is for **plugins**
> (`.streamDeckPlugin`). Icon **packs** (`.streamDeckIconPack`) have their own
> verified guide + rejection log in
> [publishing.md](publishing.md).
> The **Maker Console media** specifics (gallery 1920×960, no cropping, RGBA
> previews, release-notes Unicode) are documented there and apply to plugin
> galleries too — cross-referenced below rather than duplicated.

---

## Rejection log

### 2026-07-16 — Wi-Fi Switcher 1.43 + Bluetooth Switcher 1.1.1 (both rejected)

The two plugins were rejected the same day with near-identical feedback. Verbatim:

> - We'd like to see the media for the product page updated to better showcase
>   the product, we noticed a lot of misalignment issues with visual elements,
>   mention of a bluetooth action that we don't see included [Wi-Fi only]. Please
>   bear in mind that all products for Marketplace require **3 images or videos**
>   for the product page. […] checking out Elgato's **Volume Controller** product
>   page as a great example.
> - The icons used inside the Stream Deck app for **category and actions will
>   need to be white**.
> - We'd also like to request a **short demo video be sent to us via email at
>   maker@elgato.com** so we can verify functionality before approving.

Three distinct classes of problem, each with a durable fix below:

1. **In-app icons weren't white** → §1.
2. **Stale cross-plugin references in the media** (a Bluetooth screenshot on the
   Wi-Fi listing) → §2.
3. **Weak gallery + a demo video is expected** → §3.

Fixes shipped: white icons + Bluetooth-reference purge in
[wifi-picker](https://github.com/Beennnn/streamdeck-wifi-picker) (v1.44) and white
icons in [bluetooth-switcher](https://github.com/Beennnn/streamdeck-bluetooth-switcher)
(v1.1.2). Gallery re-shoot + demo video + resubmit remain manual.

---

## §1 — In-app icons must be white (monochrome, transparent)

The single most common rejection. Elgato's
[icon guideline](https://docs.elgato.com/guidelines/stream-deck/plugins#icons):
category + action-list icons must be **white `#FFFFFF`, monochromatic, transparent
background — no colour, no solid tile.** They're rendered by the Stream Deck app,
which tints them; a coloured or filled icon looks wrong in the actions list.

**Which images this rule covers vs not:**

| Manifest field | Rendered where | Rule |
| --- | --- | --- |
| `Icon` (`imgs/plugin/icon`) | Plugin header **inside the app** | **white monochrome** |
| `CategoryIcon` (`imgs/plugin/category`) | Actions-list category **inside the app** | **white monochrome** |
| Action `Icon` (`imgs/actions/*/icon`) | Each action row **inside the app** | **white monochrome** |
| Action `States[].Image` (the key faces) | The physical **key** | **colour OK** — this is the button art |
| Dial layout images | Stream Deck+ touch strip | colour OK |
| Marketplace **store** icon (256/512 PNG) | The web listing | **colour / branded** — keep your tile here |

**The fix pattern** (what we did, in `gen-icons.mjs`):

- Keep a white-glyph SVG on a transparent background (`glyph.svg` / `bt-glyph.svg`)
  and point the plugin `icon`, `category`, and every action `icon` job at it.
- For a "picker" action icon that needs a chevron, make a white variant of the
  glyph+chevron (`picker-*-white.svg`) — still pure `#FFFFFF`.
- Leave the coloured tile (`tile.svg`) wired **only** to the 256/512 store icon.
- `npm run icons` re-rasterizes. Verify by dropping the `@2x` PNGs on a **dark**
  background (that's the app's sidebar) — they should read as clean white — and on
  a checkerboard to confirm the background is transparent, not black/white filled.

Sizes (unchanged): category 28+56, action 20+40, key 72+144, store 256+512.

---

## §2 — No stale or cross-plugin references anywhere a reviewer sees

The Wi-Fi plugin was flagged for "mention of a bluetooth action that we don't see
included." Root cause: it **used to bundle Bluetooth**, and the split into two
plugins left Bluetooth traces behind — in a gallery screenshot **and** in the
Property Inspector UI strings.

Reviewers open the Property Inspector and read your gallery. Anything describing a
feature the plugin doesn't have reads as a broken/misleading listing. Sweep for it:

```sh
# from the plugin repo — anything the reviewer could see that names another feature
grep -rniE 'bluetooth|wifi|<other-feature>' <uuid>.sdPlugin/ui <uuid>.sdPlugin/*.json | grep -v /logs/
git ls-files docs/screenshots assets/marketplace   # no wrong-plugin images
```

Fix: remove the wording from the visible UI (`ui/*.html` + any i18n override),
delete dead localisation entries, and delete stray screenshots/app-icons of the
other plugin from the repo so they can't be re-uploaded. (A code comment that says
"no Bluetooth here" is fine — not user-visible.)

**Lesson for split/multi-plugin repos:** when you fork one plugin out of another,
audit the *loser* side for orphaned strings, screenshots, and i18n keys the same
day. They don't cause a build error — only a review rejection weeks later.

---

## §3 — Product-page media + the demo video

**Gallery minimums (hard):** every product needs **≥ 3 images or videos**. They
must *showcase the product* and be visually clean — the 2026-07-16 rejection cited
"a lot of misalignment issues with visual elements." Use Elgato's **Volume
Controller** listing as the bar. Prefer real captures over renders.

**Media dimensions & the cropping trap** are identical to the icon-pack track and
already documented once — read
[publishing.md → Upload media / Media gotchas](publishing.md#store-previews):

- Gallery images **1920×960** (2:1); **the content must fit, not just the file** —
  both WLED packs were rejected for a bottom row sliced off a file that *was*
  1920×960. Eyeball the rendered image, don't trust `sips` dimensions.
- Icon-preview slots want **transparent RGBA**, never opaque RGB (silent reject).
- Thumbnails/gallery banners stay opaque RGB.

**The demo video (plugin-specific):** Elgato may **ask for a short screen-recording
by email to `maker@elgato.com`** to verify the plugin actually works before
approving. Record the real flow on the target Mac (e.g. connect → connected state
→ disconnect), email it, then resubmit. This is a human step — it needs the live
hardware/software. Budget for it: a resubmission won't clear until they've seen it.

---

## §4 — Manifest requirements that silently block *Continue*

From the toolkit README, restated because they're review-adjacent. Maker Console
greys out **Continue** if any are wrong:

- `SDKVersion`: **3**+ · `Software.MinimumVersion`: **"6.9"**+
- **DRM**: enabled via the **toggle in Maker Console** (not a manifest field)
- **2–30 actions**; **plugin name unique** on Marketplace
- **No** `Nodejs.Debug: "enabled"` in a shipped manifest
- `streamdeck validate` passes clean (schema + rules) before you upload

**AI-content disclosure:** the wizard asks whether the product contains AI-generated
content. If an assistant produced art/code, disclose it honestly — Elgato allows it
*with* disclosure.

---

## §5 — Resubmitting an already-submitted plugin

Same mechanics as icon-pack versions (verified for packs 2026-07-16; the plugin
flow mirrors it):

- **Versions tab → Create version** — drop the new `.streamDeckPlugin`, required
  **release notes** (≤1500 chars), auto-publish toggle, Submit.
- **"Create version" is disabled only while a prior version is *Pending review*.**
- **Media is product-level** (Media tab) — update the gallery **any time**, even
  while a version is pending; it's not part of the Create-version modal.
- **Release-notes editor rejects some Unicode** (em-dashes dropped silently) — use
  ASCII hyphens and confirm the char counter moved.
- **Resubmit via "Create version" with a BUMPED number — not "Revise".**
  Empirically (Stage Keys 1.2.0->1.2.1, Wi-Fi 1.43->1.44.2), Maker Console's
  **Create version** accepts a higher version and clears the resubmission. The
  **Revise** button instead replaces the rejected version in place and demands
  the EXACT same number, which throws *"revised version does not match existing
  version"* (or *"X is not higher than Y"* on a published product). Simplest
  reliable path: bump the manifest `Version` (`x.y.z.b`), repackage, and use
  **Create version**. Keep the package's manifest version = the number you enter.

---

## Pre-submission checklist (plugins)

> **Automate the machine-checkable rows first:** `bin/sdplugin verify
> <uuid>.sdPlugin` (or `dist/*.streamDeckPlugin`) checks white icons (§1),
> foreign references (§2), and the manifest gate (§4) in one shot; `bin/sdplugin
> fix <uuid>.sdPlugin` auto-repairs the safe ones (white icons, @2x). The
> ⌨️-marked rows below are what it covers; the rest are human-only.

Run top to bottom before every submit / resubmit:

- [ ] `streamdeck validate <uuid>.sdPlugin` → clean.
- [ ] Plugin `Icon` + `CategoryIcon` + every action `Icon` are **white monochrome
      on transparent** (checked on a dark background). Coloured tile only on the
      256/512 store icon. §1
- [ ] Key `States[].Image` render correctly (colour is fine here).
- [ ] `grep` the shipped `.sdPlugin` (ui + locale json) for **any feature the
      plugin doesn't have**; zero hits. §2
- [ ] No stray screenshots/app-icons of another plugin in `docs/`, `assets/`. §2
- [ ] Gallery: **≥3** clean, aligned media; **1920×960 content-fit**, no cropping;
      previews transparent RGBA. §3
- [ ] A **demo video** is recorded and ready to email to `maker@elgato.com`. §3
- [ ] Manifest: `SDKVersion` ≥3, `Software.MinimumVersion` ≥"6.9", 2–30 actions,
      unique name, no `Nodejs.Debug`. §4
- [ ] DRM toggle set in Maker Console; AI-content disclosed if applicable. §4
- [ ] `Version` bumped; release notes written in **ASCII** (no em-dashes). §5
- [ ] `npm run pack` → fresh `dist/*.streamDeckPlugin` is the file you upload.

**Human-only (can't be automated):** Elgato login + Maker Agreement, native file
drops for media/package, the demo-video email, and the final **Submit for review**.

---

*Distilled from real Marketplace review feedback.*
