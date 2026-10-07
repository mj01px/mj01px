#!/usr/bin/env python3
"""Render the prepped photo as a colored-ASCII portrait inside an SVG.

Usage:
    python scripts/make_ascii_svg.py [src] [dst]

Defaults: assets/dp.png -> mauro-ascii.svg

The glyph for each cell is picked by luminance (brighter -> denser glyph) and
painted with the cell's own color, slightly saturated, on a GitHub-dark
background so the result reads as a terminal portrait. Consecutive cells that
quantize to the same color are merged into one <tspan> to keep the file small.
"""
import sys
from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else "assets/dp.png"
DST = sys.argv[2] if len(sys.argv) > 2 else "mauro-ascii.svg"

COLS = 76                 # character columns
CHAR_ASPECT = 0.50        # monospace cell is ~2x taller than wide
FONT_SIZE = 11            # px, in SVG user units
CELL_W = FONT_SIZE * 0.60
CELL_H = FONT_SIZE
BG = "#0d1117"
# dark -> bright; a leading space means "let the background show through".
RAMP = " .,:;i1tfLCG08@"


def luminance(r: int, g: int, b: int) -> float:
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def boost(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Lift very dark cells a touch so the colored glyph stays visible."""
    lum = luminance(r, g, b)
    if lum < 0.18:
        f = 0.18 / max(lum, 0.01)
        r, g, b = (min(255, int(c * f)) for c in (r, g, b))
    return r, g, b


def quant(c: int) -> int:
    return (c // 16) * 16 + 8


def esc(ch: str) -> str:
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}.get(ch, ch)


def main() -> None:
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    rows = max(1, int(COLS * (h / w) * CHAR_ASPECT))
    small = im.resize((COLS, rows), Image.LANCZOS)
    px = small.load()

    width = round(COLS * CELL_W) + 16
    height = round(rows * CELL_H) + 16

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="monospace" '
        f'font-size="{FONT_SIZE}" >',
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
    ]

    for ry in range(rows):
        y = 8 + ry * CELL_H + FONT_SIZE - 2
        spans: list[str] = []
        run_chars: list[str] = []
        run_color = None
        run_start = 0
        for cx in range(COLS):
            r, g, b = px[cx, ry]
            glyph = RAMP[min(len(RAMP) - 1, int(luminance(r, g, b) * (len(RAMP) - 1)))]
            r, g, b = boost(r, g, b)
            color = f"#{quant(r):02x}{quant(g):02x}{quant(b):02x}"
            if color != run_color:
                if run_chars:
                    spans.append((run_start, run_color, "".join(run_chars)))
                run_color, run_chars, run_start = color, [], cx
            run_chars.append(glyph)
        if run_chars:
            spans.append((run_start, run_color, "".join(run_chars)))

        parts = [f'<text y="{y}" xml:space="preserve">']
        for start, color, text in spans:
            if text.strip() == "":
                continue  # all-space run: background shows through
            x = round(8 + start * CELL_W, 1)
            parts.append(f'<tspan x="{x}" fill="{color}">{"".join(esc(c) for c in text)}</tspan>')
        parts.append("</text>")
        if len(parts) > 2:
            lines.append("".join(parts))

    lines.append("</svg>")
    with open(DST, "w") as fh:
        fh.write("\n".join(lines))
    print(f"make_ascii_svg: wrote {DST} ({width}x{height}, {COLS}x{rows} cells)")


if __name__ == "__main__":
    main()
