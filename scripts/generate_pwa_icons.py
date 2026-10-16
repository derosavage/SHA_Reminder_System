#!/usr/bin/env python3
"""
Generate PWA app icons for the SHA Reminder frontend.
Pure standard library (no Pillow needed) - writes valid PNG files.

Design: green rounded square + white payment card + M-Pesa-style coin.
Run: python generate_pwa_icons.py
Output: ../frontend/icons/{icon-192.png, icon-512.png, icon-maskable-512.png, favicon-32.png}
"""

import os
import struct
import zlib

GREEN = (0, 184, 67, 255)
WHITE = (255, 255, 255, 255)


def write_png(path, size, px):
    """Write a list-of-rows RGBA pixel buffer as a PNG file."""
    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = b"".join(
        b"\x00" + b"".join(struct.pack("4B", *c) for c in row) for row in px
    )
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def in_rounded_rect(x, y, x0, y0, x1, y1, r):
    """True if (x, y) is inside an axis-aligned rounded rectangle."""
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    nx = min(max(x, x0 + r), x1 - r)
    ny = min(max(y, y0 + r), y1 - r)
    return (x - nx) ** 2 + (y - ny) ** 2 <= r * r


def in_circle(x, y, cx, cy, r):
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def render(size, maskable=False):
    """Render one icon frame. Scaling done from a 512x512 design space."""
    s = size / 512.0
    px = []
    for yy in range(size):
        row = []
        for xx in range(size):
            # Background layer
            if maskable:
                color = GREEN  # full-bleed for maskable safe zone
            elif in_rounded_rect(xx, yy, 24 * s, 24 * s, 488 * s, 488 * s, 100 * s):
                color = GREEN
            else:
                row.append((0, 0, 0, 0))
                continue

            # M-Pesa-style coin (white disc with green core)
            if in_circle(xx, yy, 256 * s, 168 * s, 84 * s):
                color = WHITE
            if in_circle(xx, yy, 256 * s, 168 * s, 60 * s):
                color = GREEN

            # Payment card
            if in_rounded_rect(xx, yy, 96 * s, 216 * s, 416 * s, 368 * s, 40 * s):
                color = WHITE

            # Card detail lines (suggest account/reference text)
            if in_rounded_rect(xx, yy, 116 * s, 238 * s, 396 * s, 254 * s, 8 * s) or in_rounded_rect(
                xx, yy, 116 * s, 330 * s, 396 * s, 346 * s, 8 * s
            ):
                color = GREEN

            row.append(color)
        px.append(row)
    return px


def main():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "icons")
    out = {
        "icon-192.png": render(192, maskable=False),
        "icon-512.png": render(512, maskable=False),
        "icon-maskable-512.png": render(512, maskable=True),
        "favicon-32.png": render(32, maskable=False),
    }
    for name, px in out.items():
        size = len(px)
        path = os.path.normpath(os.path.join(base, name))
        write_png(path, size, px)
        print(f"  Wrote {path} ({size}x{size})")


if __name__ == "__main__":
    main()