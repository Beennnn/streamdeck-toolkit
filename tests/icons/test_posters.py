"""Posters: naming convention, detection, generation, idempotence."""
from pathlib import Path

from PIL import Image

from sdicons import spec
from sdicons.posters import (
    poster_for, is_animated_name, is_poster_of_animated,
    missing_posters, ensure_posters, generate_poster,
)


def test_poster_for_maps_gif_to_png():
    assert poster_for("icons/accordion-playing.gif").name == "accordion-playing.png"
    assert poster_for("x/foo.webp").name == "foo.png"


def test_is_animated_name():
    assert is_animated_name("a.gif")
    assert is_animated_name("a.WEBP")
    assert not is_animated_name("a.png")
    assert not is_animated_name("a.svg")


def test_is_poster_of_animated_only_when_sibling_exists():
    present = {"foo.gif", "foo.png", "bar.png"}
    assert is_poster_of_animated("foo.png", present)      # sibling foo.gif → poster
    assert not is_poster_of_animated("bar.png", present)  # no bar.gif → real icon
    assert not is_poster_of_animated("foo.gif", present)  # a gif is not a poster


def test_missing_posters_lists_only_uncovered(pack_factory):
    pack = pack_factory(with_posters=False)
    missing = missing_posters(pack / spec.DIR_ICONS)
    assert missing == ["accordion-playing.gif"]


def test_missing_posters_empty_when_covered(pack_factory):
    pack = pack_factory(with_posters=True)
    assert missing_posters(pack / spec.DIR_ICONS) == []


def test_ensure_posters_generates_144_png(pack_factory):
    pack = pack_factory(with_posters=False)
    made = ensure_posters(pack / spec.DIR_ICONS)
    assert len(made) == 1
    poster = pack / spec.DIR_ICONS / "accordion-playing.png"
    assert poster.exists()
    with Image.open(poster) as im:
        assert im.format == "PNG"
        assert im.size == (spec.ICON_SIZE, spec.ICON_SIZE)


def test_ensure_posters_idempotent(pack_factory):
    pack = pack_factory(with_posters=False)
    assert len(ensure_posters(pack / spec.DIR_ICONS)) == 1
    assert ensure_posters(pack / spec.DIR_ICONS) == []  # second run creates nothing


def test_ensure_posters_does_not_overwrite_handmade(pack_factory):
    pack = pack_factory(with_posters=False)
    poster = pack / spec.DIR_ICONS / "accordion-playing.png"
    # a hand-made poster of a distinct colour
    Image.new("RGBA", (spec.ICON_SIZE, spec.ICON_SIZE), (1, 2, 3, 255)).save(poster)
    before = poster.read_bytes()
    ensure_posters(pack / spec.DIR_ICONS)
    assert poster.read_bytes() == before  # untouched


def test_generate_poster_from_non_square_source(tmp_path):
    src = tmp_path / "wide.gif"
    imgs = [Image.new("RGBA", (72, 72), (i, 0, 0, 255)) for i in range(3)]
    imgs[0].save(src, save_all=True, append_images=imgs[1:], duration=100, loop=0)
    dst = generate_poster(src)
    with Image.open(dst) as im:
        assert im.size == (spec.ICON_SIZE, spec.ICON_SIZE)


def test_missing_posters_handles_missing_dir(tmp_path):
    assert missing_posters(tmp_path / "nope") == []
