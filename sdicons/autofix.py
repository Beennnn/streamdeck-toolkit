"""Auto-repair the icon-pack defects we KNOW how to fix safely.

Distilled from real Maker Console rejections, this is the "fix it for me" half of
`verify`. It only applies changes that are unambiguous and reversible-by-rebuild —
never a guess that could ship wrong content:

  * missing / wrong-size / wrong-format / unreadable companion posters
    → (re)generate from the animation's first frame (the Icon Library preview).
  * a tag containing ", " (which iconpackman rejects) → split into separate tags.

Everything else `verify` flags (no Description, empty pack, off-size source icons,
low-fps animations…) needs a human decision and is left to the report. `autofix`
returns a list of `(code, detail)` applied-fix records so the CLI can show exactly
what it changed, then re-verify.
"""
import json
from pathlib import Path

from PIL import Image

from . import spec
from .posters import poster_for, is_animated_name, generate_poster


def _fix_posters(icons_dir: Path):
    """Ensure every animated icon has a valid 144×144 PNG poster; regenerate any
    that is missing, the wrong size/format, or unreadable."""
    fixes = []
    if not icons_dir.is_dir():
        return fixes
    present = {f.name for f in icons_dir.iterdir() if f.is_file()}
    for name in sorted(present):
        if not is_animated_name(name):
            continue
        poster = poster_for(icons_dir / name)
        need, why = False, ""
        if poster.name not in present:
            need, why = True, "missing"
        else:
            try:
                with Image.open(poster) as im:
                    if im.format != "PNG":
                        need, why = True, f"format {im.format}"
                    elif im.size != (spec.ICON_SIZE, spec.ICON_SIZE):
                        need, why = True, f"{im.size[0]}x{im.size[1]}"
            except Exception:
                need, why = True, "unreadable"
        if need:
            generate_poster(icons_dir / name)
            fixes.append(("poster", f"{poster.name} ({why} → regenerated from frame 0)"))
    return fixes


def _fix_comma_tags(pack: Path):
    """Split any icons.json tag containing ', ' (iconpackman rejects it)."""
    fixes = []
    ij = pack / spec.FILE_ICONS_JSON
    if not ij.exists():
        return fixes
    try:
        entries = json.loads(ij.read_text())
    except json.JSONDecodeError:
        return fixes
    if not isinstance(entries, list):
        return fixes
    changed = False
    for e in entries:
        tags = e.get("tags")
        if not isinstance(tags, list):
            continue
        new = []
        for t in tags:
            if isinstance(t, str) and ", " in t:
                parts = [p.strip() for p in t.split(",") if p.strip()]
                new.extend(parts)
                fixes.append(("tag", f"{e.get('name', e.get('path'))!r}: "
                                     f"{t!r} → {parts}"))
                changed = True
            else:
                new.append(t)
        e["tags"] = new
    if changed:
        ij.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
    return fixes


def autofix(pack_dir):
    """Apply every safe auto-fix to a pack directory; return the fix records."""
    pack = Path(pack_dir)
    fixes = []
    fixes += _fix_posters(pack / spec.DIR_ICONS)
    fixes += _fix_comma_tags(pack)
    return fixes
