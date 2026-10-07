"""Scrape the public GitHub contribution calendar and derive profile stats.

Reads the same HTML fragment the profile page renders (no token needed), so
counts and color levels match github.com exactly. Writes data/contributions.json,
which heatmap_svg.py and stats_svg.py consume.

Usage:
    python scripts/profile_data.py [username]
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "contributions.json"
DEFAULT_USER = "mj01px"
_COUNT_RE = re.compile(r"^([\d,]+) contributions?\b")


class CalendarParseError(RuntimeError):
    """Raised when the contribution calendar markup cannot be read."""


@dataclass(frozen=True)
class Day:
    date: dt.date
    count: int
    level: int


@dataclass(frozen=True)
class Streak:
    length: int
    start: dt.date | None
    end: dt.date | None


class _CalendarParser(HTMLParser):
    """Collect calendar cells and the tooltips that carry their counts."""

    def __init__(self) -> None:
        super().__init__()
        self.cells: dict[str, tuple[dt.date, int]] = {}
        self.tooltips: dict[str, str] = {}
        self._tooltip_for: str | None = None
        self._tooltip_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "td" and "ContributionCalendar-day" in (a.get("class") or ""):
            cell_id, date = a.get("id"), a.get("data-date")
            if cell_id and date:
                self.cells[cell_id] = (dt.date.fromisoformat(date), int(a.get("data-level") or 0))
        elif tag == "tool-tip" and a.get("for"):
            self._tooltip_for, self._tooltip_text = a["for"], []

    def handle_data(self, data: str) -> None:
        if self._tooltip_for is not None:
            self._tooltip_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tool-tip" and self._tooltip_for is not None:
            self.tooltips[self._tooltip_for] = "".join(self._tooltip_text).strip()
            self._tooltip_for = None


def count_from_tooltip(text: str) -> int:
    """Turn '3 contributions on May 2nd.' / 'No contributions on ...' into an int."""
    match = _COUNT_RE.match(text)
    return int(match.group(1).replace(",", "")) if match else 0


def parse_days(html: str) -> list[Day]:
    """Extract every calendar day, sorted chronologically.

    Raises:
        CalendarParseError: If no calendar cells are present in the markup.
    """
    parser = _CalendarParser()
    parser.feed(html)
    if not parser.cells:
        raise CalendarParseError("no ContributionCalendar-day cells found; GitHub markup may have changed")
    days = [
        Day(date, count_from_tooltip(parser.tooltips.get(cell_id, "")), level)
        for cell_id, (date, level) in parser.cells.items()
    ]
    return sorted(days, key=lambda d: d.date)


def fetch_html(user: str) -> str:
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": f"{user}-profile-readme"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def current_streak(days: list[Day]) -> Streak:
    """Consecutive active days ending today (or yesterday, since today isn't over)."""
    i = len(days) - 1
    if i >= 0 and days[i].count == 0:
        i -= 1
    end = i
    while i >= 0 and days[i].count > 0:
        i -= 1
    length = end - i
    if length <= 0:
        return Streak(0, None, None)
    return Streak(length, days[i + 1].date, days[end].date)


def longest_streak(days: list[Day]) -> Streak:
    best = Streak(0, None, None)
    run_start: int | None = None
    for i, day in enumerate(days):
        if day.count == 0:
            run_start = None
            continue
        if run_start is None:
            run_start = i
        if i - run_start + 1 > best.length:
            best = Streak(i - run_start + 1, days[run_start].date, day.date)
    return best


def summarize(user: str, days: list[Day]) -> dict[str, Any]:
    total = sum(d.count for d in days)
    active = sum(1 for d in days if d.count > 0)
    best = max(days, key=lambda d: d.count)
    monthly: dict[str, int] = {}
    for d in days:
        key = d.date.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + d.count

    def streak_json(s: Streak) -> dict[str, Any]:
        return {k: (v.isoformat() if isinstance(v, dt.date) else v) for k, v in asdict(s).items()}

    return {
        "username": user,
        "generated_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0].date.isoformat(), "end": days[-1].date.isoformat()},
        "total_contributions": total,
        "active_days": active,
        "avg_per_active_day": round(total / active, 1) if active else 0.0,
        "current_streak": streak_json(current_streak(days)),
        "longest_streak": streak_json(longest_streak(days)),
        "best_day": {"date": best.date.isoformat(), "count": best.count},
        "monthly": [{"month": k, "total": v} for k, v in sorted(monthly.items())],
        "days": [{"date": d.date.isoformat(), "count": d.count, "level": d.level} for d in days],
    }


def main() -> None:
    user = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USER
    data = summarize(user, parse_days(fetch_html(user)))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(
        f"profile_data: {data['total_contributions']} contributions, "
        f"streak {data['current_streak']['length']}/{data['longest_streak']['length']}"
    )


if __name__ == "__main__":
    main()
