"""Verified Elgato Stream Deck Icon Pack specification.

Single source of truth for every constraint the validator enforces.
Facts distilled from the official Elgato Maker docs (fetched 2026-07-12):
  - https://docs.elgato.com/stream-deck/icons/getting-started/
  - https://docs.elgato.com/stream-deck/icons/api/
Keep this module data-only — no logic. If Elgato changes the spec, this
is the ONE place to update, and docs/spec.md mirrors it in prose.
"""

# Canvas: every icon must be exactly 144 x 144 px (raster). SVGs are
# rendered onto this canvas; static rasters are checked against it.
ICON_SIZE = 144

# The pack thumbnail (manifest "Icon") is recommended at 56 x 56 px.
THUMBNAIL_SIZE = 56

# Allowed icon file formats. Static vs animated split matters only for
# guidance (fps/duration), not for pack validity.
STATIC_FORMATS = (".svg", ".png", ".jpg", ".jpeg")
ANIMATED_FORMATS = (".gif", ".webp")
ICON_FORMATS = STATIC_FORMATS + ANIMATED_FORMATS

# Elgato caps icon filenames at 80 characters (basename incl. extension).
MAX_FILENAME_LEN = 80

# Animated-icon guidance (soft — warnings, not errors).
ANIM_FPS_RANGE = (10, 20)
ANIM_MAX_SECONDS = 5
ANIM_MAX_BYTES = 1_000_000  # ~1 MB preferred ceiling

# ── Animated-icon companion poster (HARD requirement — verified against
# iconpackman's exported packs) ──────────────────────────────────────────────
# The Stream Deck **Icon Library** renders each icon's grid cell from a STATIC
# poster image; for an animated icon it plays the GIF/WEBP only on hover. So a
# GIF with NO poster shows a broken tile — the "the preview images of the GIFs
# aren't loading, please ensure this icon pack is packaged correctly via
# iconpackman" review rejection.
# iconpackman guarantees the poster: for every `<base>.gif` it emits a sibling
# `<base>.png` built from the GIF's first frame, written into `icons/<base>.png`.
# The poster is NOT listed in icons.json — it is resolved by same-base-name
# convention. `sdicons package` reproduces this exactly, and `verify` FAILS a
# pack whose animated icons lack their companion poster.
POSTER_EXT = ".png"  # companion poster for an animated icon shares its base name

# manifest.json required + optional fields (exact casing Elgato expects).
MANIFEST_REQUIRED = ("Name", "Author", "Version", "Icon")
MANIFEST_OPTIONAL = ("Description", "URL", "Licence", "License")

# Version must be three numeric components, e.g. "1.0.2".
VERSION_RE = r"^\d+\.\d+\.\d+$"

# icons.json: array of objects, each with these keys.
ICON_ENTRY_REQUIRED = ("path", "name", "tags")

# Canonical pack layout produced by the toolkit.
FILE_MANIFEST = "manifest.json"
FILE_ICONS_JSON = "icons.json"
FILE_LICENSE = "license.txt"
DIR_ICONS = "icons"
DIR_PREVIEWS = "previews"   # optional store-preview images (png/jpg, up to 3)

# Container format (verified 2026-07-12 against an Icon Pack Man export):
# the shippable file is a ZIP named `<id>.streamDeckIconPack` whose single
# top-level entry is a folder `<id>.sdIconPack/` holding the pack. Stream
# Deck derives the pack identity from that folder name (reverse-domain id).
PACK_EXT = ".streamDeckIconPack"   # extension of the shippable zip
SDICONPACK_SUFFIX = ".sdIconPack"  # suffix of the required wrapper folder

# Elgato Maker Console (maker.elgato.com — NOT console.elgato.com) is where a
# pack is submitted for review. Its "Upload media" step wants these exact
# sizes (verified 2026-07-12 against the live wizard):
MAKER_URL = "https://maker.elgato.com"
MAKER_HERO_SIZE = (1920, 960)   # thumbnail + gallery IMAGES, 2:1 (png/jpg)
MAKER_VIDEO_SIZE = (1920, 1080) # gallery VIDEO, 16:9 (mp4) — verified 2026-07-14
                                # against the wizard: mp4 must be 1920×1080, not
                                # 1920×960 (a 960 mp4 is rejected at upload).
MAKER_PREVIEW_SIZE = 144        # the 5 "icon preview" tiles, 1:1
