"""World map download and synthetic fallback generation."""

from __future__ import annotations

import io
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None

MAP_URL = "https://upload.wikimedia.org/wikipedia/commons/f/f2/Large_World_Map_bright.jpg"


def generate_world_map(output_path: Path | str, width: int = 1600, height: int = 800) -> Image.Image:
    """Download world map from Wikimedia or generate a synthetic fallback."""
    output_path = Path(output_path)
    try:
        print("[*] Downloading requested map from Wikimedia...")
        req = urllib.request.Request(MAP_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            img_data = response.read()
        img = Image.open(io.BytesIO(img_data))
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "JPEG", quality=95)
        print("[OK] Downloaded and saved world map")
        return img
    except Exception as exc:
        print(f"[ERROR] Could not download map: {exc}")
        print("[INFO] Falling back to synthetic map generation")
        return generate_synthetic_map(output_path, width, height)


def generate_synthetic_map(output_path: Path | str, width: int = 1600, height: int = 800) -> Image.Image:
    """Fallback synthetic map when download fails."""
    output_path = Path(output_path)
    img = Image.new("RGB", (width, height), color=(25, 85, 150))
    draw = ImageDraw.Draw(img, "RGBA")

    forest_green = (34, 93, 34)
    leaf_green = (76, 153, 0)
    tan = (210, 180, 100)
    light_green = (144, 193, 82)

    def latlon_to_pixel(lat: float, lon: float) -> tuple[int, int]:
        x = int((lon + 180) / 360.0 * width)
        y = int((height / 2) - (lat / 90.0) * (height / 2))
        return x, y

    continents = [
        [
            (70, -130), (75, -95), (60, -60), (45, -50), (40, -75), (25, -80),
            (20, -85), (20, -110), (35, -120), (50, -125), (70, -130),
        ],
        [
            (15, -80), (10, -60), (0, -55), (-5, -40), (-15, -60), (-30, -65),
            (-45, -72), (-30, -75), (-10, -75), (5, -75), (15, -80),
        ],
        [(82, -40), (80, -15), (60, -10), (59, -40), (82, -40)],
        [
            (71, -10), (70, 20), (60, 30), (55, 35), (50, 35), (45, 25),
            (40, 20), (40, 5), (42, -5), (45, -10), (50, -5), (55, -3),
            (60, 5), (71, -10),
        ],
        [
            (38, -5), (35, 5), (35, 15), (30, 25), (20, 35), (10, 40), (5, 35),
            (0, 30), (-5, 25), (-10, 20), (-20, 25), (-30, 20), (-35, 25),
            (-25, 35), (-15, 40), (-5, 35), (5, 30), (10, 15), (20, 5),
            (35, 0), (38, -5),
        ],
        [
            (72, 40), (75, 100), (72, 160), (65, 180), (55, 160), (50, 140),
            (45, 135), (30, 120), (25, 115), (15, 105), (8, 100), (5, 95),
            (10, 90), (15, 75), (25, 70), (35, 70), (45, 75), (50, 85),
            (55, 95), (60, 105), (72, 40),
        ],
        [
            (-10, 113), (-12, 125), (-20, 150), (-30, 155), (-35, 150),
            (-37, 140), (-32, 115), (-20, 113), (-10, 113),
        ],
    ]
    fills = [leaf_green, forest_green, light_green, leaf_green, tan, leaf_green, tan]

    for polygon, fill in zip(continents, fills):
        draw.polygon([latlon_to_pixel(lat, lon) for lat, lon in polygon], fill=fill)

    draw.ellipse([latlon_to_pixel(-34, 165), latlon_to_pixel(-48, 178)], fill=light_green)
    draw.rectangle([(0, int(height * 0.85)), (width, height)], fill=(200, 200, 200))

    line_color = (50, 80, 120, 60)
    for lat in range(-90, 91, 15):
        y = int((height / 2) - (lat / 90.0) * (height / 2))
        draw.line([(0, y), (width, y)], fill=line_color, width=1)
    for lon in range(-180, 180, 15):
        x = int((lon + 180) / 360.0 * width)
        draw.line([(x, 0), (x, height)], fill=line_color, width=1)

    equator_y = height // 2
    pm_x = width // 2
    draw.line([(0, equator_y), (width, equator_y)], fill=(100, 200, 255), width=2)
    draw.line([(pm_x, 0), (pm_x, height)], fill=(100, 200, 255), width=2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    print(f"[OK] Generated synthetic map: {width}x{height} pixels")
    return img
