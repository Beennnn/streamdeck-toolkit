"""Auto-repair the plugin defects we KNOW how to fix safely — the "fix it for me"
half of the verifier, distilled from real Marketplace rejections.

Safe, unambiguous fixes only:
  * non-white in-app icons (§1) → whiten: force every pixel's RGB to #FFFFFF while
    keeping its alpha, so the glyph becomes pure white on transparent — exactly
    what Elgato's in-app icon guideline wants. Applied ONLY to the in-app icon
    fields (plugin Icon, CategoryIcon, each action Icon, @1x+@2x); key
    States[].Image faces and the store icon are left untouched (colour is correct
    there).
  * a missing @2x retina variant → generate it by a 2× nearest upscale of the @1x
    (nearest keeps a crisp glyph; it's a stopgap, a hand-drawn @2x is still better).

NOT auto-fixed (needs a human): foreign/cross-plugin references (we can't know the
right replacement text), any manifest field, missing @1x base images. Those stay
in the verify report. `autofix` returns `(code, detail)` records of what it changed.
"""
import json
from pathlib import Path

from PIL import Image

from . import spec


def _in_app_icon_refs(manifest: dict):
    """Manifest image refs that must be white monochrome (the in-app icons)."""
    refs = []
    for f in spec.WHITE_ICON_FIELDS:
        if manifest.get(f):
            refs.append(manifest[f])
    for a in (manifest.get("Actions") or []):
        if a.get(spec.WHITE_ACTION_ICON):
            refs.append(a[spec.WHITE_ACTION_ICON])
    return refs


def _pngs_for(plugin: Path, ref: str):
    base = plugin / ref
    return [base.with_suffix(".png"),
            base.parent / f"{base.name}{spec.RETINA_SUFFIX}.png"]


def _needs_whitening(png: Path) -> bool:
    try:
        with Image.open(png) as im:
            raw = im.convert("RGBA").tobytes()
    except Exception:
        return False
    for i in range(0, len(raw), 4):
        if raw[i + 3] >= spec.ICON_ALPHA_OPAQUE:
            if not (raw[i] >= spec.WHITE_MIN and raw[i + 1] >= spec.WHITE_MIN
                    and raw[i + 2] >= spec.WHITE_MIN):
                return True
    return False


def _whiten(png: Path):
    """Force RGB=255 on every pixel, keep alpha → white glyph on transparent."""
    with Image.open(png) as im:
        rgba = im.convert("RGBA")
    alpha = rgba.getchannel("A")
    white = Image.new("RGBA", rgba.size, (255, 255, 255, 0))
    white.putalpha(alpha)
    white.save(png, format="PNG")


def _fix_white_icons(plugin: Path, manifest: dict):
    fixes = []
    for ref in _in_app_icon_refs(manifest):
        for png in _pngs_for(plugin, ref):
            if png.exists() and _needs_whitening(png):
                _whiten(png)
                fixes.append(("whiten-icon",
                              f"{png.relative_to(plugin).as_posix()} → #FFFFFF glyph"))
    return fixes


def _fix_missing_retina(plugin: Path, manifest: dict):
    """Generate any missing @2x from its @1x (2× nearest upscale)."""
    fixes = []
    refs = set()
    for f in ("Icon", "CategoryIcon"):
        if manifest.get(f):
            refs.add(manifest[f])
    for a in (manifest.get("Actions") or []):
        if a.get("Icon"):
            refs.add(a["Icon"])
        for st in (a.get("States") or []):
            if st.get("Image"):
                refs.add(st["Image"])
    for ref in sorted(refs):
        one, two = _pngs_for(plugin, ref)
        if one.exists() and not two.exists():
            with Image.open(one) as im:
                im = im.convert("RGBA")
                im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(two)
            fixes.append(("gen-retina",
                          f"{two.relative_to(plugin).as_posix()} (2× from @1x)"))
    return fixes


def autofix(plugin_dir):
    """Apply every safe auto-fix to a `<UUID>.sdPlugin` directory; return records."""
    plugin = Path(plugin_dir)
    mpath = plugin / spec.MANIFEST
    if not mpath.exists():
        return []
    try:
        manifest = json.loads(mpath.read_text())
    except json.JSONDecodeError:
        return []
    fixes = []
    fixes += _fix_white_icons(plugin, manifest)
    fixes += _fix_missing_retina(plugin, manifest)
    return fixes
