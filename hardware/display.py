from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from hardware.conversion import prepare_hardware_image, prepare_passthrough_image


@dataclass
class DisplayUpdateResult:
    updated: bool
    reason: str


class InkyDisplayOutput:
    def __init__(
        self,
        *,
        spectra_mode: str = "off",
        palette_debug_enabled: bool = True,
        output_dir: str | Path | None = None,
    ) -> None:
        self.available = False
        self._display = None
        self._black = None
        self._white = None
        self.spectra_mode = spectra_mode
        self.palette_debug_enabled = palette_debug_enabled
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parent.parent / "output"

        try:
            from inky.auto import auto

            display = auto()
            self._display = display
            self._black = getattr(display, "BLACK", None)
            self._white = getattr(display, "WHITE", None)
            self.available = True
            print("[display] init=auto()")
        except Exception as exc:
            print(f"[display] init=failed reason={exc}")
            self.available = False

    def show_image(self, image: Image.Image, *, weather_overlay: Image.Image | None = None) -> DisplayUpdateResult:
        if not self.available or self._display is None:
            return DisplayUpdateResult(updated=False, reason="Inky hardware unavailable")

        result = prepare_hardware_image(
            image,
            target_size=tuple(self._display.resolution),
            output_dir=self.output_dir,
            spectra_mode=self.spectra_mode,
            palette_debug_enabled=self.palette_debug_enabled,
            weather_overlay=weather_overlay,
        )

        print(
            f"[display] source mode={result.source_mode} size={result.source_size} "
            f"spectra_mode={result.spectra_mode}"
        )
        print(
            f"[display] final mode={result.final_mode} size={result.final_size} "
            f"converted={result.converted} resized={result.resized}"
        )
        if result.invalid_pixel_count > 0:
            print(f"[display] error=non_palette_pixels count={result.invalid_pixel_count} remapped_to_nearest_allowed")
        print(f"[display] artifacts={','.join(str(path) for path in result.artifacts.written_paths())}")

        self._display.set_image(result.image)
        if self._white is not None:
            try:
                self._display.set_border(self._white)
            except Exception:
                pass
        self._display.show()
        return DisplayUpdateResult(updated=True, reason="Display updated")

    def show_photo_image(self, image: Image.Image, *, saturation: float = 0.5) -> DisplayUpdateResult:
        if not self.available or self._display is None:
            return DisplayUpdateResult(updated=False, reason="Inky hardware unavailable")

        result = prepare_passthrough_image(
            image,
            target_size=tuple(self._display.resolution),
            output_dir=self.output_dir,
            palette_debug_enabled=self.palette_debug_enabled,
        )

        print(
            f"[display] source mode={result.source_mode} size={result.source_size} "
            f"spectra_mode={result.spectra_mode}"
        )
        print(
            f"[display] final mode={result.final_mode} size={result.final_size} "
            f"converted={result.converted} resized={result.resized}"
        )
        print(f"[display] artifacts={','.join(str(path) for path in result.artifacts.written_paths())}")

        try:
            self._display.set_image(result.image, saturation=saturation)
        except TypeError:
            self._display.set_image(result.image)
        if self._white is not None:
            try:
                self._display.set_border(self._white)
            except Exception:
                pass
        self._display.show()
        return DisplayUpdateResult(updated=True, reason="Display updated")
