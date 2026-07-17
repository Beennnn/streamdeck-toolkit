"""Generate the marketing media the Elgato Maker Console asks for at submit.

Verified 2026-07-12 against the real submission wizard. The "Upload media"
step requires, at exact dimensions:
  - Thumbnail   : 1 image, 1920×960 (2:1), png/jpg ≤5 MB
  - Icon previews: up to 5 images, 144×144 (1:1), png/jpg ≤2 MB
  - Gallery     : ≥3 images, 1920×960 (or mp4), png/jpg ≤10 MB

Hand-making these is fiddly, so this builds all of them from a pack's icons:
a titled hero thumbnail, 5 icon-preview tiles, and gallery banners paginating
the whole palette. Output lands in `maker-media/` ready to drag into the
console. See docs/publishing.md for the full submission walkthrough.
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import spec
from .util import ok, warn

_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
_BG = (18, 18, 22)
_TILE = (30, 30, 36)
_TILE_EDGE = (54, 54, 62)
_FG = (240, 240, 246)
_MUTED = (150, 152, 162)


def _font(size):
    for p in _FONTS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _tile(icon_path, size):
    """One icon on a rounded dark tile (matches how it looks on a Stream Deck)."""
    pad = int(size * 0.07)
    ic = Image.open(icon_path).convert("RGBA").resize((size - 2 * pad, size - 2 * pad))
    t = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.16),
                        fill=_TILE + (255,), outline=_TILE_EDGE + (255,), width=2)
    t.alpha_composite(ic, (pad, pad))
    return t


_STATIC_EXTS = {".svg", ".png", ".jpg", ".jpeg"}


def _icons(pack: Path):
    """One tile per icon for the static montages (previews/hero/gallery).

    A pack that ships both a static icon and its animated "<x>-playing.webp"
    active-state variant has TWO files per icon that look identical on a frozen
    frame — including both duplicates every tile in the thumbnail. Collapse to
    one entry per base icon (strip a "-playing" suffix and dedupe same-stem
    static/animated pairs), preferring the static file. The animated gallery is
    built separately from the `animated` source dir, so it is unaffected.
    """
    d = pack / spec.DIR_ICONS
    cands = [p for p in d.iterdir()
             if p.suffix.lower() in spec.ICON_FORMATS and not p.name.startswith(".")]
    best: dict[str, Path] = {}
    for p in cands:
        base = p.stem[:-8] if p.stem.endswith("-playing") else p.stem
        cur = best.get(base)
        if cur is None or (p.suffix.lower() in _STATIC_EXTS
                           and cur.suffix.lower() not in _STATIC_EXTS):
            best[base] = p
    return sorted(best.values())


def _grid(img, icons, y0, cols=6, tile=250, gap=30, margin=90, max_rows=None):
    W = img.width
    gx = (W - 2 * margin - cols * tile) // (cols - 1)
    for i, ic in enumerate(icons):
        r, c = divmod(i, cols)
        if max_rows and r >= max_rows:
            break
        x = margin + c * (tile + gx)
        y = y0 + r * (tile + gap)
        img.paste(_tile(ic, tile).convert("RGB"), (x, y))


def maker_media(pack_dir, out_dir="maker-media", title=None, subtitle=None,
                previews=None, animated=None):
    pack = Path(pack_dir)
    manifest = json.loads((pack / spec.FILE_MANIFEST).read_text())
    title = title or manifest.get("Name", "Icon Pack")
    icons = _icons(pack)
    if not icons:
        raise SystemExit("no icons to build media from")
    by_stem = {p.stem: p for p in icons}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # --- 5 icon previews (144×144, TRANSPARENT RGBA) ---
    # The Maker Console "Icon previews" slot expects the transparent icon art —
    # it renders each on its own tile. An OPAQUE (RGB, no alpha) upload is
    # silently rejected: the slot blanks out ("the previews disappear"). So keep
    # the icon's alpha; do NOT bake a tile / convert to RGB here. (The hero and
    # gallery banners DO tile onto a dark background — that's fine, they're flat
    # RGB banners, not icon-preview slots.)
    prev = ([by_stem[s] for s in previews if s in by_stem] if previews
            else icons)[:5]
    sz = spec.MAKER_PREVIEW_SIZE
    for i, ic in enumerate(prev, 1):
        Image.open(ic).convert("RGBA").resize((sz, sz)).save(out / f"preview-{i}.png")

    # --- thumbnail (1920×960 hero) ---
    W, H = spec.MAKER_HERO_SIZE
    im = Image.new("RGB", (W, H), _BG)
    d = ImageDraw.Draw(im)
    d.text((90, 90), title, font=_font(84), fill=_FG)
    if subtitle:
        d.text((92, 205), subtitle, font=_font(40), fill=_MUTED)
    _grid(im, icons[:18], y0=320 if subtitle else 240, max_rows=2)
    im.save(out / "thumbnail-1920x960.png")

    # --- gallery banners (1920×960), paginate the whole palette, ≥3 ---
    # The 3 rows of 6 MUST fit inside the 960 px canvas, or the Maker Console
    # shows a sliced bottom row — Elgato rejected v1 (2026-07-14) for exactly
    # this "cropping of information". Header strip is 150 px, rows start at
    # y0=190. Fit check with tile=220, gap=24: 190 + 3*220 + 2*24 = 898 ≤ 960 ✓
    # (the old tile=250/y0=250 put the 3rd row at 810..1060 → 100 px cropped).
    per = 18
    pages = max(3, (len(icons) + per - 1) // per)
    for pg in range(pages):
        chunk = icons[pg * per:(pg + 1) * per] or icons[:per]
        g = Image.new("RGB", (W, H), _BG)
        dd = ImageDraw.Draw(g)
        dd.rectangle([0, 0, W, 150], fill=_TILE)
        dd.text((80, 42), f"{title} — {pg + 1}/{pages}", font=_font(60), fill=_FG)
        _grid(g, chunk, y0=190, tile=220, gap=24, max_rows=3)
        g.save(out / f"gallery-{pg + 1}.png")

    # --- animated gallery: AUTOMATIC when the pack ships animated icons ---
    # The Maker Console gallery accepts MP4 (≤50 MB) — the one slot where a
    # listing can SHOW motion. So an animated pack gets an animated gallery for
    # free: we detect the pack's own gif/webp icons (no flag needed). --animated
    # stays as an override to source the grid from a different folder.
    if animated:
        anim_src = sorted(p for p in Path(animated).iterdir()
                          if p.suffix.lower() in _ANIM_EXTS and not p.name.startswith("."))
    else:
        anim_src = [p for p in icons if p.suffix.lower() in _ANIM_EXTS]
    if anim_src:
        animated_gallery(anim_src, out, title=title)
    else:
        print(warn("  (static pack — no animated gallery)"))

    print(ok(f"maker media → {out}/  (thumbnail + {len(prev)} previews "
             f"+ {pages} gallery, all at Maker Console dimensions)"))
    print(warn("  drag these into the console's Upload-media step; see "
               "docs/publishing.md"))
    return out


_ANIM_EXTS = (".webp", ".gif")


def animated_gallery(anim, out, title="", cols=10, fps=8, max_icons=50):
    """Grid of ANIMATED icons → gallery-animated.mp4 (+ .webp) for Maker Console.

    `anim` is a list of gif/webp paths (or a directory). Samples up to
    `max_icons` evenly for visual diversity, tiles them on a 1920×960 (2:1)
    canvas matching the static hero/gallery banners (dark bg + title strip),
    steps every cell through its frames, and loops. NEAREST keeps the LED
    pixel-art crisp. MP4 is the gallery's animated slot (no alpha → dark bg
    baked in); the .webp keeps alpha for reuse elsewhere.
    """
    if isinstance(anim, (str, Path)):
        anim = sorted(p for p in Path(anim).iterdir()
                      if p.suffix.lower() in _ANIM_EXTS and not p.name.startswith("."))
    paths = [Path(p) for p in anim if Path(p).suffix.lower() in _ANIM_EXTS]
    if not paths:
        print(warn("  no animated icons — skipping animated gallery"))
        return None
    # even sample across the set so the montage stays visually diverse
    if len(paths) > max_icons:
        step = len(paths) / max_icons
        paths = [paths[int(i * step)] for i in range(max_icons)]

    W, H = spec.MAKER_VIDEO_SIZE           # 1920×1080 — the gallery MP4 slot
    tile, top = 144, (70 if title else 30)
    rows = (len(paths) + cols - 1) // cols
    gap_x = (W - cols * tile) // (cols + 1)
    gap_y = max(8, (H - top - rows * tile) // (rows + 1))

    ims = [Image.open(p) for p in paths]
    nframes = max(getattr(i, "n_frames", 1) for i in ims)
    tfont = _font(40)
    frames = []
    for k in range(nframes):
        canvas = Image.new("RGBA", (W, H), _BG + (255,))
        if title:
            ImageDraw.Draw(canvas).text((gap_x, 20), title, font=tfont, fill=_FG)
        for idx, im in enumerate(ims):
            im.seek(k % getattr(im, "n_frames", 1))
            fr = im.convert("RGBA").resize((tile, tile), Image.NEAREST)
            r, c = divmod(idx, cols)
            canvas.alpha_composite(fr, (gap_x + c * (tile + gap_x),
                                        top + gap_y + r * (tile + gap_y)))
        frames.append(canvas)

    webp = Path(out) / "gallery-animated.webp"
    frames[0].save(webp, format="WEBP", save_all=True, append_images=frames[1:],
                   duration=int(1000 / fps), loop=0, quality=80, method=6)
    mp4 = _encode_mp4(frames, Path(out) / "gallery-animated.mp4", fps)
    print(ok(f"  animated gallery → {webp.name}" + (f" + {mp4.name}" if mp4 else "")
             + f"  ({len(paths)} icons, {nframes}f, {W}×{H})"))
    return webp


def _encode_mp4(frames, out, fps, min_seconds=6):
    """RGB frames → a Maker-Console-compatible H.264 MP4 (None if no ffmpeg).

    The console's uploader transcodes server-side and rejects "too minimal"
    clips with "Failed to create media". Verified 2026-07-14 that it needs a
    STANDARD file, not just a valid one: the short 14-frame / 8-fps / silent
    montage failed until it was (a) looped to a few seconds, (b) re-timed to
    30 fps, (c) H.264 High profile, and (d) given a silent AAC audio track (a
    video with no audio stream is rejected). So we loop the frames to
    `min_seconds`, add anullsrc audio, and encode High/yuv420p/+faststart.
    """
    if not shutil.which("ffmpeg"):
        print(warn("  ffmpeg not found — skipping .mp4 (webp still written)"))
        return None
    loops = max(1, -(-int(min_seconds * fps) // len(frames)))  # ceil division
    seq = frames * loops
    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(seq):
            f.convert("RGB").save(Path(tmp) / f"{i:04d}.png")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-framerate", str(fps), "-i", str(Path(tmp) / "%04d.png"),
             "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
             "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
             "-pix_fmt", "yuv420p", "-r", "30",
             "-c:a", "aac", "-b:a", "128k", "-shortest",
             "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-movflags", "+faststart",
             str(out)], check=True)
    return out
