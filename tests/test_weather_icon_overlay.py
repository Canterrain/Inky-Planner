import tempfile
import unittest

from PIL import Image

from hardware.conversion import prepare_hardware_image


class WeatherIconOverlayTests(unittest.TestCase):
    def test_weather_overlay_is_composited_after_atkinson(self) -> None:
        base = Image.new("RGB", (4, 1), (0, 255, 0))
        overlay = Image.new("RGBA", (4, 1), (0, 0, 0, 0))
        overlay.putpixel((1, 0), (255, 255, 255, 255))
        overlay.putpixel((2, 0), (255, 255, 0, 255))

        with tempfile.TemporaryDirectory() as temp_dir:
            result = prepare_hardware_image(
                base,
                target_size=(4, 1),
                output_dir=temp_dir,
                spectra_mode="atkinson",
                palette_debug_enabled=False,
                weather_overlay=overlay,
            )

        self.assertEqual((255, 255, 255), result.image.getpixel((1, 0)))
        self.assertEqual((255, 255, 0), result.image.getpixel((2, 0)))


if __name__ == "__main__":
    unittest.main()
