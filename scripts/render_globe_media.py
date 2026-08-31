from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FRAMES = ROOT / "assets" / "globe_frames"
GIF = ASSETS / "radiobird-globe-demo.gif"
MP4 = ASSETS / "radiobird-globe-demo.mp4"

SITES = [
    ("IREN Sweetwater", 32.47, -100.41, "high"),
    ("CoreWeave Lancaster", 40.04, -76.31, "watch"),
    ("xAI Memphis", 35.13, -90.05, "high"),
    ("Northern Virginia", 39.04, -77.49, "stable"),
    ("Lulea AI/HPC", 65.58, 22.15, "watch"),
    ("Dublin Ring", 53.35, -6.26, "watch"),
    ("Johor Corridor", 1.49, 103.76, "high"),
    ("Tokyo Bay", 35.68, 139.76, "stable"),
]

LAND = [
    [(72, -168), (58, -132), (50, -95), (27, -82), (17, -99), (25, -124), (49, -126), (62, -150)],
    [(13, -82), (-18, -78), (-54, -67), (-34, -52), (-10, -45), (8, -61)],
    [(70, -10), (58, 30), (35, 42), (12, 20), (6, -12), (36, -10)],
    [(35, 42), (58, 78), (52, 132), (20, 122), (6, 78), (12, 45)],
    [(31, -18), (5, 18), (-34, 22), (-35, 48), (4, 42), (20, 30)],
    [(8, 95), (-10, 118), (-38, 145), (-24, 155), (5, 132)],
    [(-12, 112), (-44, 114), (-39, 153), (-18, 151)],
]

COLORS = {
    "high": (255, 107, 107),
    "watch": (244, 201, 93),
    "stable": (118, 219, 139),
}


def font(size: int) -> ImageFont.ImageFont:
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    try:
        return ImageFont.truetype(paths[0], size)
    except OSError:
        return ImageFont.load_default()


def project(lat: float, lon: float, rotation: float, tilt: float, radius: float, center: tuple[int, int]):
    phi = math.radians(lat)
    lam = math.radians(lon) + rotation
    cos_phi = math.cos(phi)
    x = radius * cos_phi * math.sin(lam)
    y = radius * (math.sin(phi) * math.cos(tilt) - cos_phi * math.cos(lam) * math.sin(tilt))
    z = cos_phi * math.cos(lam) * math.cos(tilt) + math.sin(phi) * math.sin(tilt)
    return center[0] + x, center[1] - y, z


def visible_path(points, rotation: float, tilt: float, radius: float, center: tuple[int, int]):
    return [
        (x, y)
        for lat, lon in points
        for x, y, z in [project(lat, lon, rotation, tilt, radius, center)]
        if z > -0.08
    ]


def make_frame(index: int, total: int) -> Image.Image:
    width, height = 960, 640
    center = (340, 320)
    radius = 250
    rotation = -1.55 + (math.tau * index / total)
    tilt = -0.28

    img = Image.new("RGB", (width, height), (7, 16, 19))
    draw = ImageDraw.Draw(img, "RGBA")

    for y in range(height):
        t = y / height
        color = (
            int(7 + 9 * t),
            int(16 + 18 * t),
            int(19 + 23 * t),
        )
        draw.line([(0, y), (width, y)], fill=color)

    for x in range(0, width, 48):
        draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 12))
    for y in range(0, height, 48):
        draw.line([(0, y), (width, y)], fill=(255, 255, 255, 12))

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse(
        [center[0] - radius - 8, center[1] - radius - 8, center[0] + radius + 8, center[1] + radius + 8],
        fill=(0, 0, 0, 180),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    img = Image.alpha_composite(img.convert("RGBA"), shadow)
    draw = ImageDraw.Draw(img, "RGBA")

    draw.ellipse(
        [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius],
        fill=(18, 57, 74),
        outline=(117, 231, 220, 120),
        width=3,
    )

    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse(
        [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius],
        fill=255,
    )

    land_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    land_draw = ImageDraw.Draw(land_layer, "RGBA")
    for mass in LAND:
        pts = visible_path(mass, rotation, tilt, radius, center)
        if len(pts) >= 3:
            land_draw.polygon(pts, fill=(61, 118, 84, 190), outline=(134, 190, 151, 95))
    img = Image.composite(Image.alpha_composite(img, land_layer), img, mask)
    draw = ImageDraw.Draw(img, "RGBA")

    for lat in range(-60, 61, 30):
        pts = visible_path([(lat, lon) for lon in range(-180, 181, 4)], rotation, tilt, radius, center)
        if len(pts) > 1:
            draw.line(pts, fill=(191, 230, 225, 35), width=1)
    for lon in range(-180, 181, 30):
        pts = visible_path([(lat, lon) for lat in range(-80, 81, 4)], rotation, tilt, radius, center)
        if len(pts) > 1:
            draw.line(pts, fill=(191, 230, 225, 35), width=1)

    for name, lat, lon, status in sorted(SITES, key=lambda site: project(site[1], site[2], rotation, tilt, radius, center)[2]):
        x, y, z = project(lat, lon, rotation, tilt, radius, center)
        if z <= -0.06:
            continue
        color = COLORS[status]
        pulse = 9 + math.sin(index / 4) * 2 if status == "high" else 5
        draw.ellipse([x - pulse, y - pulse, x + pulse, y + pulse], fill=(*color, 55))
        draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(*color, 255), outline=(255, 255, 255, 230), width=2)
        if status == "high":
            draw.text((x + 11, y - 12), name, fill=(238, 247, 244, 230), font=font(14))

    draw.text((640, 82), "RadioBird Watchtower", fill=(61, 217, 197), font=font(20))
    draw.text((640, 116), "Neocloud Physical", fill=(238, 247, 244), font=font(34))
    draw.text((640, 154), "Progress Monitor", fill=(238, 247, 244), font=font(34))
    draw.text((640, 210), "Hotspots: all tracked neoclouds,", fill=(158, 183, 180), font=font(18))
    draw.text((640, 236), "hyperscalers, AI/HPC, colo,", fill=(158, 183, 180), font=font(18))
    draw.text((640, 262), "and power-adjacent sites.", fill=(158, 183, 180), font=font(18))

    legend_y = 414
    for label, key in [("High attention", "high"), ("Watch", "watch"), ("Baseline", "stable")]:
        color = COLORS[key]
        draw.ellipse([640, legend_y, 654, legend_y + 14], fill=(*color, 255))
        draw.text((666, legend_y - 3), label, fill=(238, 247, 244), font=font(17))
        legend_y += 34

    draw.rounded_rectangle([632, 548, 910, 590], radius=6, outline=(151, 190, 198, 70), fill=(12, 24, 29, 205))
    draw.text((650, 560), "Rendered from repo watchlist geometry", fill=(158, 183, 180), font=font(15))
    return img.convert("RGB")


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    FRAMES.mkdir(exist_ok=True)
    total = 72
    frames = []
    for i in range(total):
        frame = make_frame(i, total)
        frame_path = FRAMES / f"frame-{i:04d}.png"
        frame.save(frame_path)
        frames.append(frame)

    frames[0].save(GIF, save_all=True, append_images=frames[1:], duration=70, loop=0, optimize=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            "15",
            "-i",
            str(FRAMES / "frame-%04d.png"),
            "-pix_fmt",
            "yuv420p",
            str(MP4),
        ],
        check=True,
    )
    print(f"Wrote {GIF}")
    print(f"Wrote {MP4}")


if __name__ == "__main__":
    main()
