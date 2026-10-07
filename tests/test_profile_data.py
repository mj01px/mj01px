from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from profile_data import (
    CalendarParseError,
    Day,
    count_from_tooltip,
    current_streak,
    longest_streak,
    parse_days,
    summarize,
)

CALENDAR_HTML = """
<table>
<tr>
<td data-date="2026-10-06" id="d-2" data-level="2" class="ContributionCalendar-day"></td>
<td data-date="2026-10-04" id="d-0" data-level="0" class="ContributionCalendar-day"></td>
<td data-date="2026-10-05" id="d-1" data-level="1" class="ContributionCalendar-day"></td>
</tr>
</table>
<tool-tip for="d-0" class="sr-only">No contributions on October 4th.</tool-tip>
<tool-tip for="d-1" class="sr-only">1 contribution on October 5th.</tool-tip>
<tool-tip for="d-2" class="sr-only">1,204 contributions on October 6th.</tool-tip>
"""


def days_from(counts: list[int], start: dt.date = dt.date(2026, 1, 1)) -> list[Day]:
    return [Day(start + dt.timedelta(days=i), c, min(c, 4)) for i, c in enumerate(counts)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("No contributions on October 4th.", 0),
        ("1 contribution on October 5th.", 1),
        ("38 contributions on September 15th.", 38),
        ("1,204 contributions on October 6th.", 1204),
        ("", 0),
    ],
)
def test_count_from_tooltip(text: str, expected: int) -> None:
    assert count_from_tooltip(text) == expected


def test_parse_days_sorts_and_reads_counts_and_levels() -> None:
    days = parse_days(CALENDAR_HTML)
    assert [(d.date.day, d.count, d.level) for d in days] == [(4, 0, 0), (5, 1, 1), (6, 1204, 2)]


def test_parse_days_rejects_unknown_markup() -> None:
    with pytest.raises(CalendarParseError):
        parse_days("<html><body>nothing here</body></html>")


def test_current_streak_ignores_empty_today() -> None:
    streak = current_streak(days_from([1, 0, 2, 3, 0]))
    assert (streak.length, streak.start, streak.end) == (2, dt.date(2026, 1, 3), dt.date(2026, 1, 4))


def test_current_streak_counts_today_when_active() -> None:
    assert current_streak(days_from([0, 5, 5, 5])).length == 3


def test_current_streak_zero_when_broken() -> None:
    assert current_streak(days_from([3, 0, 0])) == current_streak(days_from([0]))
    assert current_streak(days_from([3, 0, 0])).length == 0


def test_longest_streak_picks_first_longest_run() -> None:
    streak = longest_streak(days_from([1, 1, 0, 2, 2, 0, 9, 9]))
    assert (streak.length, streak.start, streak.end) == (2, dt.date(2026, 1, 1), dt.date(2026, 1, 2))


def test_summarize_totals_and_months() -> None:
    days = days_from([2, 0, 4], start=dt.date(2026, 1, 31))
    data = summarize("someone", days)
    assert data["total_contributions"] == 6
    assert data["active_days"] == 2
    assert data["avg_per_active_day"] == 3.0
    assert data["best_day"] == {"date": "2026-02-02", "count": 4}
    assert data["monthly"] == [{"month": "2026-01", "total": 2}, {"month": "2026-02", "total": 4}]
