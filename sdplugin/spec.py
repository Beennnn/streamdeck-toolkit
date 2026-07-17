"""Verified Elgato Stream Deck **plugin** constraints — single source of truth
for the verifier. Distilled from docs/MARKETPLACE-REVIEW.md (real rejections)
and the manifest schema. Data only, no logic.
"""

# ── manifest ─────────────────────────────────────────────────────────────────
MANIFEST = "manifest.json"
MANIFEST_REQUIRED = ("Name", "UUID", "Version", "Author", "Icon",
                     "CodePath", "SDKVersion", "Actions", "OS", "Software")

# UUID must be reverse-domain (com.author.plugin) and match the folder name
# `<UUID>.sdPlugin`.
UUID_RE = r"^[a-z0-9]+(\.[a-z0-9-]+)+$"
SDPLUGIN_SUFFIX = ".sdPlugin"

# Version: 2–4 numeric components (Elgato uses x.y.z.b for plugin resubmissions).
VERSION_RE = r"^\d+(\.\d+){1,3}$"

# Maker Console greys out "Continue" if these aren't met (§4 of the playbook).
MIN_SDK_VERSION = 3
MIN_SOFTWARE_VERSION = (6, 9)   # Software.MinimumVersion ≥ "6.9"
ACTIONS_MIN, ACTIONS_MAX = 2, 30
# A shipped manifest must NOT enable the Node debugger.
FORBIDDEN_NODEJS_DEBUG = "enabled"

# ── in-app icons that MUST be white monochrome on transparent (§1) ───────────
# These manifest fields render *inside the Stream Deck app* and are tinted by it,
# so a coloured/filled icon is the single most common rejection. Key faces
# (Action States[].Image) and the store icon are NOT in this set — colour is
# fine there. Each value resolves to `<value>.png` AND `<value>@2x.png`.
WHITE_ICON_FIELDS = ("Icon", "CategoryIcon")          # plugin-level
WHITE_ACTION_ICON = "Icon"                            # per-action

# A pixel counts as "opaque" (must then be white) above this alpha; below it the
# pixel is background and ignored. White = each channel ≥ WHITE_MIN.
ICON_ALPHA_OPAQUE = 16
WHITE_MIN = 250
# Fraction of opaque pixels allowed to be non-white before we flag the icon —
# a hair of tolerance for a stray antialiased sub-pixel, not a coloured glyph.
WHITE_NONWHITE_TOLERANCE = 0.02

# Standard raster pairing Elgato expects for every referenced image.
RETINA_SUFFIX = "@2x"

# ── cross-plugin / stale references (§2) ─────────────────────────────────────
# Known Stream Deck connectivity/feature terms that commonly leak across a
# split plugin. A term is FOREIGN to a plugin unless one of its aliases appears
# in the plugin's own identity (Name+Category+UUID+Description). Foreign terms
# found in a user-visible file (ui/*.html, <lang>.json, manifest strings) are
# exactly the "mention of a bluetooth action we don't see included" rejection.
KNOWN_FEATURE_TERMS = {
    "bluetooth": ("bluetooth", "bt"),
    "wifi": ("wifi", "wi-fi", "wireless"),
    "airplay": ("airplay",),
    "hotspot": ("hotspot", "tethering"),
    "vpn": ("vpn",),
    "ethernet": ("ethernet",),
    "midi": ("midi",),
}

# Files a reviewer sees (relative globs inside the .sdPlugin).
VISIBLE_GLOBS = ("ui/*.html", "*.json")
# Localization JSONs + manifest strings are scanned for foreign terms; the
# manifest itself is scanned via its text fields, not as a raw grep target.
