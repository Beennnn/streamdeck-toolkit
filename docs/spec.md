# Elgato Stream Deck Icon Pack — spec (as enforced by `sdicons validate`)

Distilled from the official Elgato Maker docs (fetched 2026-07-12). Mirrors
`sdicons/spec.py`, which is the machine-readable source of truth.

- [Icons — Getting Started](https://docs.elgato.com/stream-deck/icons/getting-started/)
- [Icons — API glossary (manifest.json / icons.json schema)](https://docs.elgato.com/stream-deck/icons/api/)
- [Icon Pack Man packager](https://iconpackman.elgato.com/)

## Pack layout

```
MyPack/
├── manifest.json    # pack metadata (required)
├── icons.json       # per-icon metadata array (required)
├── icon.svg         # pack thumbnail, ~56×56 px (referenced by manifest.Icon)
├── license.txt      # licence text (recommended)
└── icons/           # the icons themselves
    ├── icon_1.svg
    └── icon_2.png
```

## Icon files

| Rule | Value |
|---|---|
| Dimensions | **144 × 144 px** (all icons) |
| Static formats | SVG, PNG, JPEG |
| Animated formats | GIF, WEBP |
| Filename length | ≤ 80 characters |
| Animated fps (guidance) | 10–20 fps, ≤ 5 s, preferably < 1 MB |

## manifest.json

```json
{
    "Name": "Awesome Icons",
    "Version": "1.0.0",
    "Description": "Awesome icons for making your Stream Deck look... awesome!",
    "Author": "John Doe",
    "URL": "https://www.elgato.com",
    "Icon": "icon.svg",
    "License": "license.txt"
}
```

| Field | Required | Notes |
|---|---|---|
| `Name` | yes | shown in Stream Deck |
| `Author` | yes | maker name |
| `Version` | yes | three numeric components, e.g. `1.0.2` |
| `Icon` | yes | relative path to the ~56×56 thumbnail |
| `Description` | no | shown in Stream Deck |
| `URL` | no | more-info link |
| `Licence` / `License` | no | relative path to a licence txt (both spellings seen in docs) |

## icons.json

Array of objects, one per icon:

```json
[
    { "path": "icon_1.svg", "name": "Train", "tags": ["travel"] },
    { "path": "icon_2.svg", "name": "Salad", "tags": ["food"] },
    { "path": "icon_3.svg", "name": "Bike",  "tags": ["travel", "sport"] }
]
```

| Field | Required | Notes |
|---|---|---|
| `path` | yes | relative to `icons/` |
| `name` | yes | display name |
| `tags` | yes | searchable tags (array of strings) |

## Packaging & publishing

The shippable file is a **ZIP** named `<id>.streamDeckIconPack` containing a
single wrapper folder `<id>.sdIconPack/` (verified 2026-07-12):

```
com.you.mypack.streamDeckIconPack   (zip)
└── com.you.mypack.sdIconPack/       (Stream Deck reads the id from this name)
    ├── manifest.json
    ├── icons.json
    ├── icon.svg
    ├── license.txt
    ├── icons/
    └── previews/   (optional, ≤3 store previews)
```

`<id>` is reverse-domain (`com.you.mypack`). `sdicons package` emits exactly
this, so it's submit-ready without the Icon Pack Man web tool. Double-clicking
the file installs the pack; distribution goes through the **Maker Console**
after review. Full process + Icon Pack Man quirks: [publishing.md](publishing.md).
