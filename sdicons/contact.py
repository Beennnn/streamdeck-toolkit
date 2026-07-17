"""Build a contact-sheet PNG of the whole palette so you can eyeball it.

Same idea as wled-assets' contact sheets: one glance tells you if the set
is visually coherent before you ship it. SVG icons are rasterized on the
fly via render so they appear too.
"""
import tempfile
from pathlib import Path

from PIL import Image

from . import spec
from .render import render_svg
from .util import ok

COLS = 8
CELL = spec.ICON_SIZE          # 144
PAD = 8
BG = (24, 24, 24, 255)


def contact_sheet(pack_dir, out_path=None):
    pack = Path(pack_dir)
    icons_dir = pack / spec.DIR_ICONS
    out_path = Path(out_path) if out_path else pack / "contact-sheet.png"

    files = [f for f in sorted(icons_dir.iterdir())
             if f.suffix.lower() in spec.ICON_FORMATS and not f.name.startswith(".")]
    if not files:
        raise SystemExit("no icons to render into a contact sheet")

    rows = (len(files) + COLS - 1) // COLS
    W = COLS * CELL + (COLS + 1) * PAD
    H = rows * CELL + (rows + 1) * PAD
    sheet = Image.new("RGBA", (W, H), BG)

    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(files):
            if f.suffix.lower() == ".svg":
                png = Path(tmp) / f"{i}.png"
                render_svg(f, png)
                im = Image.open(png).convert("RGBA")
            else:
                im = Image.open(f).convert("RGBA")
            if im.size != (CELL, CELL):
                im = im.resize((CELL, CELL))
            r, c = divmod(i, COLS)
            x = PAD + c * (CELL + PAD)
            y = PAD + r * (CELL + PAD)
            sheet.alpha_composite(im, (x, y))

    sheet.save(out_path)
    print(ok(f"wrote {out_path.name} — {len(files)} icons, {rows}x{COLS} grid"))
    return out_path
