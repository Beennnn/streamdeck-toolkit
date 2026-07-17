"""Companion static posters for animated icons — the fix for the #1 reason an
animated icon pack gets rejected ("the preview images of the GIFs aren't
loading").

The Stream Deck Icon Library shows a STATIC image in each grid cell and only
plays the animation on hover. iconpackman guarantees that static image by
writing, for every `icons/<base>.gif` (or `.webp`), a sibling `icons/<base>.png`
built from the animation's FIRST frame. See spec.POSTER_EXT for the full
provenance (verified against iconpackman's exported packs).

This module is the toolkit's equivalent: `poster_for` names the companion,
`missing_posters` audits a pack, and `ensure_posters` generates any that are
missing (first frame, composited to RGBA so disposal/transparency is resolved,
forced to the 144×144 canvas). `package` calls `ensure_posters` before zipping
so every shipped pack is Icon-Library-correct even when built by hand.
"""
from pathlib import Path

from PIL import Image

from . import spec
from .util import ok, dim


def is_animated_name(name: str) -> bool:
    """True if `name`'s extension is an animated icon format (.gif/.webp)."""
    return Path(name).suffix.lower() in spec.ANIMATED_FORMATS


def poster_for(icon_path) -> Path:
    """Companion poster path for an animated icon: `<base>.gif` -> `<base>.png`.

    Same directory, same stem, `.png` extension (spec.POSTER_EXT). This is the
    exact same-base-name convention the Icon Library resolves posters by.
    """
    p = Path(icon_path)
    return p.with_suffix(spec.POSTER_EXT)


def is_poster_of_animated(name: str, present: set) -> bool:
    """True if `name` is the companion poster of an animated icon in `present`.

    `present` is the set of basenames in icons/. A `foo.png` is a poster when
    some `foo.gif`/`foo.webp` also exists — such a PNG is legitimately NOT
    listed in icons.json (iconpackman doesn't list posters either), so pack
    checks must not flag it as an orphan.
    """
    stem = Path(name).stem
    if Path(name).suffix.lower() != spec.POSTER_EXT:
        return False
    return any(f"{stem}{ext}" in present for ext in spec.ANIMATED_FORMATS)


def _first_frame(src: Path, size=spec.ICON_SIZE) -> Image.Image:
    """First frame of an animated icon, composited to RGBA at size×size.

    `convert("RGBA")` on the default (0th) frame resolves the frame's own
    disposal/transparency; resizing guards a source that isn't already square.
    """
    with Image.open(src) as im:
        im.seek(0)
        frame = im.convert("RGBA")
    if frame.size != (size, size):
        frame = frame.resize((size, size), Image.NEAREST)
    return frame


def generate_poster(icon_path, size=spec.ICON_SIZE) -> Path:
    """Write the companion poster PNG for one animated icon; return its path."""
    src = Path(icon_path)
    dst = poster_for(src)
    _first_frame(src, size).save(dst, format="PNG")
    return dst


def missing_posters(icons_dir) -> list:
    """Animated icons in `icons_dir` that lack their companion poster PNG.

    Returns a sorted list of the animated icons' basenames (e.g.
    `accordion-playing.gif`). Empty list == every animation has a poster.
    """
    d = Path(icons_dir)
    if not d.is_dir():
        return []
    present = {f.name for f in d.iterdir() if f.is_file()}
    missing = []
    for name in present:
        if is_animated_name(name) and poster_for(name).name not in present:
            missing.append(name)
    return sorted(missing)


def ensure_posters(icons_dir, size=spec.ICON_SIZE, verbose=False) -> list:
    """Generate every missing companion poster in `icons_dir`.

    Idempotent: only creates posters that don't already exist (so a hand-drawn
    poster is never overwritten). Returns the list of poster paths created.
    """
    d = Path(icons_dir)
    created = []
    for name in missing_posters(d):
        dst = generate_poster(d / name, size)
        created.append(dst)
        if verbose:
            print(ok(f"  poster {dst.name}  ← {name} (frame 0)"))
    if verbose and not created:
        print(dim("  posters: all animated icons already have one"))
    return created
