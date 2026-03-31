from PIL import ImageDraw, ImageFont


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]

    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue

    return ImageFont.load_default()


def ellipsize(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text

    ellipsis = "..."
    words = text.split()

    if len(words) > 1:
        for word_count in range(len(words) - 1, 0, -1):
            candidate = " ".join(words[:word_count]).rstrip(" ,;:-") + ellipsis
            if draw.textlength(candidate, font=font) <= max_width:
                return candidate

    truncated = text.rstrip()
    while truncated:
        truncated = truncated[:-1].rstrip(" ,;:-")
        candidate = truncated + ellipsis
        if draw.textlength(candidate, font=font) <= max_width:
            return candidate

    return ellipsis
