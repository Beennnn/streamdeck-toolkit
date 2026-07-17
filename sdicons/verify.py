"""Pre-publication verifier for Elgato icon packs — the "will Maker Console
accept this?" gate, run before every submission.

`validate` answers "is this a structurally valid pack?" (missing files, wrong
sizes, broken icons.json). `verify` is the stricter, publication-facing layer:
it runs everything validate does AND the checks that catch real-world Maker
Console rejections — headlined by the animated-icon **companion poster** rule
that got "Music Instruments for Stage Keys" 1.2 rejected on 2026-07-17
("the preview images of the GIFs aren't loading"; see spec.POSTER_EXT and
posters.py for the provenance).

Design:
  * Every check appends `Finding(level, code, message)` — no bare strings, so
    callers can group/filter by severity and code.
  * `verify(pack_dir)` checks a pack DIRECTORY (the working tree you build).
  * `verify_container(archive)` unzips a shipped `.streamDeckIconPack` and
    verifies THAT — the actual bytes you'd upload, catching a stale dist/.
  * Levels: ERROR blocks publication; WARN is store-quality guidance; INFO is
    context. `--strict` promotes WARN to blocking.
Exit policy lives in the CLI (`sdicons verify`): non-zero on any ERROR (or any
WARN under --strict).
"""
import json
import re
from pathlib import Path

from PIL import Image

from . import spec
from .validate import validate
from .posters import poster_for, is_animated_name, is_poster_of_animated
from sdcommon.findings import (Finding, ERROR, WARN, INFO,
                               counts, has_blocking, print_report)
from sdcommon.container import verify_container as _verify_container


def _load_icons_json(pack: Path):
    """Parse icons.json; return (entries_list, error_or_None)."""
    ij = pack / spec.FILE_ICONS_JSON
    if not ij.exists():
        return [], f"missing {spec.FILE_ICONS_JSON}"
    try:
        data = json.loads(ij.read_text())
    except json.JSONDecodeError as e:
        return [], f"{spec.FILE_ICONS_JSON} is not valid JSON: {e}"
    if not isinstance(data, list):
        return [], f"{spec.FILE_ICONS_JSON} must be a JSON array"
    return data, None


# ── individual checks — each takes (pack, ctx) and returns list[Finding] ──────

def check_structural(pack, ctx):
    """Fold the base validator in so `verify` is a strict superset of it."""
    out = []
    errors, warnings = validate(pack)
    for e in errors:
        out.append(Finding(ERROR, "structural", e))
    for w in warnings:
        # The base validator warns on any icons/ file absent from icons.json.
        # A companion poster is *supposed* to be absent from icons.json, so
        # suppress that specific warning here — check_posters owns posters.
        if "not listed in icons.json" in w:
            fname = w.split("icons/", 1)[1].split(":", 1)[0] if "icons/" in w else ""
            if fname and is_poster_of_animated(fname, ctx["present"]):
                continue
        out.append(Finding(WARN, "structural", w))
    return out


def check_posters(pack, ctx):
    """THE headline rejection cause: every animated icon needs a companion
    poster PNG the Icon Library can render, and it must be a 144×144 PNG."""
    out = []
    present = ctx["present"]
    icons_dir = pack / spec.DIR_ICONS
    for name in sorted(present):
        if not is_animated_name(name):
            continue
        poster = poster_for(name).name
        if poster not in present:
            out.append(Finding(
                ERROR, "missing-poster",
                f"icons/{name}: no companion poster 'icons/{poster}' — the "
                f"Stream Deck Icon Library shows a broken tile (Elgato's "
                f"\"GIF previews aren't loading\" rejection). Run "
                f"`sdicons verify {pack} --fix` or `sdicons posters {pack}`."))
            continue
        # Poster exists — make sure it's a real 144×144 PNG, not a stray file.
        pp = icons_dir / poster
        try:
            with Image.open(pp) as im:
                fmt, sz = im.format, im.size
            if fmt != "PNG":
                out.append(Finding(ERROR, "poster-format",
                                   f"icons/{poster}: poster must be PNG (is {fmt})"))
            if sz != (spec.ICON_SIZE, spec.ICON_SIZE):
                out.append(Finding(ERROR, "poster-size",
                                   f"icons/{poster}: {sz[0]}x{sz[1]}, poster must "
                                   f"be {spec.ICON_SIZE}x{spec.ICON_SIZE}"))
        except Exception as e:
            out.append(Finding(ERROR, "poster-unreadable",
                               f"icons/{poster}: cannot read poster ({e})"))
    return out


def check_manifest_store(pack, ctx):
    """Store-listing quality: a pack with no Description/URL/Licence lists poorly
    on the Marketplace even though it installs fine."""
    out = []
    m = ctx["manifest"]
    if not m:
        return out
    desc = (m.get("Description") or "").strip()
    if not desc:
        out.append(Finding(WARN, "no-description",
                           "manifest: no Description — the store listing will be bare"))
    elif len(desc) < 30:
        out.append(Finding(WARN, "thin-description",
                           f"manifest: Description is only {len(desc)} chars — "
                           f"thin for a store listing"))
    if not (m.get("URL") or "").strip():
        out.append(Finding(WARN, "no-url",
                           "manifest: no URL — no 'project page' link on the listing"))
    if not (m.get("Licence") or m.get("License")):
        out.append(Finding(WARN, "no-licence",
                           "manifest: no Licence field — buyers can't see usage terms"))
    return out


def check_tags(pack, ctx):
    """Tag hygiene. iconpackman itself rejects a tag containing ", " (its export
    splits/compares tags on that), and empty tags hurt Marketplace search."""
    out = []
    for i, e in enumerate(ctx["entries"]):
        tags = e.get("tags")
        label = e.get("name") or e.get("path") or f"[{i}]"
        if tags == []:
            out.append(Finding(WARN, "no-tags",
                               f"icons.json '{label}': no tags (hurts search)"))
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str) and ", " in t:
                    out.append(Finding(ERROR, "bad-tag",
                                       f"icons.json '{label}': tag {t!r} contains "
                                       f"', ' — iconpackman rejects this"))
    return out


def check_duplicates(pack, ctx):
    """Duplicate paths break the pack; duplicate display names confuse the grid."""
    out = []
    paths, names = {}, {}
    for i, e in enumerate(ctx["entries"]):
        p = e.get("path")
        n = e.get("name")
        if p:
            if p in paths:
                out.append(Finding(ERROR, "dup-path",
                                   f"icons.json: path {p!r} listed twice "
                                   f"(entries {paths[p]} and {i})"))
            paths[p] = i
        if n:
            names.setdefault(n, []).append(i)
    for n, idxs in names.items():
        if len(idxs) > 1:
            out.append(Finding(WARN, "dup-name",
                               f"icons.json: display name {n!r} used {len(idxs)}× "
                               f"(entries {idxs})"))
    return out


def check_filenames(pack, ctx):
    """Filename hygiene beyond the hard 80-char limit validate enforces:
    spaces and uppercase are portability hazards (iconpackman lowercases
    extensions; the Library keys on exact names)."""
    out = []
    for name in sorted(ctx["present"]):
        stem_ext = name
        if " " in stem_ext:
            out.append(Finding(WARN, "filename-space",
                               f"icons/{name}: contains a space — prefer hyphens"))
        if stem_ext != stem_ext.lower():
            out.append(Finding(WARN, "filename-case",
                               f"icons/{name}: has uppercase — prefer all-lowercase"))
        if not re.match(r"^[\w.\-]+$", stem_ext):
            out.append(Finding(WARN, "filename-charset",
                               f"icons/{name}: non-[a-z0-9._-] characters"))
    return out


def check_previews(pack, ctx):
    """previews/ is optional but capped at 3 store-preview images (png/jpg)."""
    out = []
    pv = pack / spec.DIR_PREVIEWS
    if not pv.is_dir():
        out.append(Finding(INFO, "no-previews",
                           "no previews/ folder (optional store-preview images)"))
        return out
    imgs = [f for f in sorted(pv.iterdir())
            if f.is_file() and not f.name.startswith(".")]
    ok_ext = {".png", ".jpg", ".jpeg"}
    for f in imgs:
        if f.suffix.lower() not in ok_ext:
            out.append(Finding(WARN, "preview-format",
                               f"previews/{f.name}: not a png/jpg store preview"))
    if len(imgs) > 3:
        out.append(Finding(WARN, "too-many-previews",
                           f"previews/: {len(imgs)} images, Elgato shows up to 3"))
    return out


def check_empty(pack, ctx):
    """A pack with zero listed icons is nothing to publish."""
    if not ctx["entries"]:
        return [Finding(ERROR, "empty-pack", "icons.json lists no icons")]
    return []


_CHECKS = (
    check_structural,
    check_posters,
    check_manifest_store,
    check_tags,
    check_duplicates,
    check_filenames,
    check_previews,
    check_empty,
)


def verify(pack_dir) -> list:
    """Run every check on a pack DIRECTORY; return a flat list[Finding]."""
    pack = Path(pack_dir)
    icons_dir = pack / spec.DIR_ICONS
    present = ({f.name for f in icons_dir.iterdir() if f.is_file()}
               if icons_dir.is_dir() else set())
    manifest = {}
    mpath = pack / spec.FILE_MANIFEST
    if mpath.exists():
        try:
            manifest = json.loads(mpath.read_text())
        except json.JSONDecodeError:
            manifest = {}
    entries, _ = _load_icons_json(pack)
    ctx = {"present": present, "manifest": manifest, "entries": entries}
    findings = []
    for chk in _CHECKS:
        findings.extend(chk(pack, ctx))
    return findings


def verify_container(archive) -> list:
    """Unzip a shipped `.streamDeckIconPack` and verify the real bytes inside.

    Run this on `dist/*.streamDeckIconPack` right before uploading — it catches a
    container built before a fix (e.g. a dist/ zipped without the companion
    posters) that a directory check would miss. Delegates the zip mechanics to
    the shared `sdcommon.container` helper.
    """
    return _verify_container(archive, spec.SDICONPACK_SUFFIX, verify)


# `counts`, `has_blocking`, `print_report` are imported from sdcommon.findings and
# re-exported here so `from .verify import print_report` keeps working.
