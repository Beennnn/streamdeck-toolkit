"""Generate icons.json from the icons/ folder, merging optional metadata.

Display names are derived from filenames (kebab -> Title Case) unless a
sidecar `tags.json` in the pack root overrides name/tags per icon:

    { "power-on": { "name": "Power On", "tags": ["control", "power"] } }

Regenerating is idempotent: existing icons.json entries are preserved as
the metadata source too, so hand-tuned names/tags survive a re-run.
"""
import json
from pathlib import Path

from . import spec
from .util import ok


def _title(stem):
    return " ".join(w.capitalize() for w in stem.replace("_", "-").split("-") if w)


def _load_overrides(pack: Path):
    """Merge tags.json sidecar + existing icons.json into a {stem: entry} map."""
    overrides = {}
    sidecar = pack / "tags.json"
    if sidecar.exists():
        overrides.update(json.loads(sidecar.read_text()))
    existing = pack / spec.FILE_ICONS_JSON
    if existing.exists():
        try:
            for e in json.loads(existing.read_text()):
                stem = Path(e["path"]).stem
                overrides.setdefault(stem, {})
                overrides[stem].setdefault("name", e.get("name"))
                overrides[stem].setdefault("tags", e.get("tags"))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return overrides


def build_icons_json(pack_dir):
    pack = Path(pack_dir)
    icons_dir = pack / spec.DIR_ICONS
    overrides = _load_overrides(pack)

    entries = []
    for f in sorted(icons_dir.iterdir()):
        if f.suffix.lower() not in spec.ICON_FORMATS or f.name.startswith("."):
            continue
        ov = overrides.get(f.stem, {})
        entries.append({
            "path": f.name,  # relative to icons/
            "name": ov.get("name") or _title(f.stem),
            "tags": ov.get("tags") or [],
        })

    (pack / spec.FILE_ICONS_JSON).write_text(
        json.dumps(entries, indent=4, ensure_ascii=False) + "\n")
    print(ok(f"wrote {spec.FILE_ICONS_JSON} — {len(entries)} icons"))
    return entries
