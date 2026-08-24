#!/usr/bin/env python3
"""Compose docs/social-preview.png -- the GitHub link-preview / LinkedIn card.

This is a LOCAL, ONE-SHOT generator, not part of CI. It loads TrueType fonts
by absolute path from C:\\Windows\\Fonts, so it only works on Windows and is
not portable to the CI runner. Run it by hand whenever the card's copy needs
to change, then commit the resulting PNG -- CI never regenerates it.

Rendering approach: a headless-browser screenshot pipeline was ruled out for
this environment (no working browser compositor, and cairosvg / ImageMagick /
Inkscape / rsvg-convert are all unavailable), so the card is drawn directly
with Pillow instead.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 640
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "social-preview.png"

FONTS_DIR = Path(r"C:\Windows\Fonts")

# Candidates in preference order; the first that loads wins. Matches the
# palette and typeface family used in docs/screenshots/*.svg.
REGULAR_CANDIDATES = ["segoeui.ttf", "arial.ttf"]
BOLD_CANDIDATES = ["segoeuib.ttf", "arialbd.ttf"]

# Palette matches docs/screenshots/provider-comparison.svg and the card
# accent colours on the install site, so all three read as one system.
COLOR_BACKGROUND = (255, 255, 255)
COLOR_ACCENT = (46, 90, 172)  # #2E5AAC (AdGuard)
COLOR_TITLE = (28, 28, 30)  # #1C1C1E
COLOR_MUTED = (95, 99, 104)  # #5F6368
COLOR_RULE = (229, 229, 234)  # #E5E5EA

PROJECT_NAME = "Encrypted DNS Profiles"
STRAPLINE = "Ad blocking, malware and phishing protection, and family safety \u2014 for iOS, iPadOS, macOS and Android"
FOOTER_LINE = "16 ready-to-install profiles \u00b7 DoH and DoT"

# (name, colour) pairs, each matching that provider's card accent on the
# install site and its dot colour in the comparison graphic.
PROVIDERS = [
    ("AdGuard", (46, 90, 172)),  # #2E5AAC
    ("ControlD", (0, 184, 169)),  # #00B8A9
    ("Cloudflare", (246, 130, 31)),  # #F6821F
    ("CleanBrowsing", (47, 168, 79)),  # #2FA84F
]
PROVIDER_SEPARATOR = "   \u00b7   "


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    last_error: Exception | None = None
    for name in candidates:
        path = FONTS_DIR / name
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size)
        except OSError as exc:  # pragma: no cover - depends on local fonts
            last_error = exc
            continue
    raise RuntimeError(
        f"none of the candidate fonts {candidates} could be loaded from {FONTS_DIR}"
    ) from last_error


def _draw_providers_line(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
) -> int:
    """Draw each provider name in its own accent colour, grey dots between.

    Returns the y-coordinate of the line's bottom edge.
    """
    cursor = x
    bottom = y
    for index, (name, colour) in enumerate(PROVIDERS):
        if index > 0:
            draw.text((cursor, y), PROVIDER_SEPARATOR, font=font, fill=COLOR_MUTED)
            cursor = draw.textbbox((cursor, y), PROVIDER_SEPARATOR, font=font)[2]
        draw.text((cursor, y), name, font=font, fill=colour)
        bbox = draw.textbbox((cursor, y), name, font=font)
        cursor = bbox[2]
        bottom = max(bottom, bbox[3])
    return bottom


def _measure_providers_line(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
) -> int:
    """Measurement-only twin of ``_draw_providers_line``: same cursor walk,
    but using textbbox (which does not paint pixels) instead of text, so it
    is safe to call during the y=0 layout replay.
    """
    cursor = x
    bottom = y
    for index, (name, _colour) in enumerate(PROVIDERS):
        if index > 0:
            cursor = draw.textbbox((cursor, y), PROVIDER_SEPARATOR, font=font)[2]
        bbox = draw.textbbox((cursor, y), name, font=font)
        cursor = bbox[2]
        bottom = max(bottom, bbox[3])
    return bottom


def generate_social_preview(output_path: Path = OUTPUT_PATH) -> Path:
    image = Image.new("RGB", (WIDTH, HEIGHT), COLOR_BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = _load_font(BOLD_CANDIDATES, 76)
    strapline_font = _load_font(REGULAR_CANDIDATES, 32)
    providers_font = _load_font(BOLD_CANDIDATES, 27)
    footer_font = _load_font(REGULAR_CANDIDATES, 24)

    margin_left = 88
    content_right = WIDTH - 88

    # Left accent bar, matching the accent-blue callouts used in the SVG
    # mockups.
    draw.rectangle([0, 0, 14, HEIGHT], fill=COLOR_ACCENT)

    block_top, block_bottom = _measure_block_extent(
        draw, margin_left, content_right, title_font, strapline_font, providers_font, footer_font
    )
    y = (HEIGHT - (block_bottom - block_top)) // 2 - block_top

    draw.text((margin_left, y), PROJECT_NAME, font=title_font, fill=COLOR_TITLE)
    title_bbox = draw.textbbox((margin_left, y), PROJECT_NAME, font=title_font)
    y = title_bbox[3] + 34

    strapline_lines = _wrap_text(draw, STRAPLINE, strapline_font, content_right - margin_left)
    for line in strapline_lines:
        draw.text((margin_left, y), line, font=strapline_font, fill=COLOR_MUTED)
        line_bbox = draw.textbbox((margin_left, y), line, font=strapline_font)
        y = line_bbox[3] + 10
    y += 28

    draw.line([(margin_left, y), (content_right, y)], fill=COLOR_RULE, width=2)
    y += 40

    y = _draw_providers_line(draw, margin_left, y, providers_font) + 26

    draw.text((margin_left, y), FOOTER_LINE, font=footer_font, fill=COLOR_MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    return output_path


def _measure_block_extent(
    draw: ImageDraw.ImageDraw,
    margin_left: int,
    content_right: int,
    title_font: ImageFont.FreeTypeFont,
    strapline_font: ImageFont.FreeTypeFont,
    providers_font: ImageFont.FreeTypeFont,
    footer_font: ImageFont.FreeTypeFont,
) -> tuple[int, int]:
    """Replay the layout starting at y=0 to find its overall (top, bottom).

    Mirrors the positioning logic in ``generate_social_preview`` exactly, so
    the real render can be shifted as a block to sit vertically centered.
    """
    y = 0
    title_bbox = draw.textbbox((margin_left, y), PROJECT_NAME, font=title_font)
    top = title_bbox[1]
    y = title_bbox[3] + 34

    strapline_lines = _wrap_text(draw, STRAPLINE, strapline_font, content_right - margin_left)
    for line in strapline_lines:
        line_bbox = draw.textbbox((margin_left, y), line, font=strapline_font)
        y = line_bbox[3] + 10
    y += 28

    y += 2  # divider line
    y += 40

    y = _measure_providers_line(draw, margin_left, y, providers_font) + 26

    footer_bbox = draw.textbbox((margin_left, y), FOOTER_LINE, font=footer_font)
    bottom = footer_bbox[3]

    return top, bottom


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """Greedily wrap ``text`` at word boundaries to fit within ``max_width``."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


if __name__ == "__main__":
    path = generate_social_preview()
    print(f"wrote {path}")
