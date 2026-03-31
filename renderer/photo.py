from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from config.layout import COLORS, LAYOUT
from renderer.text import load_font


class PhotoModeRenderer:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.title_font = load_font(24, bold=True)
        self.meta_font = load_font(14)

    def render_to_file(self, photo_path: Path | None, output_path: str | Path) -> Path:
        image = self.render(photo_path)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output)
        return output

    def render(self, photo_path: Path | None) -> Image.Image:
        if photo_path and photo_path.exists():
            source = Image.open(photo_path).convert("RGB")
            image = ImageOps.fit(source, (LAYOUT.canvas_width, LAYOUT.canvas_height), centering=(0.5, 0.5))
        else:
            image = Image.new("RGB", (LAYOUT.canvas_width, LAYOUT.canvas_height), COLORS.background)
            draw = ImageDraw.Draw(image)
            draw.text((LAYOUT.outer_margin, 190), "Photo Mode", fill=COLORS.text_primary, font=self.title_font)
            draw.text((LAYOUT.outer_margin, 224), "No photo found in configured folder.", fill=COLORS.text_secondary, font=self.meta_font)

        if self.debug:
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, LAYOUT.canvas_width - 1, LAYOUT.canvas_height - 1), outline=COLORS.debug, width=1)
            if photo_path:
                label = f"Photo: {photo_path.name}"
                draw.rectangle((LAYOUT.outer_margin, LAYOUT.canvas_height - 36, LAYOUT.canvas_width - LAYOUT.outer_margin, LAYOUT.canvas_height - 16), fill=COLORS.background)
                draw.text((LAYOUT.outer_margin + 6, LAYOUT.canvas_height - 33), label, fill=COLORS.text_secondary, font=self.meta_font)

        return image
