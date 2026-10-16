"""
Build PWA brand assets from branding/sha-pay-logo.webp.

Run (needs Pillow):  python scripts/make_brand_assets.py
Output: frontend/icons/{logo.png, icon-192.png, icon-512.png, icon-maskable-512.png, favicon-32.png}
The logo's white background is multiplied onto the app's Natural Cream (#F7F5E8)
so it sits flush on the cream header and icon tiles.
"""

from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "branding" / "sha-pay-logo.webp"
OUT = ROOT / "frontend" / "icons"
CREAM = (247, 245, 232)


def to_cream(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    return ImageChops.multiply(rgb, Image.new("RGB", rgb.size, CREAM))


def content_bbox(img: Image.Image, x_max=None, thresh=240):
    """Bounding box of non-white pixels (optionally only columns < x_max)."""
    rgb = img.convert("RGB")
    if x_max:
        rgb = rgb.crop((0, 0, x_max, rgb.height))
    mask = rgb.point(lambda v: 255 if v < thresh else 0).convert("L")
    return mask.point(lambda v: 255 if v else 0).getbbox()


def square_icon(mark: Image.Image, size: int, pad_ratio: float) -> Image.Image:
    canvas = Image.new("RGB", (size, size), CREAM)
    inner = int(size * (1 - 2 * pad_ratio))
    m = mark.copy()
    m.thumbnail((inner, inner), Image.LANCZOS)
    canvas.paste(m, ((size - m.width) // 2, (size - m.height) // 2))
    return canvas


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    full = Image.open(SRC).convert("RGBA")
    # Flatten onto white first so transparent pixels don't turn black.
    flat = Image.new("RGBA", full.size, (255, 255, 255, 255))
    flat.alpha_composite(full)

    # Full logo (header): trim whitespace, keep ~6px breathing room.
    l, t, r, b = content_bbox(flat)
    logo = flat.crop((max(l - 6, 0), max(t - 6, 0), r + 6, b + 6))
    logo = to_cream(logo)
    logo.thumbnail((640, 320), Image.LANCZOS)
    logo.save(OUT / "logo.png", optimize=True)

    # Kiwi mark only (left of the wordmark, which starts ~x=495 of 1536).
    ml, mt, mr, mb = content_bbox(flat, x_max=int(flat.width * 0.32))
    mark = to_cream(flat.crop((ml, mt, mr, mb)))

    square_icon(mark, 192, 0.10).save(OUT / "icon-192.png", optimize=True)
    square_icon(mark, 512, 0.10).save(OUT / "icon-512.png", optimize=True)
    # Maskable: keep the mark inside the central 80% safe zone.
    square_icon(mark, 512, 0.20).save(OUT / "icon-maskable-512.png", optimize=True)
    square_icon(mark, 32, 0.04).save(OUT / "favicon-32.png", optimize=True)
    print("Wrote assets to", OUT)


if __name__ == "__main__":
    main()
