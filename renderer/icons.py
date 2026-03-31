from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

try:
    import cairosvg
except ImportError:  # pragma: no cover - optional dependency
    cairosvg = None


ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons" / "weather"


def draw_weather_icon(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    size: int,
    icon_name: str,
    color: str,
    *,
    hardware_target: bool = False,
) -> None:
    asset = load_weather_icon_asset(icon_name, size, hardware_target=hardware_target)
    if asset is not None:
        image.paste(asset, (x, y), asset)
        return

    _draw_placeholder_icon(draw, x, y, size, icon_name, color)


def paste_weather_icon(
    image: Image.Image,
    x: int,
    y: int,
    size: int,
    icon_name: str,
    *,
    hardware_target: bool = False,
) -> bool:
    asset = load_weather_icon_asset(icon_name, size, hardware_target=hardware_target)
    if asset is None:
        return False
    image.paste(asset, (x, y), asset)
    return True

def load_weather_icon_asset(icon_name: str, size: int, *, hardware_target: bool = False) -> Image.Image | None:
    for extension in (".png", ".svg"):
        icon_path = ICON_DIR / f"{icon_name}{extension}"
        if not icon_path.exists():
            continue

        if extension == ".png":
            icon = Image.open(icon_path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            return _prepare_icon_asset(icon, hardware_target=hardware_target)

        if extension == ".svg" and cairosvg is not None:
            render_size = size * 3
            png_bytes = cairosvg.svg2png(url=str(icon_path), output_width=render_size, output_height=render_size)
            icon = Image.open(BytesIO(png_bytes)).convert("RGBA")
            icon = icon.resize((size, size), Image.Resampling.LANCZOS)
            return _prepare_icon_asset(icon, hardware_target=hardware_target)

    return None


def _prepare_icon_asset(icon: Image.Image, *, hardware_target: bool) -> Image.Image:
    if hardware_target:
        return _remap_icon_for_eink(icon)
    return icon.convert("RGBA")


def _remap_icon_for_eink(icon: Image.Image) -> Image.Image:
    dark = (0, 0, 0, 255)
    cloud_gray = (170, 178, 188, 255)
    yellow = (214, 168, 0, 255)
    blue = (44, 108, 192, 255)

    rgba = icon.convert("RGBA")
    pixels = []
    for red, green, blue_channel, alpha in rgba.getdata():
        if alpha < 56:
            pixels.append((0, 0, 0, 0))
            continue

        brightness = (red + green + blue_channel) / 3
        saturation = max(red, green, blue_channel) - min(red, green, blue_channel)

        if brightness > 210 and saturation < 42:
            pixels.append(cloud_gray)
        elif brightness > 160 and saturation < 30:
            pixels.append(cloud_gray)
        elif red > 150 and green > 110 and blue_channel < 120:
            pixels.append(yellow)
        elif blue_channel > red + 18 and blue_channel > green + 12:
            pixels.append(blue)
        elif brightness < 110:
            pixels.append(dark)
        elif saturation < 38:
            pixels.append(cloud_gray)
        else:
            pixels.append(dark)

    remapped = Image.new("RGBA", rgba.size)
    remapped.putdata(pixels)
    alpha = remapped.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    alpha = alpha.filter(ImageFilter.MedianFilter(size=3))
    remapped.putalpha(alpha)
    return remapped


def _draw_placeholder_icon(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, condition: str, color: str) -> None:
    center_x = x + size // 2
    center_y = y + size // 2

    if condition in {"clear-day", "clear-night"}:
        radius = size // 5
        draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline=color, width=2)
        if condition == "clear-day":
            for delta_x, delta_y in ((0, -14), (10, -10), (14, 0), (10, 10), (0, 14), (-10, 10), (-14, 0), (-10, -10)):
                draw.line((center_x, center_y, center_x + delta_x, center_y + delta_y), fill=color, width=2)
        else:
            draw.arc((center_x - 10, center_y - 10, center_x + 8, center_y + 8), start=60, end=300, fill=color, width=2)
        return

    if condition in {"partlycloudy-day", "partlycloudy-night"}:
        draw.ellipse((x + 6, y + 2, x + 22, y + 18), outline=color, width=2)
        _draw_cloud(draw, x + 12, y + 14, color)
        return

    if condition == "rain":
        _draw_cloud(draw, x + 7, y + 10, color)
        for offset in (10, 20, 30):
            draw.line((x + offset, y + 30, x + offset - 4, y + 38), fill=color, width=2)
        return

    if condition in {"showers-day", "showers-night"}:
        _draw_cloud(draw, x + 7, y + 10, color)
        for offset in (14, 24):
            draw.line((x + offset, y + 30, x + offset - 3, y + 37), fill=color, width=2)
        return

    if condition == "snow":
        _draw_cloud(draw, x + 7, y + 10, color)
        for snow_x, snow_y in ((x + 12, y + 34), (x + 22, y + 34), (x + 32, y + 34)):
            draw.line((snow_x - 3, snow_y, snow_x + 3, snow_y), fill=color, width=2)
            draw.line((snow_x, snow_y - 3, snow_x, snow_y + 3), fill=color, width=2)
        return

    if condition == "sleet":
        _draw_cloud(draw, x + 7, y + 10, color)
        draw.line((x + 16, y + 30, x + 12, y + 36), fill=color, width=2)
        draw.line((x + 26, y + 30, x + 26, y + 36), fill=color, width=2)
        draw.line((x + 34, y + 30, x + 30, y + 36), fill=color, width=2)
        return

    if condition == "thunderstorm":
        _draw_cloud(draw, x + 7, y + 10, color)
        draw.line((x + 20, y + 28, x + 14, y + 40), fill=color, width=2)
        draw.line((x + 14, y + 40, x + 24, y + 40), fill=color, width=2)
        draw.line((x + 24, y + 40, x + 18, y + 48), fill=color, width=2)
        return

    if condition == "wind":
        for index, width in enumerate((28, 22, 18)):
            start_y = y + 12 + index * 9
            draw.arc((x + 4, start_y - 5, x + 4 + width, start_y + 5), start=200, end=20, fill=color, width=2)
        return

    if condition == "fog":
        _draw_cloud(draw, x + 7, y + 8, color)
        for offset in (28, 34, 40):
            draw.line((x + 8, y + offset, x + 36, y + offset), fill=color, width=2)
        return

    _draw_cloud(draw, x + 7, y + 10, color)


def _draw_cloud(draw: ImageDraw.ImageDraw, x: int, y: int, color: str) -> None:
    draw.ellipse((x, y + 6, x + 14, y + 18), outline=color, width=2)
    draw.ellipse((x + 10, y, x + 24, y + 16), outline=color, width=2)
    draw.ellipse((x + 20, y + 6, x + 34, y + 18), outline=color, width=2)
    draw.line((x + 7, y + 18, x + 28, y + 18), fill=color, width=2)
