"""Assemble a validated pack into a submit-ready .streamDeckIconPack.

Container format (VERIFIED 2026-07-12 by exporting from Elgato's Icon Pack
Man and inspecting the bytes):

    <pack-id>.streamDeckIconPack          ← a ZIP file, this is what you ship
    └── <pack-id>.sdIconPack/             ← REQUIRED top-level wrapper folder
        ├── manifest.json
        ├── icons.json
        ├── icon.svg                      ← the pack thumbnail (manifest.Icon)
        ├── license.txt
        ├── icons/  (144×144 png/svg/…)
        └── previews/  (optional, up to 3 store-preview png/jpg)

`<pack-id>` is a reverse-domain identifier, e.g. `com.beennnn.stagekeys`
(Stream Deck derives the pack identity from this folder name). Our earlier
packager wrote files at the ZIP ROOT with no wrapper folder — that is NOT
the shape Icon Pack Man produces and likely won't install. This builds the
exact same container Icon Pack Man does, so Icon Pack Man is now OPTIONAL:
the output is ready to double-click-install AND to submit to Maker Console.

Packaging refuses to run if `validate` reports any error.
See docs/publishing.md for the full publishing process + Icon Pack Man quirks.
"""
import json
import re
import zipfile
from pathlib import Path

from . import spec
from .validate import validate
from .posters import ensure_posters
from .util import ok, warn, err, slug

# Files that belong in the shipped pack (everything else is dev cruft).
_INCLUDE = {spec.FILE_MANIFEST, spec.FILE_ICONS_JSON, spec.FILE_LICENSE}
_INCLUDE_PREFIX = (spec.DIR_ICONS + "/", spec.DIR_PREVIEWS + "/")


def derive_pack_id(manifest):
    """Reverse-domain id from manifest: com.<author>.<name> (lowercase alnum)."""
    if manifest.get("Id"):
        return manifest["Id"]
    def part(s):
        return re.sub(r"[^a-z0-9]", "", (s or "").lower()) or "pack"
    return f"com.{part(manifest.get('Author'))}.{part(manifest.get('Name'))}"


def package(pack_dir, out_dir="dist", pack_id=None):
    pack = Path(pack_dir)
    # Generate any missing animated-icon posters BEFORE validating/zipping, so
    # the shipped container always carries the `<base>.png` the Stream Deck Icon
    # Library needs (the iconpackman behaviour — see posters.py). Idempotent.
    made = ensure_posters(pack / spec.DIR_ICONS)
    if made:
        print(ok(f"  generated {len(made)} companion poster(s) for animated icons"))
    errors, _ = validate(pack)
    if errors:
        raise SystemExit(err(f"refusing to package: {len(errors)} validation "
                             f"error(s). Run `sdicons validate {pack}` first."))

    manifest = json.loads((pack / spec.FILE_MANIFEST).read_text())
    pid = pack_id or derive_pack_id(manifest)
    wrapper = f"{pid}{spec.SDICONPACK_SUFFIX}"      # <id>.sdIconPack
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    archive = out / f"{pid}{spec.PACK_EXT}"          # <id>.streamDeckIconPack

    icon_rel = manifest.get("Icon")
    wanted = set(_INCLUDE)
    if icon_rel:
        wanted.add(icon_rel)

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pack.rglob("*")):
            if f.is_dir() or f.name.startswith("."):
                continue
            rel = f.relative_to(pack).as_posix()
            if rel in wanted or rel.startswith(_INCLUDE_PREFIX):
                # Everything nests under the required <id>.sdIconPack/ wrapper.
                z.write(f, f"{wrapper}/{rel}")

    print(ok(f"built {archive}"))
    print(ok(f"  id: {pid} — submit-ready (double-click to install, "
             f"or upload to Maker Console)"))
    return archive
