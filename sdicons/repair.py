"""Repair an Icon Pack Man export whose icons.json lost its names & tags.

Why this exists (learned the hard way, 2026-07-12): Elgato's Icon Pack Man
web packager IGNORES the `name` and `tags` in a dragged-in `icons.json` —
on import every icon's name becomes its filename (e.g. "trombone.png") and
tags come out empty, and it stamps `"License": "MIT"` into the manifest by
default. It DOES, however, emit the correct container:

    <id>.streamDeckIconPack (zip)
    └── <id>.sdIconPack/ { manifest.json, icons.json, icon.svg, license.txt,
                           icons/, previews/ }

So the reliable flow is: package/export via Icon Pack Man, then run this to
re-inject the real names + tags (matched by icon filename stem) from your
`tags.json`, and optionally fix the manifest License/URL. The container is
preserved byte-for-structure.

NB: `sdicons package` now emits this same container directly, so for packs
built with this toolkit you usually don't need Icon Pack Man at all. This
command is for fixing exports made through the web tool.
"""
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from .util import ok, warn, err


def _find(root: Path, name: str):
    hits = list(root.rglob(name))
    return hits[0] if hits else None


def repair_export(export_path, tags_path, license=None, url=None, out=None):
    export = Path(export_path)
    if not export.exists():
        raise SystemExit(err(f"export not found: {export}"))
    tags = json.loads(Path(tags_path).read_text())
    out_path = Path(out) if out else export

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(export) as z:
            z.extractall(tmp)

        ij = _find(tmp, "icons.json")
        if not ij:
            raise SystemExit(err("no icons.json inside the export"))
        entries = json.loads(ij.read_text())
        fixed, missing = 0, []
        for e in entries:
            stem = os.path.splitext(e.get("path", ""))[0]
            t = tags.get(stem)
            if t:
                e["name"] = t.get("name", e.get("name"))
                e["tags"] = t.get("tags", e.get("tags", []))
                fixed += 1
            else:
                missing.append(stem)
        ij.write_text(json.dumps(entries, indent=4, ensure_ascii=False))
        print(ok(f"  icons.json: {fixed}/{len(entries)} names+tags injected"))
        if missing:
            print(warn(f"  unmapped (left as-is): {', '.join(missing)}"))

        if license or url:
            mf = _find(tmp, "manifest.json")
            if mf:
                m = json.loads(mf.read_text())
                if license:
                    m["License"] = license
                if url:
                    m["URL"] = url
                mf.write_text(json.dumps(m, indent=4, ensure_ascii=False))
                print(ok(f"  manifest: "
                         + ", ".join(filter(None, [
                             f"License={license}" if license else None,
                             f"URL={url}" if url else None]))))

        # Re-zip, preserving the top-level <id>.sdIconPack/ wrapper folder.
        wrapper = next((p for p in tmp.iterdir() if p.is_dir()), None)
        if not wrapper:
            raise SystemExit(err("export had no wrapper folder — unexpected shape"))
        tmp_out = tmp / "repacked.zip"
        with zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(wrapper.rglob("*")):
                if f.is_file() and not f.name.startswith("."):
                    z.write(f, f.relative_to(tmp).as_posix())
        shutil.move(str(tmp_out), str(out_path))

    print(ok(f"repaired → {out_path}"))
    return out_path
