import tempfile
import unittest
from pathlib import Path

from PIL import Image

from hardware.conversion import prepare_hardware_image, prepare_passthrough_image
from hardware.palette import spectra_palette_rgb


class ConversionTests(unittest.TestCase):
    def test_quantize_mode_uses_only_strict_palette(self) -> None:
        image = Image.new("RGB", (4, 1))
        image.putdata(
            [
                (12, 12, 12),
                (250, 210, 20),
                (10, 40, 240),
                (30, 180, 40),
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = prepare_hardware_image(
                image,
                target_size=(4, 1),
                output_dir=temp_dir,
                spectra_mode="quantize",
                palette_debug_enabled=True,
            )

            self.assertEqual("quantize", result.spectra_mode)
            self.assertTrue((Path(temp_dir) / "layout_render.png").exists())
            self.assertTrue((Path(temp_dir) / "quantized_render.png").exists())
            self.assertTrue((Path(temp_dir) / "dithered_render.png").exists())
            self.assertTrue((Path(temp_dir) / "hardware_final.png").exists())

            allowed = set(spectra_palette_rgb())
            self.assertTrue(self._all_pixels_within_palette(result.image, allowed))

    def test_off_mode_remaps_non_palette_colors_before_final_output(self) -> None:
        image = Image.new("RGB", (1, 1), (123, 45, 67))

        with tempfile.TemporaryDirectory() as temp_dir:
            result = prepare_hardware_image(
                image,
                target_size=(1, 1),
                output_dir=temp_dir,
                spectra_mode="off",
                palette_debug_enabled=True,
            )

            self.assertEqual((0, 0, 0), result.image.getpixel((0, 0)))
            self.assertEqual(1, result.invalid_pixel_count)

    def test_atkinson_mode_uses_only_strict_palette(self) -> None:
        image = Image.new("RGB", (3, 2))
        image.putdata(
            [
                (255, 255, 255),
                (200, 200, 200),
                (0, 0, 0),
                (240, 20, 20),
                (20, 20, 240),
                (240, 240, 20),
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = prepare_hardware_image(
                image,
                target_size=(3, 2),
                output_dir=temp_dir,
                spectra_mode="atkinson",
                palette_debug_enabled=False,
            )

            allowed = set(spectra_palette_rgb())
            self.assertTrue(self._all_pixels_within_palette(result.image, allowed))

    def test_passthrough_mode_preserves_rgb_pixels(self) -> None:
        image = Image.new("RGB", (1, 1), (123, 45, 67))

        with tempfile.TemporaryDirectory() as temp_dir:
            result = prepare_passthrough_image(
                image,
                target_size=(1, 1),
                output_dir=temp_dir,
                palette_debug_enabled=True,
            )

            self.assertEqual("inky_auto", result.spectra_mode)
            self.assertEqual((123, 45, 67), result.image.getpixel((0, 0)))
            self.assertEqual(0, result.invalid_pixel_count)
            self.assertTrue((Path(temp_dir) / "layout_render.png").exists())
            self.assertTrue((Path(temp_dir) / "hardware_final.png").exists())
            self.assertFalse((Path(temp_dir) / "quantized_render.png").exists())

    def _all_pixels_within_palette(self, image: Image.Image, allowed: set[tuple[int, int, int]]) -> bool:
        width, height = image.size
        for y in range(height):
            for x in range(width):
                if image.getpixel((x, y)) not in allowed:
                    return False
        return True


if __name__ == "__main__":
    unittest.main()
