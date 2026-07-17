"""Auto-fix: whiten in-app icons + generate missing @2x, without touching key
art or trying to guess foreign-reference edits."""
from PIL import Image

from sdplugin.autofix import autofix
from sdplugin.verify import verify, counts, ERROR


def _codes(fixes):
    return [c for c, _ in fixes]


def _pixel(png):
    with Image.open(png) as im:
        return im.convert("RGBA").getpixel((im.width // 2, im.height // 2))


def test_autofix_whitens_coloured_in_app_icons(plugin_factory):
    plug = plugin_factory(white_icons=False)
    assert "non-white-icon" in {f.code for f in verify(plug)}
    fixes = autofix(plug)
    assert "whiten-icon" in _codes(fixes)
    assert "non-white-icon" not in {f.code for f in verify(plug)}  # green after


def test_autofix_preserves_key_state_art(plugin_factory):
    """States[].Image key faces are colour art — must NOT be whitened."""
    plug = plugin_factory(white_icons=False)
    autofix(plug)
    key = plug / "imgs/actions/connect/key@2x.png"
    r, g, b, a = _pixel(key)
    assert (r, g, b) != (255, 255, 255)  # still the red key art


def test_autofix_generates_missing_retina(plugin_factory):
    plug = plugin_factory(retina=False)
    fixes = autofix(plug)
    assert "gen-retina" in _codes(fixes)
    assert (plug / "imgs/plugin/icon@2x.png").exists()


def test_autofix_does_not_touch_foreign_references(plugin_factory):
    plug = plugin_factory(locale_extra={"x": "Connect your Bluetooth speaker"})
    autofix(plug)
    # foreign references need a human — still flagged after auto-fix
    assert "foreign-reference" in {f.code for f in verify(plug)}


def test_autofix_idempotent(plugin_factory):
    plug = plugin_factory(white_icons=False, retina=False)
    assert autofix(plug)
    assert autofix(plug) == []


def test_autofix_missing_manifest_noop(tmp_path):
    plug = tmp_path / "com.x.y.sdPlugin"
    plug.mkdir()
    assert autofix(plug) == []
