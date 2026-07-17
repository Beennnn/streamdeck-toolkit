"""Fixtures: build a synthetic `<UUID>.sdPlugin` on disk from a compact spec so
every check runs against real files/PIL images, not mocks."""
import json
from pathlib import Path

import pytest
from PIL import Image


def _png(path, size, rgba):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (size, size), rgba).save(path, format="PNG")


WHITE = (255, 255, 255, 255)
RED = (220, 20, 20, 255)


def make_plugin(root, *, uuid="com.tester.demo", name="Demo Switcher",
                category="Demo", version="1.0.0.0", sdk=3, min_sw="6.9",
                description="A demo plugin for tests.",
                actions=None, white_icons=True, retina=True,
                codepath="bin/plugin.js", locale_extra=None,
                include_manifest=True):
    """Create `<uuid>.sdPlugin/` under root. Returns the plugin Path."""
    plug = Path(root) / f"{uuid}.sdPlugin"
    plug.mkdir(parents=True, exist_ok=True)
    (plug / codepath).parent.mkdir(parents=True, exist_ok=True)
    (plug / codepath).write_text("// stub")

    if actions is None:
        actions = [
            {"UUID": f"{uuid}.connect", "Name": "Connect", "Icon": "imgs/actions/connect/icon",
             "States": [{"Image": "imgs/actions/connect/key"}]},
            {"UUID": f"{uuid}.power", "Name": "Power", "Icon": "imgs/actions/power/icon",
             "States": [{"Image": "imgs/actions/power/key"}]},
        ]

    glyph = WHITE if white_icons else RED
    # in-app icons (must be white); key State images (colour fine)
    _png(plug / "imgs/plugin/icon.png", 28, glyph)
    _png(plug / "imgs/plugin/category.png", 28, glyph)
    if retina:
        _png(plug / "imgs/plugin/icon@2x.png", 56, glyph)
        _png(plug / "imgs/plugin/category@2x.png", 56, glyph)
    for a in actions:
        if a.get("Icon"):
            _png(plug / f"{a['Icon']}.png", 20, glyph)
            if retina:
                _png(plug / f"{a['Icon']}@2x.png", 40, glyph)
        for st in a.get("States", []):
            if st.get("Image"):
                _png(plug / f"{st['Image']}.png", 72, RED)  # key art, colour ok
                if retina:
                    _png(plug / f"{st['Image']}@2x.png", 144, RED)

    manifest = {
        "Name": name, "UUID": uuid, "Version": version, "Author": "Tester",
        "Icon": "imgs/plugin/icon", "CategoryIcon": "imgs/plugin/category",
        "Category": category, "Description": description,
        "CodePath": codepath, "SDKVersion": sdk,
        "Software": {"MinimumVersion": min_sw},
        "OS": [{"Platform": "mac", "MinimumVersion": "12"}],
        "Nodejs": {"Version": "20"},
        "Actions": actions,
    }
    if include_manifest:
        (plug / "manifest.json").write_text(json.dumps(manifest, indent=2))

    (plug / "ui").mkdir(exist_ok=True)
    (plug / "ui" / "connect.html").write_text("<html>Pick a network and connect.</html>")
    loc = {"Localization": {"Connect": "Connect", "Power": "Power"}}
    if locale_extra:
        loc["Localization"].update(locale_extra)
    (plug / "en.json").write_text(json.dumps(loc))
    return plug


@pytest.fixture
def plugin_factory(tmp_path):
    counter = {"n": 0}

    def _factory(**kw):
        counter["n"] += 1
        return make_plugin(tmp_path / f"p{counter['n']}", **kw)

    return _factory
