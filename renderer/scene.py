from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True)
class RenderedScene:
    image: Image.Image
    weather_overlay: Image.Image | None = None

