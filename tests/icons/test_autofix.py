"""Auto-fix: regenerate posters + split comma-tags, safely and idempotently."""
import json

from PIL import Image

from sdicons import spec
from sdicons.autofix import autofix
from sdicons.verify import verify, has_blocking, counts, ERROR


def _codes(fixes):
    return [c for c, _ in fixes]


def test_autofix_generates_missing_posters(pack_factory):
    pack = pack_factory(with_posters=False)
    fixes = autofix(pack)
    assert "poster" in _codes(fixes)
    assert counts(verify(pack))[ERROR] == 0  # green after


def test_autofix_regenerates_wrong_size_poster(pack_factory):
    pack = pack_factory(with_posters=True)
    bad = pack / spec.DIR_ICONS / "accordion-playing.png"
    Image.new("RGBA", (60, 60)).save(bad)  # wrong size
    fixes = autofix(pack)
    assert any(c == "poster" for c, _ in fixes)
    with Image.open(bad) as im:
        assert im.size == (spec.ICON_SIZE, spec.ICON_SIZE)


def test_autofix_splits_comma_tags(pack_factory):
    pack = pack_factory(icons=[{"file": "a.png", "name": "A", "tags": ["x, y", "z"]}],
                        with_posters=False)
    fixes = autofix(pack)
    assert "tag" in _codes(fixes)
    tags = json.loads((pack / "icons.json").read_text())[0]["tags"]
    assert tags == ["x", "y", "z"]
    assert "bad-tag" not in {f.code for f in verify(pack)}


def test_autofix_idempotent(pack_factory):
    pack = pack_factory(with_posters=False)
    assert autofix(pack)          # first run fixes things
    assert autofix(pack) == []    # second run finds nothing


def test_autofix_full_pack_goes_green(pack_factory):
    pack = pack_factory(with_posters=False, previews=3)
    autofix(pack)
    assert not has_blocking(verify(pack))
