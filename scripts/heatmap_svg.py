"""Render data/contributions.json as an animated contribution graph SVG.

Transparent background and GitHub's own level colors, so it looks like the
real profile graph. Cells pop in with a diagonal sweep (left -> right, top ->
bottom) and active days flash bright as they land; plays once, then holds.

Usage:
    python scripts/heatmap_svg.py [output.svg]
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from svg_kit import INK, LEVEL_COLORS, MUTED, SANS

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "contributions.json"

CELL = 13
STEP = CELL + 3
LEFT = 34
TOP = 24
SWEEP_S = 3.6  # time for the reveal front to cross the whole grid
POP_S = 0.55
ROW_WEIGHT = 0.55  # how much each row lags behind the one above it

CSS = (
    f"text.lbl{{fill:{MUTED};font-size:13px;font-weight:600}}"
    f"text.total{{fill:{INK};font-size:15px;font-weight:700}}"
    f".c{{transform-box:fill-box;transform-origin:center;opacity:0;animation:pop {POP_S}s ease-out both}}"
    f".on{{animation:pop {POP_S}s ease-out both,flash {POP_S + 0.15:.2f}s ease-out both}}"
    "@keyframes pop{0%{opacity:0;transform:scale(.2)}60%{opacity:1;transform:scale(1.1)}"
    "100%{opacity:1;transform:scale(1)}}"
    "@keyframes flash{0%,45%{filter:brightness(2.4)}100%{filter:brightness(1)}}"
    "@media (prefers-reduced-motion:reduce){.c{opacity:1!important;animation:none!important}}"
)


def sunday_index(date: dt.date) -> int:
    """Row in the calendar: Sunday=0 ... Saturday=6."""
    return (date.weekday() + 1) % 7


def render(data: dict[str, Any]) -> str:
    days = [(dt.date.fromisoformat(d["date"]), int(d["level"])) for d in data["days"]]
    origin = days[0][0] - dt.timedelta(days=sunday_index(days[0][0]))
    weeks = (days[-1][0] - origin).days // 7 + 1
    last_order = (weeks - 1) + 6 * ROW_WEIGHT

    width = LEFT + weeks * STEP + 6
    height = TOP + 7 * STEP + 22
    out: list[str] = []

    month_seen: int | None = None
    for week in range(weeks):
        month = (origin + dt.timedelta(weeks=week)).month
        if month != month_seen:
            month_seen = month
            label = dt.date(2000, month, 1).strftime("%b")
            out.append(f'<text class="lbl" x="{LEFT + week * STEP}" y="{TOP - 8}">{label}</text>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text class="lbl" x="2" y="{TOP + row * STEP + CELL - 2}">{name}</text>')

    for date, level in days:
        week, row = (date - origin).days // 7, sunday_index(date)
        delay = (week + row * ROW_WEIGHT) / last_order * SWEEP_S
        cls = "c on" if level else "c"
        out.append(
            f'<rect class="{cls}" x="{LEFT + week * STEP}" y="{TOP + row * STEP}" '
            f'width="{CELL}" height="{CELL}" rx="2.5" fill="{LEVEL_COLORS[level]}" '
            f'style="animation-delay:{delay:.3f}s"/>'
        )

    total = int(data["total_contributions"])
    out.append(f'<text class="total" x="{LEFT}" y="{height - 6}">{total:,} contributions in the last year</text>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{SANS}">'
        f"<style>{CSS}</style>" + "".join(out) + "</svg>"
    )


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "contrib-heatmap.svg"
    svg = render(json.loads(DATA_PATH.read_text()))
    out_path.write_text(svg)
    print(f"heatmap_svg: wrote {out_path.name} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
