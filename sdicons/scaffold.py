"""Create a new, spec-shaped icon-pack skeleton ready to fill with icons."""
import json
from pathlib import Path

from . import spec
from .util import ok

_TEMPLATE_MANIFEST = {
    "Name": "My Icon Pack",
    "Author": "Your Name",
    "Version": "1.0.0",
    "Description": "Describe your icon pack here.",
    "Icon": "icon.svg",
    "URL": "https://example.com",
    "Licence": spec.FILE_LICENSE,
}

# A neutral 56x56 placeholder thumbnail so the pack is valid from minute one.
_TEMPLATE_THUMB = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="56" height="56" '
    'viewBox="0 0 56 56"><rect width="56" height="56" rx="10" fill="#2b2b2b"/>'
    '<circle cx="28" cy="28" r="14" fill="none" stroke="#fff" stroke-width="3"/>'
    '</svg>\n'
)


def new_pack(pack_dir, name=None, author=None):
    pack = Path(pack_dir)
    if pack.exists() and any(pack.iterdir()):
        raise SystemExit(f"refusing to scaffold into non-empty dir: {pack}")
    (pack / spec.DIR_ICONS).mkdir(parents=True, exist_ok=True)

    manifest = dict(_TEMPLATE_MANIFEST)
    if name:
        manifest["Name"] = name
    if author:
        manifest["Author"] = author

    (pack / spec.FILE_MANIFEST).write_text(
        json.dumps(manifest, indent=4, ensure_ascii=False) + "\n")
    (pack / spec.FILE_ICONS_JSON).write_text("[]\n")
    (pack / "icon.svg").write_text(_TEMPLATE_THUMB)
    (pack / spec.FILE_LICENSE).write_text(
        "Copyright (c) YEAR Your Name. All rights reserved.\n")

    print(ok(f"scaffolded pack at {pack}"))
    print(f"  next: drop SVGs in a source dir, then `sdicons build <src> {pack}`")
    return pack


def ensure_skeleton(pack_dir, name=None, author=None):
    """Create any missing pack scaffolding WITHOUT clobbering existing files.

    Used by `build` so a first run on a bare directory yields a valid pack
    instead of failing validation on a missing manifest. Hand-authored
    manifest.json / tags.json / icon.svg / license.txt are always kept.
    """
    pack = Path(pack_dir)
    (pack / spec.DIR_ICONS).mkdir(parents=True, exist_ok=True)

    mpath = pack / spec.FILE_MANIFEST
    if not mpath.exists():
        manifest = dict(_TEMPLATE_MANIFEST)
        if name:
            manifest["Name"] = name
        if author:
            manifest["Author"] = author
        mpath.write_text(json.dumps(manifest, indent=4, ensure_ascii=False) + "\n")
        print(ok(f"  created {spec.FILE_MANIFEST} (edit its Name/Author/URL)"))
    if not (pack / "icon.svg").exists():
        (pack / "icon.svg").write_text(_TEMPLATE_THUMB)
    if not (pack / spec.FILE_LICENSE).exists():
        (pack / spec.FILE_LICENSE).write_text(
            "Copyright (c) YEAR Your Name. All rights reserved.\n")
    return pack
