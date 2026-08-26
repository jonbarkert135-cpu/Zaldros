#!/usr/bin/env python3
"""Rank UI fonts against the real Windows 11 capture, instead of picking one by taste.

The reference screenshot in assets/refs is a Russian Windows 11 desktop, so it carries genuine
Segoe UI Cyrillic at UI sizes. This tool crops two known strings from it, renders the same string
with each candidate font, scales the rendering to the reference's ink height and reports the
normalised pixel difference plus the width ratio.

    python tools/visual/font_match.py                       # rank the shipped font
    python tools/visual/font_match.py extra/Inter.ttf ...    # rank candidates against it

Numbers are comparative, not absolute: hinting and subpixel rendering differ, so even a perfect
match never reaches 0 %. What matters is the ranking, and that the shipped font wins it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "assets" / "refs" / "win11_start_reference.png"
SHIPPED = ROOT / "assets" / "fonts" / "pt-sans"

# (crop box in reference pixels, the string it contains, whether Windows draws it semibold)
SAMPLES = (
    ((648, 350, 1016, 377), "Чтобы начать поиск, введите запрос здесь", False),
    ((630, 431, 783, 459), "Закрепленные", True),
)


def _tight(array: np.ndarray, threshold: float = 0.45) -> np.ndarray:
    """Crop to the inked box so two renderings can be compared without their margins."""
    mask = array > threshold
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        raise ValueError("no ink found in sample")
    return array[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _reference(box: tuple[int, int, int, int]) -> np.ndarray:
    image = Image.open(REFERENCE).convert("L").crop(box)
    array = np.asarray(image, dtype=float)
    array = (array - array.min()) / max(array.max() - array.min(), 1e-6)
    return _tight(array)


def _render(font_path: Path, text: str, size: int) -> np.ndarray:
    font = ImageFont.truetype(str(font_path), size)
    canvas = Image.new("L", (2000, 160), 0)
    ImageDraw.Draw(canvas).text((20, 20), text, 255, font=font)
    return _tight(np.asarray(canvas, dtype=float) / 255)


def compare(font_path: Path, box, text: str) -> tuple[float, float]:
    """Best (pixel difference, width ratio) over plausible pixel sizes."""
    reference = _reference(box)
    height, width = reference.shape
    best = (float("inf"), 0.0)
    for size in range(12, 32):
        rendered = _render(font_path, text, size)
        scaled_width = max(1, int(rendered.shape[1] * height / rendered.shape[0]))
        scaled = np.asarray(
            Image.fromarray((rendered * 255).astype("uint8")).resize((scaled_width, height)),
            dtype=float) / 255
        overlap = min(width, scaled.shape[1])
        difference = (np.abs(scaled[:, :overlap] - reference[:, :overlap]).sum()
                      / reference[:, :overlap].sum())
        ratio = scaled.shape[1] / width
        if difference + abs(ratio - 1) < best[0] + abs(best[1] - 1):
            best = (difference, ratio)
    return best


def faces(path: Path) -> dict[str, Path]:
    if path.is_file():
        return {path.stem: path}
    return {ttf.stem: ttf for ttf in sorted(path.glob("*.ttf"))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", nargs="*", type=Path,
                        help="font files or directories; defaults to the shipped family")
    args = parser.parse_args(argv)
    candidates = args.candidates or [SHIPPED]
    if not REFERENCE.exists():
        print(f"missing reference capture: {REFERENCE}", file=sys.stderr)
        return 2

    rows = []
    for candidate in candidates:
        for name, ttf in faces(candidate).items():
            for box, text, semibold in SAMPLES:
                bold_face = "bold" in name.lower() or "semibold" in name.lower()
                if semibold != bold_face:
                    continue
                difference, ratio = compare(ttf, box, text)
                rows.append((difference, name, "semibold" if semibold else "regular", ratio))
    for difference, name, weight, ratio in sorted(rows):
        print(f"{name:24s} {weight:9s} diff {difference * 100:5.1f}%  width vs Segoe {ratio:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
