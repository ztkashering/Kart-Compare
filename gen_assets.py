"""
gen_assets.py — generates placeholder brand images (favicon, PWA icons, and
the social-share preview image) so the site has something real in place
before the actual logo design phase.

PLAIN-ENGLISH NOTE: these are a simple "KC" monogram on the brand color,
not a real logo — that's intentionally still phase 2, as discussed. This
just makes sure nothing is blank/broken (browser tab icon, phone home-screen
icon, link preview image) in the meantime. Swap these files for the real
logo exports later; every other file references these same filenames, so
dropping in replacements with the same names is a complete swap.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).parent / "docs"
OUT.mkdir(exist_ok=True)

BRAND = (29, 63, 235)       # #1D3FEB
BRAND_DARK = (21, 48, 176)  # #1530B0
ACCENT = (6, 182, 212)      # #06B6D4
WHITE = (255, 255, 255)


def rounded_square(size, radius_ratio=0.24):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = int(size * radius_ratio)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BRAND)
    # small accent dot, top-right, echoes the logo's magnifying glass mark
    dot_r = size * 0.16
    cx, cy = size * 0.76, size * 0.28
    draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=ACCENT)
    return img, draw, r


def find_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def make_icon(size, path):
    img, draw, _ = rounded_square(size)
    font = find_font(int(size * 0.42))
    text = "KC"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1] - size * 0.03), text, font=font, fill=WHITE)
    img.save(path)
    print("wrote", path, img.size)


def make_favicon_ico(path):
    sizes = [16, 32, 48]
    imgs = []
    for s in sizes:
        img, draw, _ = rounded_square(s, radius_ratio=0.28)
        font = find_font(int(s * 0.5))
        text = "K"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((s - tw) / 2 - bbox[0], (s - th) / 2 - bbox[1]), text, font=font, fill=WHITE)
        imgs.append(img.convert("RGBA"))
    imgs[0].save(path, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[1:])
    print("wrote", path)


def make_og_image(path, brand_name, tagline, stat_text):
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BRAND)
    draw = ImageDraw.Draw(img)
    # diagonal darker band for depth
    draw.polygon([(0, H), (W, H), (W, H * 0.6), (0, H * 0.85)], fill=BRAND_DARK)

    # logo chip top-left
    chip = 90
    chip_img, chip_draw, _ = rounded_square(chip, radius_ratio=0.26)
    font_chip = find_font(int(chip * 0.4))
    bbox = chip_draw.textbbox((0, 0), "KC", font=font_chip)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    chip_draw.text(((chip - tw) / 2 - bbox[0], (chip - th) / 2 - bbox[1] - chip * 0.03), "KC", font=font_chip, fill=WHITE)
    img.paste(chip_img, (80, 70), chip_img)

    font_title = find_font(72)
    font_sub = find_font(34)
    font_stat = find_font(30)
    draw.text((80, 200), brand_name, font=font_title, fill=WHITE)
    draw.text((84, 300), tagline, font=font_sub, fill=(230, 230, 250))
    draw.text((84, 520), stat_text, font=font_stat, fill=ACCENT)

    img.save(path, quality=90)
    print("wrote", path, img.size)


make_icon(192, OUT / "icon-192.png")
make_icon(512, OUT / "icon-512.png")
make_icon(180, OUT / "apple-touch-icon.png")
make_favicon_ico(OUT / "favicon.ico")
make_og_image(
    OUT / "og-image.png",
    "Kart Compare",
    "Compare grocery deals across Lakewood.",
    "437 real deals  ·  6 stores  ·  updated regularly",
)
