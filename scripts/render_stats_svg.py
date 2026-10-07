#!/usr/bin/env python3
"""Render a neofetch-style GitHub stats card (streak + totals) as an SVG.

Usage:
    python scripts/render_stats_svg.py [username] [dst]

Env: GH_TOKEN (or GITHUB_TOKEN) with public read access.
Defaults: username=mj01px, dst=stats.svg

Sits to the right of the ASCII portrait, so it mimics `neofetch` output.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "mj01px"
DST = sys.argv[2] if len(sys.argv) > 2 else "stats.svg"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

BG = "#0d1117"
KEY = "#58a6ff"     # labels
VAL = "#c9d1d9"     # values
ACCENT = "#3fb950"  # prompt / headline
DIM = "#8b949e"

QUERY = """
query($login:String!){
  user(login:$login){
    name login createdAt
    followers{ totalCount }
    repositories(first:100, ownerAffiliations:OWNER, isFork:false){
      totalCount nodes{ stargazerCount }
    }
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ contributionCount date } }
      }
    }
  }
}
"""


def graphql(query: str, variables: dict) -> dict:
    if not TOKEN:
        sys.exit("render_stats_svg: set GH_TOKEN or GITHUB_TOKEN")
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": f"{USER}-profile-art",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    if "errors" in payload:
        sys.exit(f"render_stats_svg: GraphQL error: {payload['errors']}")
    return payload["data"]


def streaks(days: list[dict]) -> tuple[int, int]:
    """Return (current_streak, longest_streak) from dated contribution days."""
    days = sorted(days, key=lambda d: d["date"])
    longest = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        longest = max(longest, run)

    today = dt.date.today()
    counts = {d["date"]: d["contributionCount"] for d in days}
    current = 0
    cur = today
    # today may have no activity yet; let the streak start at yesterday.
    if counts.get(cur.isoformat(), 0) == 0:
        cur -= dt.timedelta(days=1)
    while counts.get(cur.isoformat(), 0) > 0:
        current += 1
        cur -= dt.timedelta(days=1)
    return current, longest


def main() -> None:
    u = graphql(QUERY, {"login": USER})["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    all_days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(all_days)
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
    joined = dt.datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00")).year
    name = u["name"] or u["login"]

    rows = [
        ("Contributions (yr)", str(cal["totalContributions"])),
        ("Current streak", f"{current} days"),
        ("Longest streak", f"{longest} days"),
        ("Public repos", str(u["repositories"]["totalCount"])),
        ("Total stars", str(stars)),
        ("Followers", str(u["followers"]["totalCount"])),
        ("On GitHub since", str(joined)),
    ]

    pad, line_h, fs = 20, 26, 14
    width = 420
    header = f"{name.lower().replace(' ', '')}@github"
    rule = "-" * len(header)
    height = pad * 2 + line_h * (len(rows) + 2) + 6

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="monospace" font-size="{fs}">',
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
        f'<text x="{pad}" y="{pad + fs}" fill="{ACCENT}" font-weight="bold">{header}</text>',
        f'<text x="{pad}" y="{pad + fs + line_h}" fill="{DIM}">{rule}</text>',
    ]
    y = pad + fs + line_h * 2
    label_w = max(len(k) for k, _ in rows)
    for k, v in rows:
        key = (k + ":").ljust(label_w + 2)
        out.append(
            f'<text x="{pad}" y="{y}" xml:space="preserve">'
            f'<tspan fill="{KEY}">{key}</tspan>'
            f'<tspan fill="{VAL}">{v}</tspan></text>'
        )
        y += line_h
    out.append("</svg>")

    with open(DST, "w") as fh:
        fh.write("\n".join(out))
    print(f"render_stats_svg: wrote {DST} (streak {current}/{longest}, {stars} stars)")


if __name__ == "__main__":
    main()
