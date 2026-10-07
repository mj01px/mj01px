"""Isolate the subject of the profile photo for a clean ASCII portrait.

Runs locally only (heavy deps: see requirements-portrait.txt); the daily
workflow never regenerates the portrait.

Steps: cut the background out, smooth skin texture while keeping edges,
stretch tones over the subject only, ink fine dark features (eyes, ear, lips),
paste onto white and square-crop around the subject. White becomes blank space in the ASCII, so only the person prints.

Usage:
    python scripts/portrait_prep.py [photo] [output.png]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove

ROOT = Path(__file__).resolve().parent.parent

TONE_LOW_PCT = 2  # subject percentile mapped to black
TONE_HIGH_PCT = 97  # subject percentile mapped to white
MARGIN = 40  # px of white around the subject in the square crop
LINE_WEIGHT = float(os.environ.get("LINE_WEIGHT", "0.6"))  # how hard fine dark features are inked


def isolate(photo: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    """Return (grayscale, alpha) arrays with the background cut out."""
    cut = remove(photo.convert("RGBA"))
    rgba = np.array(cut)
    gray = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY)
    return gray, rgba[:, :, 3]


def stretch(gray: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    smooth = gray
    for _ in range(2):
        smooth = cv2.bilateralFilter(smooth, 9, 35, 9)
    lo, hi = np.percentile(smooth[alpha > 128], [TONE_LOW_PCT, TONE_HIGH_PCT])
    tone = np.clip((smooth.astype(np.float32) - lo) / max(hi - lo, 1.0), 0, 1)
    # Eyes, ear and lips are thin dark strokes that averaging down to ASCII
    # resolution washes out; a difference of Gaussians finds them so they can
    # be pushed darker.
    fine = cv2.GaussianBlur(smooth, (0, 0), 1.5).astype(np.float32)
    coarse = cv2.GaussianBlur(smooth, (0, 0), 6).astype(np.float32)
    ridges = np.clip((coarse - fine) / 40.0, 0, 1)
    return np.clip(tone - LINE_WEIGHT * ridges, 0, 1)


def on_white_square(tone: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    mask = cv2.GaussianBlur(alpha.astype(np.float32) / 255.0, (0, 0), 1.0)
    img = tone * 255.0 * mask + 255.0 * (1.0 - mask)

    ys, xs = np.where(alpha > 20)
    side = max(xs.max() - xs.min(), ys.max() - ys.min()) + 2 * MARGIN
    cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
    canvas = np.full((side, side), 255, np.uint8)
    x0, y0 = cx - side // 2, cy - side // 2
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + side, img.shape[1]), min(y0 + side, img.shape[0])
    canvas[sy0 - y0 : sy1 - y0, sx0 - x0 : sx1 - x0] = img[sy0:sy1, sx0:sx1].astype(np.uint8)
    return canvas


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "source-photo.png"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "source-prepped.png"
    gray, alpha = isolate(Image.open(src))
    Image.fromarray(on_white_square(stretch(gray, alpha), alpha), mode="L").save(dst)
    print(f"portrait_prep: wrote {dst.name}")


if __name__ == "__main__":
    main()
