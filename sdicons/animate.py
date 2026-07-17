"""Generate an animated icon from per-phase SVG frames.

Elgato animated icons: 144×144 GIF/WEBP, ~10-20 fps, ≤5 s loop, < 1 MB. GIF
only carries 1-bit alpha (jagged on soft/anti-aliased edges), so for
transparent full-colour icons **WEBP** (full alpha) is the better container —
both are accepted. Pick the format by the output extension.

The `render`/`validate` steps already accept animated SOURCE files (a GIF/WEBP
in `src/` is resized to 144×144 and its timing checked). This module is the
missing GENERATOR: turn a motion — a function `phase(t) -> svg_string` for
`t` in [0, 1) — into a seamless looping animated icon by rendering N evenly
spaced phases through rsvg-convert and assembling them.

For pack authors: define one `phase(t)` per animated instrument (rotation
angle, bar heights, a scrolling waveform… as functions of t), call
`animate_svg(phase, "src/<name>.webp")`, then build the pack normally.
"""
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from . import spec
from .util import require_tool, ok


def render_phases(phase, n, size=spec.ICON_SIZE):
    """Render n evenly-spaced phases of a motion to RGBA frames."""
    require_tool("rsvg-convert")
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            svg = phase(i / n)                      # t in [0, 1)
            png = Path(tmp) / f"{i:03d}.png"
            subprocess.run(
                ["rsvg-convert", "-w", str(size), "-h", str(size),
                 "-o", str(png), "-"],
                input=svg.encode(), check=True)
            frames.append(Image.open(png).convert("RGBA").copy())
    return frames


def save_animated(frames, out, fps=15):
    """Write frames as a looping GIF or WEBP (by out extension)."""
    out = Path(out)
    dur = int(round(1000 / fps))
    if out.suffix.lower() == ".gif":
        # GIF: 1-bit alpha via a reserved palette index, applied to EVERY frame
        # (a raw RGBA save keeps alpha only on frame 0 — the key colour then
        # flashes opaque mid-loop; see render._rgba_to_p / the CLAUDE.md gotcha).
        from .render import _rgba_to_p, _TRANSPARENT_IDX
        pal = [_rgba_to_p(f.convert("RGBA")) for f in frames]
        pal[0].save(out, save_all=True, append_images=pal[1:],
                    duration=dur, loop=0, disposal=2,
                    transparency=_TRANSPARENT_IDX, optimize=False)
    else:
        frames[0].save(out, format="WEBP", save_all=True,
                       append_images=frames[1:], duration=dur, loop=0,
                       lossless=False, quality=88, method=6)
    kb = out.stat().st_size // 1024
    print(ok(f"  animated {out.name} — {len(frames)} frames @ {fps}fps, {kb}KB"))
    return out


def animate_svg(phase, out, frames=30, fps=15, size=spec.ICON_SIZE):
    """Motion `phase(t)->svg` → looping animated icon at `out`."""
    return save_animated(render_phases(phase, frames, size), out, fps)


def animate_frames_dir(frames_dir, out, fps=15, size=spec.ICON_SIZE):
    """Assemble a folder of frame images (sorted by name) into one animation."""
    exts = (".png", ".webp", ".gif", ".jpg", ".jpeg")
    files = sorted(p for p in Path(frames_dir).iterdir()
                   if p.suffix.lower() in exts and not p.name.startswith("."))
    if not files:
        raise SystemExit(f"no frame images in {frames_dir}")
    frames = [Image.open(p).convert("RGBA").resize((size, size)) for p in files]
    return save_animated(frames, out, fps)
