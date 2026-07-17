"""Test fixtures: build synthetic icon packs on disk from a compact spec.

`make_pack(tmp_path, ...)` writes a minimal-but-real pack (manifest.json,
icons.json, icons/) so every check runs against actual files and PIL images,
not mocks. Helpers create true 144×144 PNGs and multi-frame GIFs so size/format
checks are exercised for real.
"""
import json
from pathlib import Path

import pytest
from PIL import Image

from sdicons import spec

SIZE = spec.ICON_SIZE


def _png(path, size=SIZE, color=(200, 40, 40, 255)):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (size, size), color).save(path, format="PNG")


def _gif(path, frames=15, size=SIZE, duration=80):
    """A real animated GIF (frames×duration → fps ≈ 1000/duration)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    imgs = [Image.new("RGBA", (size, size), (20 * i % 255, 80, 160, 255))
            for i in range(frames)]
    imgs[0].save(path, save_all=True, append_images=imgs[1:],
                 duration=duration, loop=0, format="GIF")


def make_pack(root, *, name="Test Pack", author="Tester", version="1.0.0",
              description="A test pack with plenty of description text here.",
              url="https://example.com", licence="license.txt",
              icons=None, with_posters=True, previews=0,
              icon_file="icon.png"):
    """Create a pack directory under `root`. `icons` is a list of dicts:
      {"file": "accordion.png"|"accordion-playing.gif", "name":..., "tags":[...]}
    Static .png and animated .gif files are created to match. Companion posters
    for animated icons are created iff `with_posters`.
    Returns the pack Path.
    """
    pack = Path(root)
    (pack / spec.DIR_ICONS).mkdir(parents=True, exist_ok=True)
    if icons is None:
        icons = [
            {"file": "accordion.png", "name": "Accordion", "tags": ["reed"]},
            {"file": "accordion-playing.gif", "name": "Accordion (playing)",
             "tags": ["reed", "animated"]},
        ]
    entries = []
    for it in icons:
        f = it["file"]
        dst = pack / spec.DIR_ICONS / f
        if f.lower().endswith(".gif"):
            _gif(dst, frames=it.get("frames", 15), duration=it.get("duration", 80))
            if with_posters:
                _png(dst.with_suffix(".png"))
        else:
            _png(dst)
        entries.append({"path": f, "name": it["name"], "tags": it["tags"]})

    manifest = {"Name": name, "Author": author, "Version": version, "Icon": icon_file}
    if description is not None:
        manifest["Description"] = description
    if url is not None:
        manifest["URL"] = url
    if licence is not None:
        manifest["Licence"] = licence
    (pack / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (pack / "icons.json").write_text(json.dumps(entries, indent=2))
    if licence:
        (pack / licence).write_text("MIT — test license\n")
    if icon_file:
        _png(pack / icon_file, size=spec.THUMBNAIL_SIZE)
    if previews:
        pv = pack / spec.DIR_PREVIEWS
        for i in range(previews):
            _png(pv / f"{i:02d}.png", size=SIZE)
    return pack


@pytest.fixture
def pack_factory(tmp_path):
    """Return a factory that builds packs in unique subdirs of tmp_path."""
    counter = {"n": 0}

    def _factory(**kw):
        counter["n"] += 1
        return make_pack(tmp_path / f"pack{counter['n']}", **kw)

    return _factory
