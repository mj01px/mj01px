"""Shared palette and terminal-window chrome for the profile SVGs."""

from __future__ import annotations

from html import escape

MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "-apple-system, Segoe UI, Helvetica, Arial, sans-serif"

# GitHub's own dark-theme contribution ramp, indexed by data-level 0..4.
LEVEL_COLORS = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353")

BG_TOP = "#111722"
BG_BOTTOM = "#0d1117"
FRAME = "#30363d"
TILE = "#161b22"
MUTED = "#7d8590"
INK = "#e6edf3"
ASCII_INK = "#c9d1d9"
GREEN = "#39d353"
BAR = "#26a641"

TITLEBAR_H = 30
_LIGHTS = ("#ff5f56", "#ffbd2e", "#27c93f")


def window(width: float, height: float, title: str, body: str, style: str = "") -> str:
    """Wrap SVG body markup in a macOS-style terminal window.

    Args:
        width: Canvas width in px.
        height: Canvas height in px.
        title: Text centered in the title bar.
        body: Inner SVG markup drawn on top of the window.
        style: Optional CSS placed in a <style> element.

    Returns:
        A complete standalone SVG document.
    """
    lights = "".join(
        f'<circle cx="{20 + i * 16}" cy="{TITLEBAR_H / 2}" r="5" fill="{color}"/>' for i, color in enumerate(_LIGHTS)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}" height="{height:g}" '
        f'viewBox="0 0 {width:g} {height:g}" font-family="{MONO}">'
        + (f"<style>{style}</style>" if style else "")
        + '<defs><linearGradient id="win-bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG_TOP}"/><stop offset="1" stop-color="{BG_BOTTOM}"/>'
        "</linearGradient></defs>"
        f'<rect width="{width:g}" height="{height:g}" rx="12" fill="url(#win-bg)"/>'
        f'<rect x="0.5" y="0.5" width="{width - 1:g}" height="{height - 1:g}" rx="12" '
        f'fill="none" stroke="{FRAME}"/>'
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{width:g}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>'
        + lights
        + f'<text x="{width / 2:g}" y="{TITLEBAR_H / 2 + 4}" fill="{MUTED}" font-size="12" '
        f'text-anchor="middle">{escape(title)}</text>' + body + "</svg>"
    )
