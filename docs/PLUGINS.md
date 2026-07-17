# Building Stream Deck plugins

Tools, commands and gotchas for **building, packaging and shipping Elgato Stream
Deck plugins** — collected from real plugins (a Wi-Fi/Bluetooth switcher, a MIDI note
display, …). It's a reference, not a framework: a checklist you can copy from.

> Focus: **macOS**, TypeScript plugins, distribution on the **Elgato Marketplace**
> (Maker Console) and via GitHub releases.

---

## Reference plugins (worked examples)

Open-source plugins these notes come from — read them alongside for real code:

- **[Wi-Fi Switcher](https://github.com/Beennnn/streamdeck-wifi-picker)** — switch
  between saved Wi-Fi networks from a key or a Stream Deck+ dial (macOS); a deep
  dive on the **macOS Location wall** and the honest limits.
- **[Bluetooth Switcher](https://github.com/Beennnn/streamdeck-bluetooth-switcher)** —
  connect / disconnect paired Bluetooth devices from a key or dial; **bundles a
  universal `blueutil`** — the native-helper + quarantine pattern in practice.
- **[MIDI Note Display](https://github.com/Beennnn/streamdeck-midi-note-display)** —
  a Stream Deck+ dial showing a MIDI value as a note name + mini piano — the
  custom **dial-layout** technique in the wild.

---

## The toolchain

| Tool | What it does | Install |
| --- | --- | --- |
| **[Node.js](https://nodejs.org)** 20+ | Runtime Stream Deck runs the plugin on | `brew install node` |
| **[@elgato/cli](https://www.npmjs.com/package/@elgato/cli)** (`streamdeck`) | Scaffold, **validate**, **pack**, **link**, **restart**, view logs | `npm i -g @elgato/cli` |
| **[@elgato/streamdeck](https://www.npmjs.com/package/@elgato/streamdeck)** | The plugin SDK (actions, settings, feedback, i18n) | `npm i @elgato/streamdeck` |
| **[Rollup](https://rollupjs.org)** + `@rollup/plugin-typescript`, `-commonjs`, `-node-resolve` | Bundle `src/*.ts` → one inlined `bin/plugin.js` (the SD runtime has no `node_modules`) | dev deps |
| **[TypeScript](https://www.typescriptlang.org)** | Typed plugin code | dev dep |
| **[librsvg](https://gitlab.gnome.org/GNOME/librsvg)** (`rsvg-convert`) | Rasterize SVG icons → the PNG sizes SD wants | `brew install librsvg` |
| **[blueutil](https://github.com/toy/blueutil)** *(optional)* | Example of a **bundled native helper** (Bluetooth connect) | `brew install blueutil` |
| **[Maker Console](https://maker.elgato.com)** | Submit & manage Marketplace products | web |

---

## Project skeleton

```
my-plugin/
├─ src/
│  ├─ plugin.ts              # entry: registers actions, calls streamDeck.connect()
│  └─ actions/*.ts           # one SingletonAction per action (@action({UUID}))
├─ com.author.myplugin.sdPlugin/
│  ├─ manifest.json          # the plugin definition (see below)
│  ├─ bin/plugin.js          # rollup output (gitignored)
│  ├─ imgs/…                 # icons (rasterized from SVG)
│  ├─ ui/*.html              # Property Inspector (settings panels)
│  ├─ layouts/*.json         # Stream Deck+ dial touch layouts
│  └─ <lang>.json            # locale files (en, fr, de, es, ja, ko, zh_CN)
├─ assets/*.svg + gen-icons.mjs
├─ rollup.config.mjs
├─ tsconfig.json
└─ package.json
```

Start one with `streamdeck create` (interactive scaffolder).

---

## The build / ship loop

```bash
npm run build                      # rollup -c → bin/plugin.js
streamdeck validate  my.sdPlugin   # schema + rules check
streamdeck link      my.sdPlugin   # symlink into Stream Deck (dev install)
streamdeck restart   com.author.myplugin   # reload the running plugin
npm run pack                       # → dist/*.streamDeckPlugin  (installer)
```

Handy `package.json` scripts:

```json
{
  "build": "rollup -c",
  "watch": "rollup -c -w --watch.onEnd=\"streamdeck restart com.author.myplugin\"",
  "icons": "node assets/gen-icons.mjs",
  "validate": "streamdeck validate com.author.myplugin.sdPlugin",
  "pack": "streamdeck pack com.author.myplugin.sdPlugin --output dist --force"
}
```

Two plugins from one repo? Make `rollup.config.mjs` export an **array** of bundles
(one input + output each) and chain `&&` in the validate/pack scripts. Pass a
per-bundle `outDir` to `@rollup/plugin-typescript` or it errors on the second one.

---

## `sdplugin` — automate the pre-submission checklist

The checks a script *can* run are run for you. `sdplugin` is the plugin
sibling of `sdicons` (the icon-pack tool in this repo): it
encodes the automatable half of [docs/MARKETPLACE-REVIEW.md](MARKETPLACE-REVIEW.md)
so a plugin never gets rejected for something detectable ahead of time.

Two modes — **`verify`** (check only, never writes) and **`fix`** (auto-repair,
then re-verify):

```sh
bin/sdplugin verify path/to/<uuid>.sdPlugin          # check a plugin directory
bin/sdplugin verify dist/foo.streamDeckPlugin        # check the SHIPPED bytes
bin/sdplugin fix    <uuid>.sdPlugin                  # auto-repair, then verify
bin/sdplugin verify <plugin> --strict                # warnings become blocking
bin/sdplugin verify <plugin> --foreign bluetooth,vpn # force-forbid feature terms
```

**`fix`** auto-repairs the safe, unambiguous defects from our own rejections:
it **whitens** coloured in-app icons (RGB→`#FFFFFF`, alpha kept — never touching
key `States[].Image` art) and **generates missing `@2x`** variants. Foreign
references are reported, never auto-edited (they need human intent). Idempotent.
(`bin/sdplugin-verify …` stays as a compat alias for `bin/sdplugin verify …`.)

> Rule-based and self-contained — a good fit for an official pre-publication
> check. Contributions and upstream adoption welcome.

It catches the two real rejection classes plus the manifest gate:

- **`non-white-icon`** (§1) — plugin `Icon`, `CategoryIcon` and every action
  `Icon` (`@1x`+`@2x`) must be white `#FFFFFF` monochrome on transparent. Key
  `States[].Image` faces and the store icon are correctly *exempt* (colour OK).
- **`foreign-reference`** (§2) — a user-visible file (`ui/*.html`, `<lang>.json`,
  manifest strings) naming a feature the plugin doesn't ship ("mention of a
  bluetooth action we don't see included"). Foreign terms are auto-derived: every
  known feature term the plugin doesn't own in its Name/Category/UUID/Description.
- Manifest gate (§4): `SDKVersion`≥3, `Software.MinimumVersion`≥6.9, 2–30 actions,
  no `Nodejs.Debug`, valid reverse-domain UUID matching the folder, all referenced
  images (`@1x`+`@2x`) and Property Inspector files present.

Requires Python 3 + Pillow. Tests: `python3 -m pytest tests/` (52 cases, ~97%
coverage). The **human-only** steps — demo video, gallery re-shoot, the final
Submit — stay in the doc; the tool never claims those are done.

## Marketplace requirements (the ones that block submission)

> **Getting through the human review** is a separate skill from meeting the
> machine checks — white in-app icons, no stale cross-plugin references, a strong
> gallery, and a demo video are what actually get plugins rejected. Full rejection
> log + fixes + a pre-submission checklist: **[docs/MARKETPLACE-REVIEW.md](MARKETPLACE-REVIEW.md)**.
> Run **`bin/sdplugin verify`** (above) to check the automatable items in one shot.

Maker Console silently disables **Continue** if these aren't met — check them first:

- **`SDKVersion`: 3** (or later)
- **`Software.MinimumVersion`: "6.9"** (Stream Deck 6.9+)
- **DRM**: enable it via the **toggle in Maker Console** (not a manifest/CLI field).
- **Actions**: 2–30 per plugin. **Plugin name unique** on Marketplace.
- No **`Nodejs.Debug: "enabled"`** in a shipped manifest (dev-only debug port).

Publishing a JS plugin needs **no Apple signing / no Developer account** — it runs
inside the Stream Deck app. You do need a (free) **Maker Console** account.

### Icon sizes (per [Elgato guidelines](https://docs.elgato.com/guidelines/stream-deck/plugins/))

| Asset | Size |
| --- | --- |
| Plugin / marketplace icon | 256×256 **and** 512×512 PNG |
| Category / action-list icon | 20×20 + 40×40 (or 28×28 + 56×56), monochrome white on transparent |
| Key icon | 72×72 (144×144 @2x) |
| Dial touch layout | 200×100 |

---

## Icons pipeline

Keep **SVG sources** in `assets/`, rasterize to the exact PNGs with `rsvg-convert`
via a small `gen-icons.mjs` (`npm run icons`). Recolour a single-colour glyph per
state by string-replacing the fill and re-rasterizing — cheap way to get
amber/green/grey state variants without hand-editing files.

---

## Localization (i18n)

Ship one **`<lang>.json`** at the `.sdPlugin` root per language, each with a top-level
`"Localization"` object. Stream Deck picks the user's language automatically.

- Keys = the **English string** (manifest `Name`/`Tooltip`, or a dotted key like
  `dial.connecting`). Values = the translation. English is the fallback.
- In code: `streamDeck.i18n.t("dial.connecting")`.
- Standard set: `en, fr, de, es, ja, ko, zh_CN` (+ `zh_TW`).
- **sdpi-components does NOT translate plain PI labels** (only `__MSG_key__`, and it
  never loads your locales) — swap `label`/`placeholder`/button text yourself in a
  small script if you localize the settings panel.

---

## Stream Deck+ dial layouts

A custom touch layout is a `layouts/*.json` with an `id` and `items` (pixmap/text,
each with a `rect [x,y,w,h]` on a 200×100 canvas). Reference it from the action's
`Encoder.layout`. Update it live from code with
`action.setFeedback({ key: value })` — a text item accepts `{ value, color }` for
per-state colour. **Bump the layout `id`** when you change it, or Stream Deck serves
the cached one.

---

## Bundling a native helper (advanced)

If macOS has no API for what you need (e.g. connecting a Bluetooth device), bundle a
small binary in the plugin instead of asking users to `brew install`:

1. Put it in `helpers/`, ship a **universal** build (`clang -arch arm64 -arch
   x86_64 …` or `lipo`).
2. Resolve its path at runtime from `import.meta.url` (relative to `bin/plugin.js`).
3. On first use, **clear the Gatekeeper quarantine** on your own bundled binary:
   `xattr -dr com.apple.quarantine <path>` (no admin needed) + `chmod 0755`.
4. Respect the binary's licence (attribution for MIT, etc.).

---

## Distribution

- **Elgato Marketplace** — `npm run pack` → upload the `.streamDeckPlugin` in
  [Maker Console](https://maker.elgato.com), fill the listing, submit for review.
- **GitHub release** — attach the `.streamDeckPlugin`; users double-click to install.
  Great fallback while a Marketplace review is pending, or for beta builds.

---

## Gotchas I've actually hit

- **Multiple actions that share state → one refresh loop, not one per action.** If a
  plugin has several `SingletonAction`s that reflect the same live state (e.g. a
  Connect tile + an on/off tile), do NOT give each its own `setInterval` — they drift
  out of step and each re-queries the OS. Put a **single shared hub** in its own
  module: one loop takes one snapshot per tick and drives every action's render in
  the SAME tick; each action `hub.subscribe(fn)` and reads the snapshot. Keep renders
  **idempotent** (emit `setState`/`setTitle` only when the value changed) so a steady
  tick sends nothing and writes no SDK log, and throttle the slow queries (a rarely-
  changing radio state, a heavy `system_profiler`) inside the hub. Worked example:
  the Bluetooth/Wi-Fi switchers' `src/hub.ts` (see their `docs/REFRESH-HUB.md`).

- **Colour-code a multi-purpose tile with extra `States` + `DisableAutomaticStates`.**
  A radio on/off tile reads better as off / idle / connecting / connected (grey /
  blue / amber / green) than a bare on/off. Add the extra entries to the manifest
  `States` array and set **`DisableAutomaticStates: true`** — otherwise a press
  cycles through every state instead of toggling; you drive the index yourself.

- **`@action({UUID})` must sit directly above the class.** Slipping a `const`/comment
  between the decorator and `export class …` detaches it → *"The action's manifestId
  cannot be undefined"* and the plugin crash-loops. (The `tsc` "Decorators are not
  valid here" warning is the real tell.)
- **Periodic `setInterval` re-renders must read `await action.getSettings()` fresh** —
  not the settings captured at `onWillAppear`. Otherwise a key added empty keeps
  re-rendering its placeholder and overwrites a later selection.
- **Rollup + two bundles:** give each a `outDir` under its own plugin dir, or the TS
  plugin errors (`outDir must be inside the same directory as the 'file' option`).
- **Maker Console upload flow is finicky:** after a refresh the file can show but
  *Continue* stays greyed — re-select the file to re-trigger validation.
- **macOS Wi-Fi is Location-gated:** apps can't read SSID names without Location, and
  a plugin can't get Location — so no in-range scan and no instant precise join. Plan
  around it. (Long write-up in the wifi-picker repo.)

---

## Links

- [Stream Deck SDK docs](https://docs.elgato.com/streamdeck/sdk/introduction/getting-started/)
- [Plugin guidelines](https://docs.elgato.com/guidelines/stream-deck/plugins/)
- [Distribution](https://docs.elgato.com/streamdeck/sdk/introduction/distribution/)
- [Maker Console](https://maker.elgato.com) · [Become a Maker](https://docs.elgato.com/makers/general/become-a-maker/)

---

*MIT licensed — copy freely.*
