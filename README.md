# streamdeck-toolkit

**Build, verify and publish Elgato Stream Deck content — icon packs *and*
plugins — without hitting a Marketplace review rejection.** Two command-line
tools over one shared core, each with a `verify` gate and a `fix` auto-repair
mode distilled from real Maker Console rejections.

| Tool | For | Highlights |
| --- | --- | --- |
| **`sdicons`** | **icon packs** | render SVG→144×144, write `icons.json`, `verify` (companion posters, sizes, tags…), `fix`, package a `.streamDeckIconPack` |
| **`sdplugin`** | **plugins** | `verify` (white in-app icons, no cross-plugin refs, manifest gate), `fix` (whiten icons, generate `@2x`), check a shipped `.streamDeckPlugin` |
| **`sdcommon`** | *shared core* | the `Finding` model + report, coloured output, and the container (zip) verify helper both tools use |

```sh
bin/sdicons  verify MyPack            # icon-pack pre-publication gate
bin/sdicons  fix    MyPack            # auto-repair, then verify
bin/sdplugin verify my.sdPlugin       # plugin pre-publication gate
bin/sdplugin fix    my.sdPlugin       # auto-repair, then verify
```

**Plugin building** (toolchain, skeleton, ship loop, gotchas) →
[docs/PLUGINS.md](docs/PLUGINS.md). **Marketplace review playbook** (the real
rejection checks these tools automate) → [docs/MARKETPLACE-REVIEW.md](docs/MARKETPLACE-REVIEW.md).

> These checks are intentionally simple and rule-based — they'd fit naturally as
> an official pre-publication step. Contributions and upstream adoption welcome.

---

## Icon packs (`sdicons`)

Point it at a folder of SVGs and it renders them to spec, writes the pack
metadata, lints everything against Elgato's requirements, builds a contact
sheet, and packages a `.streamDeckIconPack` ready for
[Icon Pack Man](https://iconpackman.elgato.com/) and the Marketplace.

### Pipeline

```
src/*.svg ──render──▶ MyPack/icons/*.png (144×144)      static SVG/PNG/JPEG
src/*.gif ──render──▶ MyPack/icons/*.gif (144×144, ×N frames)  animated
                      MyPack/icons.json   (names + tags)
                      MyPack/manifest.json
                      ├─ validate ▶ Elgato spec lint (blocks packaging on error)
                      ├─ contact  ▶ contact-sheet.png (eyeball the whole set)
                      └─ package  ▶ dist/<name>-<version>.streamDeckIconPack
```

## Requirements

- Python 3.9+ with [Pillow](https://python-pillow.org/) (`pip install pillow`)
- [`rsvg-convert`](https://gitlab.gnome.org/GNOME/librsvg) for SVG→PNG
  (macOS: `brew install librsvg`)

No install step for the toolkit itself — run it straight from a clone via
`bin/sdicons`.

## Quick start

```sh
# one-shot: render + metadata + validate + contact sheet + package
bin/sdicons build examples/demo-src examples/demo-pack

# or step by step
bin/sdicons new   MyPack --name "My Pack" --author "You"
bin/sdicons render src/ MyPack        # SVG → 144×144 PNG in MyPack/icons/
bin/sdicons meta   MyPack             # (re)generate icons.json
bin/sdicons validate MyPack           # lint against the Elgato spec
bin/sdicons contact  MyPack           # build contact-sheet.png
bin/sdicons package  MyPack           # → dist/*.streamDeckIconPack
```

Try it on the bundled demo:

```sh
bin/sdicons build examples/demo-src examples/demo-pack
# → dist/transport-demo-1.0.0.streamDeckIconPack  (valid, ready to install)
```

## Authoring metadata

Names and tags are derived from filenames by default (`power-on` → *Power On*).
Override per icon with a `tags.json` sidecar in the pack root — hand-tuned
values survive every `meta`/`build` re-run:

```json
{
    "power": { "name": "Power", "tags": ["control", "power", "transport"] }
}
```

## Commands

| Command | Does |
|---|---|
| `new`      | scaffold an empty, spec-shaped pack |
| `render`   | source dir → 144×144 icons in `pack/icons/` (SVG/PNG/JPEG static, GIF/WEBP animated frame-by-frame) |
| `meta`     | (re)generate `icons.json` from `icons/` + `tags.json` |
| `validate` | lint the pack against the Elgato spec (exit 1 on error) |
| `verify`   | **pre-publication gate** — check only, never writes (`--strict`; also verifies a shipped `.streamDeckIconPack`) |
| `fix`      | **auto-repair** safe defects (regenerate missing/bad companion posters, split `", "` tags), then verify |
| `posters`  | generate companion poster PNGs for animated icons (required by the Icon Library) |
| `contact`  | build a contact-sheet PNG of the whole palette |
| `package`  | build a **submit-ready** `.streamDeckIconPack` (correct `<id>.sdIconPack/` container) |
| `build`    | all of the above, end to end |
| `repair`   | fix an Icon Pack Man export (re-inject names/tags from `tags.json`) |
| `maker-media` | generate Maker Console upload assets (thumbnail/previews/gallery at exact dims) |
| `animate`  | assemble frame images into a looping GIF/WEBP animated icon (144×144, spec-checked) |

## Animated icons

Elgato icon packs accept animated **GIF** and **WEBP** (Stream Deck plays them
on the key). `render` treats them as first-class: every frame is resized to
144×144 with per-frame timing, loop count, and transparency preserved. Small
LED-matrix effect GIFs (72×72) become a spec-conformant pack without touching
a single file by hand:

```sh
bin/sdicons render effects-src/ WledEffects   # 72×72 .gif → 144×144 .gif
```

Resample filter defaults per source — **lanczos** for smooth static art
(gradients, illustrations), **nearest** for animation so an integer upscale
doubles pixels crisply instead of blurring the LED grid. Override with
`--resample {nearest,bilinear,bicubic,lanczos}`. Animated GIFs stay in palette
mode (nearest), so a ×2 upscale is a lossless pixel double and identical
consecutive frames merge without changing the loop. `validate` warns when an
animation drifts outside Elgato's fps/duration guidance or the ~1 MB budget.

## Publishing

`sdicons package` emits the **exact container Elgato expects** (a
`.streamDeckIconPack` zip wrapping a `<id>.sdIconPack/` folder), so the output
is **submit-ready**: double-click to install, or upload to the Maker Console —
no Icon Pack Man web tool required. If you *do* use Icon Pack Man, it mangles
icon names/tags on import; `sdicons repair` fixes the export.

**Start here: [docs/procedure.md](docs/procedure.md)** — the complete
end-to-end runbook (zero → published pack). The hard-won detail (container
format, Icon Pack Man quirks, Maker Console wizard) is in
[docs/publishing.md](docs/publishing.md); the enforced spec in
[docs/spec.md](docs/spec.md).

## Packs built with it

- **[Stage Keys](https://github.com/Beennnn/streamdeck-stage-keys)** — 83
  full-colour sound-select icons for the live keyboardist: the complete
  General MIDI / XP set (all 128 programs) plus modern synth categories. Lives
  in its own repo (built with this toolkit).
- **[WLED icons](https://github.com/Beennnn/streamdeck-wled-icons)** — the
  WLED visual set as two packs: **216 animated effect GIFs** (the first pack to
  exercise the animated pipeline) + **111 static** palette/control icons.

## License

MIT — see [LICENSE](LICENSE).
