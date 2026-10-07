"""Render the prepped photo as a monochrome ASCII portrait in a terminal window.

One light-gray ink on the dark window: brighter pixels get sparser glyphs and
near-white becomes blank, so only the subject prints. Each row is wiped in left
to right with a block cursor riding the edge, top to bottom, like a terminal
printing it once; then a `whoami` status line keeps a blinking cursor.

Usage:
    python scripts/portrait_svg.py [prepped.png] [output.svg]
    STATIC=1 python scripts/portrait_svg.py   # frozen frame, for previews
"""

from __future__ import annotations

import os
import sys
from html import escape
from pathlib import Path

from PIL import Image, ImageEnhance
from svg_kit import ASCII_INK, FRAME, MUTED, TITLEBAR_H, window

ROOT = Path(__file__).resolve().parent.parent

COLS = int(os.environ.get("COLS", "180"))
ART_W = 800
CELL_W = ART_W / COLS
CELL_H = CELL_W * 15 / 8  # monospace glyph aspect
ROWS = round(COLS * 8 / 15)
ART_H = ROWS * CELL_H
PAD = 20
STATUS_H = 30
W = ART_W + 2 * PAD
H = TITLEBAR_H + ART_H + STATUS_H + PAD

RAMP = " .`:-=+*oa#%@"  # sparse -> dense
GAMMA = 1.18  # >1 lifts mid-tones into sparser glyphs
CONTRAST = 1.05
BLANK_ABOVE = 0.80  # luminance at/above this prints nothing
PRINT_S = 5.8  # whole portrait prints in ~6s at any resolution

WHOAMI = "mauro@github:~$ whoami "
NAME = "Mauro Junior"


def ascii_rows(src: Path) -> list[str]:
    im = Image.open(src).convert("L")
    im = ImageEnhance.Contrast(im).enhance(CONTRAST).resize((COLS, ROWS), Image.Resampling.LANCZOS)
    px = im.tobytes()  # one byte per pixel in "L" mode, row-major
    rows: list[str] = []
    for y in range(ROWS):
        line = []
        for x in range(COLS):
            lum = (px[y * COLS + x] / 255.0) ** GAMMA
            if lum >= BLANK_ABOVE:
                line.append(" ")
            else:
                line.append(RAMP[round((1.0 - lum) * (len(RAMP) - 1))])
        rows.append("".join(line))
    return rows


def art(rows: list[str], static: bool) -> str:
    top = TITLEBAR_H + PAD * 0.35
    row_s = PRINT_S / ROWS
    font_size = CELL_H * 0.86
    out: list[str] = []
    for r, line in enumerate(rows):
        row_y = top + r * CELL_H
        text = (
            f'<text xml:space="preserve" x="{PAD}" y="{row_y + CELL_H * 0.74:.1f}" fill="{ASCII_INK}" '
            f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">{escape(line)}</text>'
        )
        if static:
            out.append(text)
            continue
        begin = r * row_s
        out.append(
            f'<clipPath id="row{r}"><rect x="{PAD}" y="{row_y:.1f}" width="0" height="{CELL_H:.2f}">'
            f'<animate attributeName="width" from="0" to="{ART_W}" begin="{begin:.3f}s" dur="{row_s:.3f}s" '
            f'fill="freeze"/></rect></clipPath><g clip-path="url(#row{r})">{text}</g>'
            f'<rect y="{row_y + 1:.1f}" width="{CELL_W:.2f}" height="{CELL_H - 2:.2f}" fill="{ASCII_INK}" opacity="0">'
            f'<animate attributeName="x" from="{PAD}" to="{PAD + ART_W}" begin="{begin:.3f}s" dur="{row_s:.3f}s" '
            f'fill="freeze"/><set attributeName="opacity" to="0.85" begin="{begin:.3f}s"/>'
            f'<set attributeName="opacity" to="0" begin="{begin + row_s:.3f}s"/></rect>'
        )
    return "".join(out)


def status_bar() -> str:
    line_y = TITLEBAR_H + ART_H + PAD * 0.35
    text_y = line_y + 19
    cursor_x = PAD + len(WHOAMI + NAME + " ") * 13 * 0.6  # 13px mono glyph ~0.6em wide
    return (
        f'<line x1="0" y1="{line_y:.1f}" x2="{W}" y2="{line_y:.1f}" stroke="{FRAME}"/>'
        f'<text x="{PAD}" y="{text_y:.1f}" fill="{MUTED}" font-size="13">{escape(WHOAMI)}'
        f'<tspan fill="{ASCII_INK}">{escape(NAME)}</tspan></text>'
        f'<rect x="{cursor_x:.1f}" y="{text_y - 12:.1f}" width="8" height="14" fill="{ASCII_INK}">'
        '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" '
        'repeatCount="indefinite"/></rect>'
    )


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "source-prepped.png"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "mauro-ascii.svg"
    static = bool(os.environ.get("STATIC"))
    svg = window(W, H, "mauro@github: ~$ ./portrait.sh", art(ascii_rows(src), static) + status_bar())
    dst.write_text(svg)
    print(f"portrait_svg: wrote {dst.name} ({W:g}x{H:g}, {COLS}x{ROWS} chars)")


if __name__ == "__main__":
    main()
