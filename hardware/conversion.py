from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from hardware.palette import nearest_palette_color, spectra_palette_rgb


@dataclass(frozen=True)
class ConversionArtifacts:
    layout_render: Path | None
    quantized_render: Path | None
    dithered_render: Path | None
    hardware_final: Path | None

    def written_paths(self) -> list[Path]:
        return [path for path in (self.layout_render, self.quantized_render, self.dithered_render, self.hardware_final) if path is not None]


@dataclass(frozen=True)
class ConversionResult:
    image: Image.Image
    artifacts: ConversionArtifacts
    source_mode: str
    source_size: tuple[int, int]
    final_mode: str
    final_size: tuple[int, int]
    converted: bool
    resized: bool
    spectra_mode: str
    invalid_pixel_count: int


def prepare_passthrough_image(
    image: Image.Image,
    *,
    target_size: tuple[int, int],
    output_dir: str | Path,
    palette_debug_enabled: bool,
) -> ConversionResult:
    source_mode = image.mode
    source_size = image.size
    resized = False
    converted = False

    working = image
    if tuple(working.size) != tuple(target_size):
        working = working.resize(target_size, Image.Resampling.LANCZOS)
        resized = True

    if working.mode != "RGB":
        working = working.convert("RGB")
        converted = True
    else:
        working = working.copy()

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    layout_path = output_root / "layout_render.png"
    hardware_path = output_root / "hardware_final.png"

    if palette_debug_enabled:
        working.save(layout_path)
    working.save(hardware_path)

    artifacts = ConversionArtifacts(
        layout_render=layout_path if palette_debug_enabled else None,
        quantized_render=None,
        dithered_render=None,
        hardware_final=hardware_path,
    )

    return ConversionResult(
        image=working,
        artifacts=artifacts,
        source_mode=source_mode,
        source_size=source_size,
        final_mode=working.mode,
        final_size=working.size,
        converted=converted,
        resized=resized,
        spectra_mode="inky_auto",
        invalid_pixel_count=0,
    )


def prepare_hardware_image(
    image: Image.Image,
    *,
    target_size: tuple[int, int],
    output_dir: str | Path,
    spectra_mode: str,
    palette_debug_enabled: bool,
    weather_overlay: Image.Image | None = None,
) -> ConversionResult:
    source_mode = image.mode
    source_size = image.size
    resized = False
    converted = False

    working = image
    if tuple(working.size) != tuple(target_size):
        working = working.resize(target_size, Image.Resampling.LANCZOS)
        resized = True

    if working.mode != "RGB":
        working = working.convert("RGB")
        converted = True
    else:
        working = working.copy()

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    layout_path = output_root / "layout_render.png"
    quantized_path = output_root / "quantized_render.png"
    dithered_path = output_root / "dithered_render.png"
    hardware_path = output_root / "hardware_final.png"

    if palette_debug_enabled:
        working.save(layout_path)

    normalized_mode = spectra_mode.lower()
    if normalized_mode == "off":
        quantized = working.copy()
        dithered = working.copy()
        final_image = working.copy()
    else:
        quantized = _quantize_to_palette(working)
        if normalized_mode == "quantize":
            dithered = quantized.copy()
        elif normalized_mode == "floyd":
            dithered = _floyd_to_palette(working)
        elif normalized_mode == "atkinson":
            dithered = _atkinson_to_palette(working)
        else:
            raise ValueError(f"Unsupported spectra_mode: {spectra_mode}")
        final_image = dithered.copy()

    final_image, invalid_pixel_count = _enforce_palette(final_image)
    if weather_overlay is not None:
        final_image = _composite_weather_overlay(final_image, weather_overlay, target_size)
        final_image, overlay_invalid = _enforce_palette(final_image)
        invalid_pixel_count += overlay_invalid

    if palette_debug_enabled:
        quantized.save(quantized_path)
        dithered.save(dithered_path)

    final_image.save(hardware_path)

    artifacts = ConversionArtifacts(
        layout_render=layout_path if palette_debug_enabled else None,
        quantized_render=quantized_path if palette_debug_enabled else None,
        dithered_render=dithered_path if palette_debug_enabled else None,
        hardware_final=hardware_path,
    )

    return ConversionResult(
        image=final_image,
        artifacts=artifacts,
        source_mode=source_mode,
        source_size=source_size,
        final_mode=final_image.mode,
        final_size=final_image.size,
        converted=converted,
        resized=resized,
        spectra_mode=normalized_mode,
        invalid_pixel_count=invalid_pixel_count,
    )


def _composite_weather_overlay(
    image: Image.Image,
    weather_overlay: Image.Image,
    target_size: tuple[int, int],
) -> Image.Image:
    overlay = weather_overlay
    if tuple(overlay.size) != tuple(target_size):
        overlay = overlay.resize(target_size, Image.Resampling.LANCZOS)
    if overlay.mode != "RGBA":
        overlay = overlay.convert("RGBA")
    base = image.convert("RGBA")
    composed = Image.alpha_composite(base, overlay)
    return composed.convert("RGB")


def _quantize_to_palette(image: Image.Image) -> Image.Image:
    quantized = image.quantize(palette=_spectra_palette_image(), dither=Image.Dither.NONE)
    return quantized.convert("RGB")


def _floyd_to_palette(image: Image.Image) -> Image.Image:
    quantized = image.quantize(palette=_spectra_palette_image(), dither=Image.Dither.FLOYDSTEINBERG)
    return quantized.convert("RGB")


def _atkinson_to_palette(image: Image.Image) -> Image.Image:
    source = image.convert("RGB")
    width, height = source.size
    source_pixels = [[list(source.getpixel((x, y))) for x in range(width)] for y in range(height)]

    output = Image.new("RGB", source.size)
    output_pixels = output.load()

    for y in range(height):
        for x in range(width):
            old_pixel = tuple(_clamp_channel(channel) for channel in source_pixels[y][x])
            new_pixel = nearest_palette_color(old_pixel)
            output_pixels[x, y] = new_pixel

            error = [old_pixel[index] - new_pixel[index] for index in range(3)]
            diffusion = [channel / 8 for channel in error]
            for dx, dy in ((1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)):
                nx = x + dx
                ny = y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    for index in range(3):
                        source_pixels[ny][nx][index] += diffusion[index]

    return output


def _spectra_palette_image() -> Image.Image:
    palette_image = Image.new("P", (1, 1))
    flat_palette: list[int] = []
    for red, green, blue in spectra_palette_rgb():
        flat_palette.extend((red, green, blue))
    while len(flat_palette) < 768:
        flat_palette.extend((0, 0, 0))
    palette_image.putpalette(flat_palette[:768])
    return palette_image


def _clamp_channel(value: float) -> int:
    return max(0, min(255, int(round(value))))


def _enforce_palette(image: Image.Image) -> tuple[Image.Image, int]:
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    output = Image.new("RGB", rgb_image.size)
    invalid_pixel_count = 0
    allowed = set(spectra_palette_rgb())

    for y in range(height):
        for x in range(width):
            pixel = rgb_image.getpixel((x, y))
            if pixel in allowed:
                output.putpixel((x, y), pixel)
                continue

            invalid_pixel_count += 1
            output.putpixel((x, y), nearest_palette_color(pixel))

    return output, invalid_pixel_count
