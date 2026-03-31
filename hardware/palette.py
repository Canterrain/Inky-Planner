from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaletteColor:
    name: str
    rgb: tuple[int, int, int]


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)


SPECTRA_PALETTE: tuple[PaletteColor, ...] = (
    PaletteColor("white", WHITE),
    PaletteColor("black", BLACK),
    PaletteColor("red", RED),
    PaletteColor("green", GREEN),
    PaletteColor("blue", BLUE),
    PaletteColor("yellow", YELLOW),
)


def spectra_palette_rgb() -> list[tuple[int, int, int]]:
    return [color.rgb for color in SPECTRA_PALETTE]


def nearest_palette_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    red, green, blue = rgb
    return min(
        spectra_palette_rgb(),
        key=lambda palette_rgb: (
            (red - palette_rgb[0]) ** 2
            + (green - palette_rgb[1]) ** 2
            + (blue - palette_rgb[2]) ** 2
        ),
    )
