#!/usr/bin/env python3
"""Normalize the source avatar into a clean square photo for ASCII conversion.

Usage:
    python scripts/prep_photo.py [src] [dst]

Defaults: assets/dp-src.png -> assets/dp.png

Steps: square center-crop, grayscale-friendly contrast boost, light sharpen.
The output is what make_ascii_svg.py reads.
"""
import sys
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

SRC = sys.argv[1] if len(sys.argv) > 1 else "assets/dp-src.png"
DST = sys.argv[2] if len(sys.argv) > 2 else "assets/dp.png"

TARGET = 512  # work size; make_ascii downsamples from here


def square_crop(im: Image.Image) -> Image.Image:
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return im.crop((left, top, left + side, top + side))


def main() -> None:
    im = Image.open(SRC).convert("RGB")
    im = square_crop(im)
    im = im.resize((TARGET, TARGET), Image.LANCZOS)

    # Auto-contrast spreads the tonal range so the face reads well in ASCII.
    im = ImageOps.autocontrast(im, cutoff=1)
    im = ImageEnhance.Contrast(im).enhance(1.15)
    im = ImageEnhance.Color(im).enhance(1.1)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))

    im.save(DST)
    print(f"prep_photo: wrote {DST} ({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
