from dataclasses import dataclass


@dataclass(frozen=True)
class Layout:
    canvas_width: int = 800
    canvas_height: int = 480
    outer_margin: int = 20
    header_height: int = 44
    calendar_height: int = 240
    weather_height: int = 132
    column_count: int = 5
    column_width: int = 145
    column_gap: int = 8
    section_gap: int = 12
    divider_gap: int = 8
    weather_top_gap: int = 18
    event_row_height: int = 48
    event_time_dot_size: int = 8
    event_time_line_gap: int = 8
    column_inner_padding: int = 12
    weather_icon_size: int = 92


@dataclass(frozen=True)
class Colors:
    background: str = "#D2DAC8"
    text_primary: str = "#000000"
    text_secondary: str = "#202020"
    text_muted: str = "#3A3A3A"
    divider: str = "#6B6B6B"
    separator_light: str = "#8E8E8E"
    weather_strip_background: str = "#B9C3AA"
    weather_strip_edge: str = "#788264"
    weather_strip_bottom: str = "#8C9678"
    debug: str = "#D9CFC3"
    dot_fallback: str = "#3F3F3F"
    weather_icon: str = "#000000"
    weather_accent: str = "#C89650"


LAYOUT = Layout()
COLORS = Colors()
