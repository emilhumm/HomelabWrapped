"""Draw Homelab Wrapped's brand icon: a gift box on the story's gradient.

Usage (needs Pillow): python scripts/make_icon.py custom_components/homelab_wrapped/brand
Home Assistant (2026.10) serves a custom integration's icon from its brand/ folder.
"""

from itertools import pairwise
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageDraw

S = 1024  # drawn large, scaled down for smooth edges


def gradient(size: int) -> Image.Image:
    """Diagonal: indigo -> violet -> pink, as on the Play button."""
    stops = [(0.0, (0x31, 0x2E, 0x81)), (0.55, (0x6D, 0x28, 0xD9)), (1.0, (0xBE, 0x18, 0x5D))]
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            for (t0, c0), (t1, c1) in pairwise(stops):
                if t <= t1:
                    k = (t - t0) / (t1 - t0)
                    px[x, y] = tuple(round(a + (b - a) * k) for a, b in zip(c0, c1, strict=True))
                    break
    return img


def icon() -> Image.Image:
    background = gradient(S).convert("RGBA")
    badge = Image.new("L", (S, S), 0)
    ImageDraw.Draw(badge).rounded_rectangle((0, 0, S - 1, S - 1), radius=S // 5, fill=255)

    gift = Image.new("L", (S, S), 0)
    draw = ImageDraw.Draw(gift)
    draw.rounded_rectangle((250, 470, 774, 820), radius=40, fill=255)  # box
    draw.rounded_rectangle((210, 360, 814, 470), radius=36, fill=255)  # lid
    w = 30  # the bow: two loops
    draw.ellipse((300, 180, 512, 370), outline=255, width=2 * w)
    draw.ellipse((512, 180, 724, 370), outline=255, width=2 * w)
    # Cut the ribbon and the gap under the lid out of the white, so the gradient shows.
    cut = Image.new("L", (S, S), 0)
    cuts = ImageDraw.Draw(cut)
    cuts.rectangle((482, 360, 542, 820), fill=255)
    cuts.rectangle((210, 470, 814, 500), fill=255)
    gift = ImageChops.subtract(gift, cut)
    # Keep the loops above the lid only.
    above = Image.new("L", (S, S), 0)
    ImageDraw.Draw(above).rectangle((0, 0, S, 360), fill=255)
    loops = ImageChops.multiply(gift, above)
    body = ImageChops.subtract(gift, above)
    gift = ImageChops.lighter(loops, body)

    white = Image.new("RGBA", (S, S), (255, 255, 255, 255))
    background.paste(white, (0, 0), gift)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(background, (0, 0), badge)
    return out


def main(folder: str) -> None:
    big = icon()
    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    big.resize((512, 512), Image.LANCZOS).save(target / "icon@2x.png", optimize=True)
    big.resize((256, 256), Image.LANCZOS).save(target / "icon.png", optimize=True)


if __name__ == "__main__":
    main(sys.argv[1])
