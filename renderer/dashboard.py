from pathlib import Path

from PIL import Image, ImageDraw

from hardware.palette import BLACK, BLUE, GREEN, RED, WHITE, YELLOW
from models.calendar import CalendarDay, CalendarEvent
from models.dashboard import DashboardData
from models.weather import WeatherDay
from renderer.icons import draw_weather_icon, paste_weather_icon
from renderer.scene import RenderedScene
from renderer.text import ellipsize, load_font
from services.text import month_day


class DashboardRenderer:
    HEADER_BAND_HEIGHT = 64
    SECTION_GAP = 16
    CALENDAR_PANEL_HEIGHT = 220
    WEATHER_BAND_HEIGHT = 164
    CALENDAR_SIDE_MARGIN = 20
    DAY_BAR_HEIGHT = 22
    EVENT_ROW_HEIGHT = 40
    WEATHER_ICON_SIZE = 92
    STATUS_BANNER_HEIGHT = 18

    def __init__(self, debug: bool = False, hardware_target: bool = False) -> None:
        self.debug = debug
        self.hardware_target = hardware_target
        self.language = "en"
        self.title_font = load_font(30, bold=True)
        self.timestamp_font = load_font(14, bold=True)
        self.day_font = load_font(22, bold=True)
        self.date_font = load_font(14, bold=True)
        self.event_time_font = load_font(15, bold=True)
        self.event_title_font = load_font(13, bold=True)
        self.bar_font = load_font(12, bold=True)
        self.overflow_font = load_font(13, bold=True)
        self.temperature_font = load_font(20, bold=True)

    def render_to_file(self, data: DashboardData, output_path: str | Path) -> Path:
        image = self.render(data)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output)
        return output

    def render(self, data: DashboardData) -> Image.Image:
        return self.render_scene(data).image

    def render_scene(self, data: DashboardData) -> RenderedScene:
        self.language = data.language
        image = Image.new("RGB", (800, 480), GREEN)
        draw = ImageDraw.Draw(image)
        weather_overlay = Image.new("RGBA", image.size, (0, 0, 0, 0)) if self.hardware_target else None

        header_box = (0, 0, 800, self.HEADER_BAND_HEIGHT)
        calendar_box = (20, 80, 780, 300)
        weather_box = (20, 316, 780, 460)
        calendar_columns = self._column_boxes(calendar_box)
        weather_columns = self._column_boxes(weather_box)

        self._draw_header(draw, data, header_box)
        self._draw_calendar_panel(draw, calendar_box, calendar_columns, data.calendar_days)
        self._draw_weather_band(image, draw, weather_box, weather_columns, data.weather_days, weather_overlay=weather_overlay)
        self._draw_source_warnings(draw, data, calendar_box, weather_box)

        return RenderedScene(image=image, weather_overlay=weather_overlay)

    def _draw_header(self, draw: ImageDraw.ImageDraw, data: DashboardData, box: tuple[int, int, int, int]) -> None:
        left, top, right, bottom = box
        draw.rectangle(box, fill=GREEN)
        self._draw_text(draw, 22, top + 14, data.title or "Inky Planner", WHITE, self.title_font)
        timestamp_width = draw.textlength(data.updated_at, font=self.timestamp_font)
        self._draw_text(draw, int(right - 24 - timestamp_width), top + 20, data.updated_at, WHITE, self.timestamp_font)
        draw.line((left, bottom - 1, right, bottom - 1), fill=BLACK, width=4)
        self._debug_box(draw, box)

    def _draw_calendar_panel(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        columns: list[tuple[int, int, int, int]],
        calendar_days: list[CalendarDay],
    ) -> None:
        draw.rectangle(box, fill=WHITE, outline=BLACK, width=3)
        for index in range(1, len(columns)):
            x = columns[index][0]
            draw.line((x, box[1], x, box[3]), fill=BLACK, width=2)
        for day, column in zip(calendar_days, columns):
            self._draw_calendar_day(draw, day, column)
        self._debug_box(draw, box)

    def _draw_calendar_day(self, draw: ImageDraw.ImageDraw, day: CalendarDay, box: tuple[int, int, int, int]) -> None:
        left, top, right, bottom = box
        content_left = left + 8
        content_right = right - 8

        self._draw_text(draw, content_left, top + 10, day.label, BLACK, self.day_font)
        self._draw_text(draw, content_left, top + 40, month_day(day.date_value, self.language), BLUE, self.date_font)

        primary_bar = day.multi_day_event or (day.all_day_events[0] if day.all_day_events else None)
        hidden_bars = len(day.all_day_events)
        if day.multi_day_event is not None:
            hidden_bars = len(day.all_day_events)
        elif primary_bar is not None:
            hidden_bars = max(0, len(day.all_day_events) - 1)

        current_y = top + 66
        if primary_bar is not None:
            self._draw_event_bar(draw, primary_bar.display_title, (content_left, current_y, content_right, current_y + self.DAY_BAR_HEIGHT), RED, WHITE)
            current_y += self.DAY_BAR_HEIGHT + 10

        row_gap = 4
        max_timed_rows = 3
        reserved_overflow_height = 28
        base_timed_events = day.timed_events[:max_timed_rows]
        base_overflow_total = max(0, len(day.timed_events) - max_timed_rows) + hidden_bars
        reserved_bottom = bottom - 10 - (reserved_overflow_height if base_overflow_total > 0 else 0)

        rendered_timed_count = 0
        for index, event in enumerate(base_timed_events):
            row_bottom = current_y + self.EVENT_ROW_HEIGHT
            if row_bottom > reserved_bottom:
                break
            self._draw_timed_event(
                draw,
                event,
                (content_left, current_y, content_right, row_bottom),
                highlight=index == 0,
            )
            rendered_timed_count += 1
            current_y += self.EVENT_ROW_HEIGHT + row_gap

        overflow_total = max(0, len(day.timed_events) - rendered_timed_count) + hidden_bars
        if overflow_total > 0:
            overflow_box = (content_left, bottom - 34, content_right, bottom - 10)
            self._draw_event_bar(draw, f"+{overflow_total} MORE", overflow_box, BLUE, WHITE)

        self._debug_box(draw, box)

    def _draw_event_bar(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        box: tuple[int, int, int, int],
        fill,
        text_fill,
    ) -> None:
        left, top, right, bottom = box
        draw.rectangle(box, fill=fill)
        label = ellipsize(draw, text.upper(), self.bar_font, (right - left) - 4)
        self._draw_text(draw, left + 3, top + 4, label, text_fill, self.bar_font)

    def _draw_timed_event(
        self,
        draw: ImageDraw.ImageDraw,
        event: CalendarEvent,
        box: tuple[int, int, int, int],
        *,
        highlight: bool,
    ) -> None:
        left, top, right, bottom = box
        if highlight:
            draw.rectangle((left, top, right, bottom - 4), fill=YELLOW)

        first_line, second_line = self._wrap_dashboard_event(
            draw,
            event.compact_start_time,
            event.dashboard_title,
            right - left,
        )

        self._draw_text(draw, left, top, first_line, BLACK, self.event_time_font)
        if second_line:
            self._draw_text(draw, left, top + 18, second_line, BLACK, self.event_title_font)

    def _wrap_dashboard_event(
        self,
        draw: ImageDraw.ImageDraw,
        compact_time: str,
        title: str,
        available_width: int,
    ) -> tuple[str, str]:
        prefix = f"{compact_time} "
        words = title.split()
        if not words:
            return compact_time, ""

        first_line = prefix
        index = 0
        while index < len(words):
            candidate = f"{first_line}{words[index]}" if first_line.endswith(" ") else f"{first_line} {words[index]}"
            if draw.textlength(candidate, font=self.event_time_font) > available_width:
                break
            first_line = candidate
            index += 1

        if index == 0:
            first_line = ellipsize(draw, prefix + title, self.event_time_font, available_width)
            return first_line, ""

        remaining = " ".join(words[index:])
        second_line = ellipsize(draw, remaining, self.event_title_font, available_width) if remaining else ""
        return first_line, second_line

    def _draw_weather_band(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        columns: list[tuple[int, int, int, int]],
        weather_days: list[WeatherDay],
        *,
        weather_overlay: Image.Image | None = None,
    ) -> None:
        left, top, right, bottom = box
        draw.rectangle(box, fill=GREEN)
        draw.line((left, top, right - 1, top), fill=BLACK, width=3)
        draw.line((left, bottom - 1, right - 1, bottom - 1), fill=BLACK, width=3)
        draw.line((left, top, left, bottom - 1), fill=BLACK, width=3)
        draw.line((right - 1, top, right - 1, bottom - 1), fill=BLACK, width=3)
        for index in range(1, len(columns)):
            x = columns[index][0]
            draw.line((x, top + 3, x, bottom - 4), fill=WHITE, width=2)
        for weather_day, column in zip(weather_days, columns):
            self._draw_weather_column(image, draw, weather_day, column, weather_overlay=weather_overlay)
        self._debug_box(draw, box)

    def _draw_source_warnings(
        self,
        draw: ImageDraw.ImageDraw,
        data: DashboardData,
        calendar_box: tuple[int, int, int, int],
        weather_box: tuple[int, int, int, int],
    ) -> None:
        if not data.calendar_status.is_live:
            self._draw_status_banner(draw, calendar_box, data.calendar_status.message)
        if not data.weather_status.is_live:
            self._draw_status_banner(draw, weather_box, data.weather_status.message)

    def _draw_status_banner(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        message: str,
    ) -> None:
        left, top, right, _ = box
        banner = (left + 3, top + 3, right - 3, top + 3 + self.STATUS_BANNER_HEIGHT)
        draw.rectangle(banner, fill=RED)
        label = ellipsize(draw, message.upper(), self.bar_font, (banner[2] - banner[0]) - 8)
        self._draw_text(draw, banner[0] + 4, banner[1] + 3, label, WHITE, self.bar_font)

    def _draw_weather_column(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        weather_day: WeatherDay,
        box: tuple[int, int, int, int],
        *,
        weather_overlay: Image.Image | None = None,
    ) -> None:
        left, top, right, bottom = box
        center_x = int((left + right) / 2)
        icon_left = center_x - int(self.WEATHER_ICON_SIZE / 2)
        icon_top = top + 12
        if weather_overlay is not None and paste_weather_icon(
            weather_overlay,
            icon_left,
            icon_top,
            self.WEATHER_ICON_SIZE,
            weather_day.icon_name,
            hardware_target=True,
        ):
            pass
        else:
            draw_weather_icon(
                image,
                draw,
                icon_left,
                icon_top,
                self.WEATHER_ICON_SIZE,
                weather_day.icon_name,
                WHITE,
                hardware_target=self.hardware_target,
            )

        temps = f"{weather_day.high_temp}° / {weather_day.low_temp}°"
        temp_width = draw.textlength(temps, font=self.temperature_font)
        self._draw_text(draw, int(center_x - int(temp_width / 2)), top + 112, temps, WHITE, self.temperature_font)
        self._debug_box(draw, box)

    def _column_boxes(self, container: tuple[int, int, int, int]) -> list[tuple[int, int, int, int]]:
        left, top, right, bottom = container
        width = int((right - left) / 5)
        boxes = []
        current_left = left
        for index in range(5):
            current_right = right if index == 4 else current_left + width
            boxes.append((current_left, top, current_right, bottom))
            current_left = current_right
        return boxes

    def _debug_box(self, draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
        if not self.debug:
            return
        draw.rectangle(box, outline=RED, width=1)

    def _draw_text(self, draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill, font) -> None:
        bbox = font.getbbox(text)
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        mask = Image.new("1", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((-bbox[0], -bbox[1]), text, fill=1, font=font)
        draw.bitmap((int(x), int(y)), mask, fill=fill)
