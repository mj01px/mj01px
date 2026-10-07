"""Render the streak / numbers card that sits beside the ASCII portrait.

Same 840x880 canvas as mauro-ascii.svg so both panels line up at equal widths.
Six tiles slide in and count up to the real values, then a contributions-per-
month bar chart grows underneath. GitHub runs CSS/SMIL inside <img> SVGs but
never JS, so the count-up is a stack of pre-rendered frames toggled with <set>.

Usage:
    python scripts/stats_svg.py [output.svg]
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from svg_kit import BAR, FRAME, GREEN, INK, MUTED, TILE, TITLEBAR_H, window

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "contributions.json"

W, H = 840, 880
PAD = 20
GAP = 16
COLS, ROWS = 2, 3
TILE_W = (W - 2 * PAD - GAP * (COLS - 1)) / COLS
TILE_H = 150
TILES_TOP = TITLEBAR_H + PAD + 4
CHART_TOP = TILES_TOP + ROWS * (TILE_H + GAP)

TILE_DELAY = 0.15
SLIDE_S = 0.45
COUNT_S = 1.2
FRAMES = 16
BARS_START = TILE_DELAY * COLS * ROWS + 0.4
BAR_DELAY = 0.06
BAR_S = 0.6

CSS = (
    f".t{{opacity:0;animation:rise {SLIDE_S}s ease-out both}}"
    "@keyframes rise{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}"
    f".b{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow {BAR_S}s ease-out both}}"
    "@keyframes grow{to{transform:scaleY(1)}}"
    "@media (prefers-reduced-motion:reduce){.t,.b{opacity:1!important;transform:none!important;animation:none!important}}"
)


@dataclass(frozen=True)
class Stat:
    label: str
    value: float
    suffix: str
    caption: str
    color: str


def short_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d:%b} {d.day}"


def streak_span(streak: dict[str, Any]) -> str:
    if not streak["length"]:
        return "—"
    return f"{short_date(str(streak['start']))} – {short_date(str(streak['end']))}"


def build_stats(data: dict[str, Any]) -> list[Stat]:
    cur = data["current_streak"]
    lng = data["longest_streak"]
    best = data["best_day"]
    n_days = len(data["days"])
    active = int(data["active_days"])
    return [
        Stat("current streak", cur["length"], " days", streak_span(cur), GREEN),
        Stat("longest streak", lng["length"], " days", streak_span(lng), INK),
        Stat("contributions", data["total_contributions"], "", "in the last year", INK),
        Stat("active days", active, f" / {n_days}", f"{active / n_days:.0%} of the year", INK),
        Stat("best day", best["count"], "", short_date(best["date"]), INK),
        Stat("avg / active day", float(data["avg_per_active_day"]), "", "contributions", INK),
    ]


def number(value: float, as_float: bool) -> str:
    return f"{value:,.1f}" if as_float else f"{round(value):,}"


def tile(i: int, stat: Stat) -> str:
    col, row = i % COLS, i // COLS
    x = PAD + col * (TILE_W + GAP)
    y = TILES_TOP + row * (TILE_H + GAP)
    start = i * TILE_DELAY
    count_from = start + SLIDE_S * 0.6
    as_float = isinstance(stat.value, float)

    parts = [
        f'<g class="t" style="animation-delay:{start:.2f}s">',
        f'<rect x="{x:.1f}" y="{y}" width="{TILE_W:.1f}" height="{TILE_H}" rx="10" fill="{TILE}" stroke="{FRAME}"/>',
        f'<text x="{x + 24:.1f}" y="{y + 40}" fill="{MUTED}" font-size="22">$ {stat.label}</text>',
    ]
    for k in range(1, FRAMES + 1):
        eased = 1 - (1 - k / FRAMES) ** 3  # ease-out cubic: decelerates into the real number
        show = count_from + COUNT_S * (k - 1) / FRAMES
        hide = count_from + COUNT_S * k / FRAMES
        sets = f'<set attributeName="opacity" to="1" begin="{show:.3f}s"/>'
        if k < FRAMES:
            sets += f'<set attributeName="opacity" to="0" begin="{hide:.3f}s"/>'
        parts.append(
            f'<text x="{x + 24:.1f}" y="{y + 100}" opacity="0" font-size="54" font-weight="700" '
            f'fill="{stat.color}">{number(stat.value * eased, as_float)}'
            f'<tspan font-size="24" font-weight="400" fill="{MUTED}">{stat.suffix}</tspan>{sets}</text>'
        )
    parts.append(f'<text x="{x + 24:.1f}" y="{y + 132}" fill="{MUTED}" font-size="20">{stat.caption}</text>')
    parts.append("</g>")
    return "".join(parts)


def month_chart(monthly: list[dict[str, Any]]) -> str:
    chart_w = W - 2 * PAD
    chart_h = H - PAD - CHART_TOP
    parts = [
        f'<g class="t" style="animation-delay:{BARS_START - 0.3:.2f}s">',
        f'<rect x="{PAD}" y="{CHART_TOP}" width="{chart_w}" height="{chart_h}" rx="10" fill="{TILE}" stroke="{FRAME}"/>',
        f'<text x="{PAD + 24}" y="{CHART_TOP + 40}" fill="{MUTED}" font-size="22">$ contributions / month</text>',
        "</g>",
    ]
    top, bottom = CHART_TOP + 64, CHART_TOP + chart_h - 40
    left, right = PAD + 24, PAD + chart_w - 24
    slot = (right - left) / len(monthly)
    bar_w = slot * 0.62
    peak = max(int(m["total"]) for m in monthly) or 1

    for i, m in enumerate(monthly):
        total = int(m["total"])
        h = max(2.0, (bottom - top) * total / peak)
        bx = left + i * slot + (slot - bar_w) / 2
        cx = bx + bar_w / 2
        delay = BARS_START + i * BAR_DELAY
        is_peak = total == peak
        parts.append(
            f'<rect class="b" x="{bx:.1f}" y="{bottom - h:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
            f'rx="3" fill="{GREEN if is_peak else BAR}" style="animation-delay:{delay:.2f}s"/>'
        )
        initial = dt.date.fromisoformat(f"{m['month']}-01").strftime("%b")[0]
        parts.append(
            f'<text x="{cx:.1f}" y="{bottom + 28}" fill="{MUTED}" font-size="18" text-anchor="middle">{initial}</text>'
        )
        if is_peak:
            parts.append(
                f'<text class="t" style="animation-delay:{delay + BAR_S:.2f}s" x="{cx:.1f}" y="{bottom - h - 10:.1f}" '
                f'fill="{INK}" font-size="18" text-anchor="middle">{peak:,}</text>'
            )
    return "".join(parts)


def render(data: dict[str, Any]) -> str:
    body = "".join(tile(i, s) for i, s in enumerate(build_stats(data)))
    body += month_chart(data["monthly"])
    return window(W, H, "mauro@github: ~$ ./stats.sh", body, CSS)


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stats.svg"
    svg = render(json.loads(DATA_PATH.read_text()))
    out_path.write_text(svg)
    print(f"stats_svg: wrote {out_path.name} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
