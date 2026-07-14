#!/usr/bin/env python3
"""
ascii_terminal.py — Turn any image into ASCII art that types itself out
like a terminal, saved as a self-contained animated SVG.

Usage:
    Drop an image into this folder and run with no arguments:
        python3 ascii_terminal.py
    It auto-detects the newest image in the folder, converts it to ASCII,
    and writes an animated .svg next to it. The SVG uses SMIL animation so
    it plays in a browser AND inside a GitHub README.

    Optional: pass an image path explicitly:
        python3 ascii_terminal.py path/to/photo.png

Dependencies: Pillow only.
"""

import sys
import os
import glob
from PIL import Image

# ----------------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------------
WIDTH = 100          # target width in characters (~100 wide)
CHAR_ASPECT = 0.52   # monospace glyphs are ~2x taller than wide
CONTRAST = 1.15      # >1 boosts contrast, <1 flattens it

# Bright -> blank, dark -> dense. This makes bright backgrounds wash out.
# First char is a plain space so highlights become clean empty space.
RAMP = " .'`^\",:;Il!i~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

# Terminal look
BG_COLOR = "#0d1117"     # dark background (GitHub dark)
FG_COLOR = "#c9d1d9"     # light monospace text
CURSOR_COLOR = "#3fb950" # green terminal cursor
FONT_SIZE = 12           # px
LINE_HEIGHT = 13         # px per row
CHAR_WIDTH = 7.2         # px per glyph (monospace advance)
PAD = 16                 # px padding around the art
ROW_DURATION = 0.28      # seconds to type one row
PIXELS_LOOK_HOLD = 1.2   # seconds frozen at the end before it settles

IMAGE_EXTS = ("*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp",
              "*.tif", "*.tiff", "*.JPG", "*.JPEG", "*.PNG")


# ----------------------------------------------------------------------------
# Image -> ASCII
# ----------------------------------------------------------------------------
def image_to_ascii(path, width=WIDTH):
    from PIL import ImageOps, ImageEnhance

    img = Image.open(path).convert("L")  # grayscale luminance
    # Spread the tonal range so faces don't turn to mush and bright
    # backgrounds push all the way to white (-> blank space).
    img = ImageOps.autocontrast(img, cutoff=1)
    if CONTRAST != 1.0:
        img = ImageEnhance.Contrast(img).enhance(CONTRAST)

    w, h = img.size
    new_w = width
    new_h = max(1, int(width * (h / w) * CHAR_ASPECT))
    img = img.resize((new_w, new_h))

    px = img.load()
    n = len(RAMP) - 1
    rows = []
    for y in range(new_h):
        chars = []
        for x in range(new_w):
            lum = px[x, y]  # 0 = black, 255 = white
            # Bright areas -> start of ramp (space); dark -> dense glyphs
            idx = int((255 - lum) / 255 * n)
            chars.append(RAMP[idx])
        rows.append("".join(chars).rstrip())
    return rows


# ----------------------------------------------------------------------------
# ASCII -> animated SVG (SMIL, GitHub-README friendly)
# ----------------------------------------------------------------------------
def _xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def ascii_to_svg(rows, out_path):
    n_rows = len(rows)
    max_cols = max((len(r) for r in rows), default=1)
    art_w = max_cols * CHAR_WIDTH
    art_h = n_rows * LINE_HEIGHT
    svg_w = int(art_w + PAD * 2)
    svg_h = int(art_h + PAD * 2)

    total = n_rows * ROW_DURATION + PIXELS_LOOK_HOLD  # full loop length

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" '
        f'height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" '
        f'font-family="monospace">'
    )
    parts.append(f'<rect width="100%" height="100%" fill="{BG_COLOR}"/>')
    parts.append(
        f'<style>text{{font-family:Menlo,Consolas,"DejaVu Sans Mono",'
        f'monospace;font-size:{FONT_SIZE}px;white-space:pre;'
        f'dominant-baseline:hanging;}}</style>'
    )

    for i, row in enumerate(rows):
        y = PAD + i * LINE_HEIGHT
        start = i * ROW_DURATION
        row_len = max(len(row), 1)
        row_px = row_len * CHAR_WIDTH

        # Clip rectangle that sweeps left->right to reveal the row.
        clip_id = f"c{i}"
        parts.append(f'<clipPath id="{clip_id}">')
        parts.append(
            f'<rect x="{PAD}" y="{y}" width="0" height="{LINE_HEIGHT}">'
            f'<animate attributeName="width" from="0" to="{row_px:.1f}" '
            f'begin="{start:.3f}s" dur="{ROW_DURATION:.3f}s" '
            f'fill="freeze" calcMode="linear"/>'
            f'</rect>'
        )
        parts.append('</clipPath>')

        # The row text, revealed through its clip.
        parts.append(
            f'<text x="{PAD}" y="{y}" fill="{FG_COLOR}" '
            f'clip-path="url(#{clip_id})" '
            f'xml:space="preserve">{_xml_escape(row)}</text>'
        )

        # Block cursor that sweeps across this row while it types,
        # then vanishes when the row is done.
        parts.append(
            f'<rect y="{y}" width="{CHAR_WIDTH:.1f}" '
            f'height="{FONT_SIZE}" fill="{CURSOR_COLOR}" opacity="0">'
            f'<animate attributeName="x" from="{PAD}" '
            f'to="{PAD + row_px:.1f}" begin="{start:.3f}s" '
            f'dur="{ROW_DURATION:.3f}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.85" begin="{start:.3f}s"/>'
            f'<set attributeName="opacity" to="0" '
            f'begin="{start + ROW_DURATION:.3f}s"/>'
            f'</rect>'
        )

    parts.append('</svg>')

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return total


# ----------------------------------------------------------------------------
# Auto-detect the image to convert
# ----------------------------------------------------------------------------
def find_image(folder):
    candidates = []
    for pat in IMAGE_EXTS:
        candidates.extend(glob.glob(os.path.join(folder, pat)))
    # Ignore anything we might have generated
    candidates = [c for c in set(candidates) if not c.lower().endswith(".svg")]
    if not candidates:
        return None
    # Newest file wins (the one you just dropped in)
    return max(candidates, key=os.path.getmtime)


def main():
    folder = os.path.dirname(os.path.abspath(__file__))

    if len(sys.argv) > 1:
        img_path = os.path.abspath(sys.argv[1])
        if not os.path.exists(img_path):
            print(f"! Not found: {img_path}")
            sys.exit(1)
    else:
        img_path = find_image(folder)
        if not img_path:
            print("! No image found. Drop a .jpg/.png into this folder and "
                  "run again.")
            sys.exit(1)

    print(f"→ Reading {os.path.basename(img_path)}")
    rows = image_to_ascii(img_path)
    out_path = os.path.splitext(img_path)[0] + ".svg"
    duration = ascii_to_svg(rows, out_path)
    print(f"✓ Wrote {os.path.basename(out_path)} "
          f"({len(rows)} rows, ~{duration:.1f}s animation)")
    print(f"  Open it in a browser: open \"{out_path}\"")


if __name__ == "__main__":
    main()
