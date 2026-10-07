#!/usr/bin/env python3
"""Render the real GitHub contribution calendar as an animated heatmap SVG.

Usage:
    python scripts/render_heatmap_svg.py [username] [dst]

Env: GH_TOKEN (or GITHUB_TOKEN) with public read access.
Defaults: username=mj01px, dst=contrib-heatmap.svg

Cells reveal one by one (staggered CSS fade-in), matching the terminal vibe.
"""
import json
import os
import sys
import urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "mj01px"
DST = sys.argv[2] if len(sys.argv) > 2 else "contrib-heatmap.svg"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

CELL = 13       # cell size
GAP = 3         # gap between cells
PAD = 16
BG = "#0d1117"

QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ contributionCount color date weekday } }
      }
    }
  }
}
"""


def graphql(query: str, variables: dict) -> dict:
    if not TOKEN:
        sys.exit("render_heatmap_svg: set GH_TOKEN or GITHUB_TOKEN")
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
        sys.exit(f"render_heatmap_svg: GraphQL error: {payload['errors']}")
    return payload["data"]


def main() -> None:
    data = graphql(QUERY, {"login": USER})
    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    total = cal["totalContributions"]

    width = PAD * 2 + len(weeks) * (CELL + GAP) - GAP
    height = PAD * 2 + 7 * (CELL + GAP) - GAP + 22

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="monospace">',
        "<style>"
        ".c{opacity:0;animation:p .45s ease forwards}"
        "@keyframes p{to{opacity:1}}"
        "@media(prefers-reduced-motion){.c{opacity:1;animation:none}}"
        "</style>",
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
    ]

    i = 0
    for wx, week in enumerate(weeks):
        for day in week["contributionDays"]:
            x = PAD + wx * (CELL + GAP)
            y = PAD + day["weekday"] * (CELL + GAP)
            # GitHub returns near-white for empty days on a light canvas; map
            # those to a subtle dark cell so the grid reads on a dark bg.
            color = day["color"]
            if color.upper() in ("#EBEDF0", "#EBEDF0FF"):
                color = "#161b22"
            delay = round(i * 0.004, 3)
            out.append(
                f'<rect class="c" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2.5" fill="{color}" style="animation-delay:{delay}s"/>'
            )
            i += 1

    out.append(
        f'<text x="{PAD}" y="{height - 8}" fill="#8b949e" font-size="12">'
        f'{total} contributions in the last year</text>'
    )
    out.append("</svg>")

    with open(DST, "w") as fh:
        fh.write("\n".join(out))
    print(f"render_heatmap_svg: wrote {DST} ({total} contributions, {len(weeks)} weeks)")


if __name__ == "__main__":
    main()
