"""Lint an icon pack against the Elgato spec — the get-it-accepted tool.

Errors block packaging (would be rejected by Maker Console review or fail
to install). Warnings are guidance (animated-icon budgets, empty tags).
Returns (errors, warnings) as lists of strings; CLI exits non-zero on any
error.
"""
import json
import re
from pathlib import Path

from PIL import Image

from . import spec
from .util import ok, warn, err

RASTER = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _anim_warnings(name, path):
    """Soft fps/duration checks for an animated icon (Elgato guidance only)."""
    out = []
    try:
        with Image.open(path) as im:
            frames = getattr(im, "n_frames", 1)
            if frames <= 1:
                return out  # static file in an animated container — fine
            total_ms = 0
            for i in range(frames):
                im.seek(i)
                total_ms += im.info.get("duration", 0) or 0
    except Exception:
        return out
    if total_ms <= 0:
        return out
    secs = total_ms / 1000
    fps = frames / secs
    lo, hi = spec.ANIM_FPS_RANGE
    if fps < lo or fps > hi:
        out.append(f"icons/{name}: ~{fps:.0f} fps (Elgato suggests {lo}-{hi})")
    if secs > spec.ANIM_MAX_SECONDS:
        out.append(f"icons/{name}: {secs:.1f}s loop (Elgato suggests "
                   f"≤ {spec.ANIM_MAX_SECONDS}s)")
    return out


def validate(pack_dir):
    pack = Path(pack_dir)
    errors, warnings = [], []

    def E(m): errors.append(m)
    def W(m): warnings.append(m)

    # --- manifest.json ---
    mpath = pack / spec.FILE_MANIFEST
    manifest = {}
    if not mpath.exists():
        E(f"missing {spec.FILE_MANIFEST}")
    else:
        try:
            manifest = json.loads(mpath.read_text())
        except json.JSONDecodeError as e:
            E(f"{spec.FILE_MANIFEST} is not valid JSON: {e}")
        for field in spec.MANIFEST_REQUIRED:
            if not manifest.get(field):
                E(f"manifest: missing required field '{field}'")
        ver = manifest.get("Version", "")
        if ver and not re.match(spec.VERSION_RE, str(ver)):
            E(f"manifest: Version '{ver}' must be three numbers, e.g. 1.0.2")
        icon_rel = manifest.get("Icon")
        if icon_rel and not (pack / icon_rel).exists():
            E(f"manifest: Icon '{icon_rel}' does not exist in pack")
        lic = manifest.get("Licence") or manifest.get("License")
        if lic and not (pack / lic).exists():
            W(f"manifest: Licence '{lic}' referenced but file missing")

    # --- icons folder + files ---
    icons_dir = pack / spec.DIR_ICONS
    on_disk = {}
    if not icons_dir.is_dir():
        E(f"missing {spec.DIR_ICONS}/ folder")
    else:
        for f in sorted(icons_dir.iterdir()):
            if f.name.startswith(".") or f.is_dir():
                continue
            ext = f.suffix.lower()
            if ext not in spec.ICON_FORMATS:
                E(f"icons/{f.name}: unsupported format '{ext}'")
                continue
            if len(f.name) > spec.MAX_FILENAME_LEN:
                E(f"icons/{f.name}: filename >{spec.MAX_FILENAME_LEN} chars")
            if ext in RASTER:
                try:
                    with Image.open(f) as im:
                        w, h = im.size
                    if (w, h) != (spec.ICON_SIZE, spec.ICON_SIZE):
                        E(f"icons/{f.name}: {w}x{h}, must be "
                          f"{spec.ICON_SIZE}x{spec.ICON_SIZE}")
                    if ext in {".gif", ".webp"}:
                        if f.stat().st_size > spec.ANIM_MAX_BYTES:
                            W(f"icons/{f.name}: {f.stat().st_size//1024}KB "
                              f"exceeds ~{spec.ANIM_MAX_BYTES//1024}KB animated budget")
                        for m in _anim_warnings(f.name, f):
                            W(m)
                except Exception as e:  # unreadable/corrupt raster
                    E(f"icons/{f.name}: cannot read image ({e})")
            on_disk[f.name] = f

    # --- icons.json cross-check ---
    ijpath = pack / spec.FILE_ICONS_JSON
    if not ijpath.exists():
        E(f"missing {spec.FILE_ICONS_JSON}")
    else:
        try:
            entries = json.loads(ijpath.read_text())
        except json.JSONDecodeError as e:
            E(f"{spec.FILE_ICONS_JSON} is not valid JSON: {e}")
            entries = []
        if not isinstance(entries, list):
            E(f"{spec.FILE_ICONS_JSON} must be a JSON array")
            entries = []
        referenced = set()
        for i, e in enumerate(entries):
            for k in spec.ICON_ENTRY_REQUIRED:
                if k not in e:
                    E(f"icons.json[{i}]: missing '{k}'")
            p = e.get("path")
            if p:
                referenced.add(p)
                if p not in on_disk:
                    E(f"icons.json[{i}]: path '{p}' not found in icons/")
            if e.get("tags") == []:
                W(f"icons.json[{i}] '{e.get('name', p)}': no tags "
                  f"(hurts Marketplace search)")
        for name in on_disk:
            if name not in referenced:
                W(f"icons/{name}: on disk but not listed in icons.json")

    return errors, warnings


def print_report(pack_dir, errors, warnings):
    for w in warnings:
        print(warn(f"  ⚠ {w}"))
    for e in errors:
        print(err(f"  ✖ {e}"))
    if not errors and not warnings:
        print(ok("  ✓ pack is valid — no issues"))
    elif not errors:
        print(ok(f"  ✓ valid ({len(warnings)} warning(s))"))
    else:
        print(err(f"  ✖ {len(errors)} error(s), {len(warnings)} warning(s)"))
