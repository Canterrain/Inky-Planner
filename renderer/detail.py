from pathlib import Path

from PIL import Image, ImageDraw

from hardware.palette import BLACK, BLUE, GREEN, RED, WHITE, YELLOW
from models.calendar import CalendarDay, CalendarEvent
from models.dashboard import DashboardData
from models.weather import WeatherDay
from renderer.icons import draw_weather_icon, paste_weather_icon
from renderer.scene import RenderedScene
from renderer.text import ellipsize, load_font
from services.text import month_day, translate


class DayDetailRenderer:
    HEADER_HEIGHT = 64
    SECTION_GAP = 16
    LEFT_PANEL_BOX = (20, 80, 520, 460)
    RIGHT_PANEL_BOX = (536, 80, 780, 460)
    EVENT_BAR_HEIGHT = 22
    EVENT_ROW_HEIGHT = 40
    EVENT_ROW_GAP = 8
    WEATHER_ICON_SIZE = 152
    STATUS_BANNER_HEIGHT = 18

    def __init__(self, day_index: int, title_prefix: str, debug: bool = False, hardware_target: bool = False) -> None:
        self.day_index = day_index
        self.title_prefix = title_prefix
        self.debug = debug
        self.hardware_target = hardware_target
        self.title_font = load_font(30, bold=True)
        self.timestamp_font = load_font(14, bold=True)
        self.day_font = load_font(22, bold=True)
        self.date_font = load_font(14, bold=True)
        self.event_time_font = load_font(15, bold=True)
        self.event_title_font = load_font(14, bold=True)
        self.bar_font = load_font(12, bold=True)
        self.overflow_font = load_font(13, bold=True)
        self.temperature_font = load_font(24, bold=True)
        self.label_font = load_font(14, bold=True)
        self.meta_font = load_font(13, bold=True)
        self.intel_primary_font = load_font(15, bold=True)
        self.intel_secondary_font = load_font(12, bold=True)
        self.weather_advice_font = load_font(16, bold=True)
        self.weather_fact_font = load_font(13, bold=True)
        self.language = "en"

    def render_to_file(self, data: DashboardData, output_path: str | Path) -> Path:
        image = self.render(data)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output)
        return output

    def render(self, data: DashboardData) -> Image.Image:
        return self.render_scene(data).image

    def render_scene(self, data: DashboardData) -> RenderedScene:
        image = Image.new("RGB", (800, 480), GREEN)
        draw = ImageDraw.Draw(image)
        day = data.calendar_days[self.day_index]
        weather = data.weather_days[self.day_index]
        self.language = data.language
        weather_overlay = Image.new("RGBA", image.size, (0, 0, 0, 0)) if self.hardware_target else None

        header_box = (0, 0, 800, self.HEADER_HEIGHT)
        self._draw_header(draw, data, day, header_box)
        self._draw_schedule(draw, day, self.LEFT_PANEL_BOX)
        self._draw_weather(image, draw, day, weather, self.RIGHT_PANEL_BOX, weather_overlay=weather_overlay)
        self._draw_source_warnings(draw, data, self.LEFT_PANEL_BOX, self.RIGHT_PANEL_BOX)

        return RenderedScene(image=image, weather_overlay=weather_overlay)

    def _draw_header(
        self,
        draw: ImageDraw.ImageDraw,
        data: DashboardData,
        day: CalendarDay,
        box: tuple[int, int, int, int],
    ) -> None:
        left, top, right, bottom = box
        draw.rectangle(box, fill=GREEN)
        title = f"{self._title_prefix_label()}: {day.label}"
        self._draw_text(draw, 22, top + 14, title, WHITE, self.title_font)
        timestamp_width = draw.textlength(data.updated_at, font=self.timestamp_font)
        self._draw_text(draw, int(right - 24 - timestamp_width), top + 20, data.updated_at, WHITE, self.timestamp_font)
        draw.line((left, bottom - 1, right, bottom - 1), fill=BLACK, width=4)
        self._debug_box(draw, box)

    def _draw_source_warnings(
        self,
        draw: ImageDraw.ImageDraw,
        data: DashboardData,
        schedule_box: tuple[int, int, int, int],
        weather_box: tuple[int, int, int, int],
    ) -> None:
        if not data.calendar_status.is_live:
            self._draw_status_banner(draw, schedule_box, data.calendar_status.message)
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

    def _draw_schedule(self, draw: ImageDraw.ImageDraw, day: CalendarDay, box: tuple[int, int, int, int]) -> None:
        left, top, right, bottom = box
        draw.rectangle(box, fill=WHITE, outline=BLACK, width=3)

        content_left = left + 12
        content_right = right - 12
        self._draw_text(draw, content_left, top + 10, day.label, BLACK, self.day_font)
        self._draw_text(draw, content_left, top + 40, month_day(day.date_value, self.language), BLUE, self.date_font)

        current_y = top + 70
        if day.multi_day_event is not None:
            current_y = self._draw_event_bar(draw, day.multi_day_event.display_title, (content_left, current_y, content_right, current_y + self.EVENT_BAR_HEIGHT), RED, WHITE)
        for event in day.all_day_events:
            current_y = self._draw_event_bar(draw, event.display_title, (content_left, current_y, content_right, current_y + self.EVENT_BAR_HEIGHT), RED, WHITE)

        if day.multi_day_event or day.all_day_events:
            current_y += 4

        timed_events = day.timed_events
        if not timed_events and day.multi_day_event is None and not day.all_day_events:
            self._draw_status_block(draw, self._status_block_box(box), [self._t("schedule.free_all_day")])
            self._debug_box(draw, box)
            return

        available_bottom = bottom - 16
        row_height, row_gap = self._timed_row_metrics(len(timed_events))
        rendered_timed_count = 0
        for index, event in enumerate(timed_events):
            row_bottom = current_y + row_height
            if row_bottom > available_bottom:
                remaining = len(timed_events) - index
                if remaining > 0:
                    overflow_box = (content_left, bottom - 34, content_right, bottom - 10)
                    self._draw_event_bar(draw, f"+{remaining} MORE", overflow_box, BLUE, WHITE)
                break
            current_y = self._draw_timed_event(
                draw,
                event,
                (content_left, current_y, content_right, row_bottom),
                highlight=index == 0,
                row_gap=row_gap,
            )
            rendered_timed_count += 1

        status_lines = self._build_status_block_lines(day)
        if status_lines and self._should_show_status_block(day, box, current_y, rendered_timed_count):
            self._draw_status_block(draw, self._status_block_box(box), status_lines)

        self._debug_box(draw, box)

    def _draw_weather(
        self,
        image: Image.Image,
        draw: ImageDraw.ImageDraw,
        day: CalendarDay,
        weather: WeatherDay,
        box: tuple[int, int, int, int],
        *,
        weather_overlay: Image.Image | None = None,
    ) -> None:
        left, top, right, bottom = box
        draw.rectangle(box, fill=GREEN)
        draw.rectangle((left, top, right - 1, bottom - 1), outline=BLACK, width=3)

        center_x = int((left + right) / 2)
        icon_left = center_x - int(self.WEATHER_ICON_SIZE / 2)
        icon_top = top + 8
        if weather_overlay is not None and paste_weather_icon(
            weather_overlay,
            icon_left,
            icon_top,
            self.WEATHER_ICON_SIZE,
            weather.icon_name,
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
                weather.icon_name,
                WHITE,
                hardware_target=self.hardware_target,
            )

        temps = f"{weather.high_temp}° / {weather.low_temp}°"
        temp_width = draw.textlength(temps, font=self.temperature_font)
        self._draw_text(draw, int(center_x - temp_width / 2), top + 182, temps, WHITE, self.temperature_font)

        facts = self._build_weather_facts(weather)
        facts_start_y = top + 218
        for index, fact in enumerate(facts[:2]):
            fact_width = draw.textlength(fact, font=self.weather_fact_font)
            self._draw_text(draw, int(center_x - fact_width / 2), facts_start_y + (index * 18), fact, WHITE, self.weather_fact_font)

        info_box = (left + 12, bottom - 96, right - 12, bottom - 12)
        draw.rectangle(info_box, fill=WHITE, outline=BLACK, width=2)
        insights = self._build_weather_advice(weather)
        advice_lines = self._wrap_centered_lines(draw, insights[:2], self.weather_advice_font, (info_box[2] - info_box[0]) - 12)
        total_height = len(advice_lines) * 20
        start_y = info_box[1] + max(8, int(((info_box[3] - info_box[1]) - total_height) / 2))
        for index, line in enumerate(advice_lines):
            text_width = draw.textlength(line, font=self.weather_advice_font)
            text_x = int((info_box[0] + info_box[2] - text_width) / 2)
            self._draw_text(draw, text_x, start_y + (index * 20), line, BLACK, self.weather_advice_font)

        self._debug_box(draw, box)

    def _draw_event_bar(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        box: tuple[int, int, int, int],
        fill,
        text_fill,
    ) -> int:
        left, top, right, bottom = box
        draw.rectangle(box, fill=fill)
        label = ellipsize(draw, text.upper(), self.bar_font, (right - left) - 4)
        self._draw_text(draw, left + 3, top + 4, label, text_fill, self.bar_font)
        return bottom + 8

    def _draw_timed_event(
        self,
        draw: ImageDraw.ImageDraw,
        event: CalendarEvent,
        box: tuple[int, int, int, int],
        *,
        highlight: bool,
        row_gap: int,
    ) -> int:
        left, top, right, bottom = box
        if highlight:
            highlight_top = top + 20
            highlight_bottom = min(bottom - 8, top + 38)
            draw.rectangle((left, highlight_top, right, highlight_bottom), fill=YELLOW)

        time_text = event.start_time
        title_text = ellipsize(draw, event.display_title, self.event_title_font, int((right - left) * 0.95))

        self._draw_text(draw, left, top, time_text, BLACK, self.event_time_font)
        self._draw_text(draw, left, top + 18, title_text, BLACK, self.event_title_font)
        return bottom + row_gap

    def _wrap_centered_lines(
        self,
        draw: ImageDraw.ImageDraw,
        insights: list[str],
        font,
        max_width: int,
    ) -> list[str]:
        if not insights:
            return [self._t("weather.steady")]

        primary = insights[0].strip().upper()
        if draw.textlength(primary, font=font) <= max_width:
            return [primary]

        words = primary.split()
        if len(words) >= 2:
            best_split = None
            best_score = None
            for index in range(1, len(words)):
                first = " ".join(words[:index])
                second = " ".join(words[index:])
                first_width = draw.textlength(first, font=font)
                second_width = draw.textlength(second, font=font)
                if first_width <= max_width and second_width <= max_width:
                    score = abs(first_width - second_width)
                    if best_score is None or score < best_score:
                        best_score = score
                        best_split = [first, second]
            if best_split:
                return best_split

        return [ellipsize(draw, primary, font, max_width)]

    def _draw_text(self, draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill, font) -> None:
        bbox = font.getbbox(text)
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        mask = Image.new("1", (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((-bbox[0], -bbox[1]), text, fill=1, font=font)
        draw.bitmap((int(x), int(y)), mask, fill=fill)

    def _debug_box(self, draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
        if not self.debug:
            return
        draw.rectangle(box, outline=RED, width=1)

    def _timed_row_metrics(self, event_count: int) -> tuple[int, int]:
        if event_count <= 1:
            return 72, 14
        if event_count == 2:
            return 56, 12
        if event_count <= 4:
            return 44, 8
        return 36, 6

    def _build_weather_advice(self, weather: WeatherDay) -> list[str]:
        primary = self._weather_intelligence(weather)
        secondary = self._secondary_weather_advice(weather)
        lines: list[str] = []
        if primary:
            lines.append(primary)
        if secondary and secondary != primary:
            lines.append(secondary)
        return lines[:2] if lines else [self._t("weather.steady")]

    def _weather_intelligence(self, weather: WeatherDay) -> str | None:
        icon = weather.icon_name
        spread = weather.high_temp - weather.low_temp
        if icon in {"rain", "showers-day", "showers-night"}:
            return self._t("weather.rain_likely")
        if icon == "thunderstorm":
            return self._t("weather.storm_risk")
        if icon in {"snow", "sleet"}:
            return self._t("weather.cold_and_wet")
        if spread >= 15:
            return self._t("weather.warmer_later")
        if weather.high_temp <= 45:
            return self._t("weather.cold_morning")
        if icon in {"clear-day", "clear-night"}:
            return self._t("weather.dry_all_day")
        return self._t("weather.steady")

    def _secondary_weather_advice(self, weather: WeatherDay) -> str | None:
        if weather.high_temp <= 40 or (weather.feels_like_low is not None and weather.feels_like_low <= 35):
            return self._t("weather.bring_coat")
        if weather.icon_name in {"rain", "showers-day", "showers-night", "thunderstorm"}:
            return self._t("weather.bring_umbrella")
        spread = weather.high_temp - weather.low_temp
        if spread >= 15:
            return self._t("weather.warmer_later")
        if weather.high_temp >= 75:
            return self._t("weather.mild_afternoon")
        return None

    def _build_weather_facts(self, weather: WeatherDay) -> list[str]:
        facts: list[str] = []
        if weather.feels_like_high is not None:
            facts.append(self._t("weather.fact_feels", value=weather.feels_like_high))
        if weather.rain_chance is not None:
            facts.append(self._t("weather.fact_rain", value=weather.rain_chance))
        if weather.wind_speed is not None:
            facts.append(self._t("weather.fact_wind", value=weather.wind_speed, unit=weather.wind_speed_unit.upper()))
        if weather.feels_like_low is not None and weather.feels_like_low != weather.low_temp:
            facts.append(self._t("weather.fact_low_feels", value=weather.feels_like_low))

        unique_facts: list[str] = []
        for fact in facts:
            if fact not in unique_facts:
                unique_facts.append(fact)
        if len(unique_facts) >= 2:
            return unique_facts[:2]
        if len(unique_facts) == 1:
            return [unique_facts[0], self._t("weather.fact_high", value=weather.high_temp)]
        return [self._t("weather.fact_high", value=weather.high_temp), self._t("weather.fact_low", value=weather.low_temp)]

    def _free_time_line(self, day: CalendarDay) -> str | None:
        timed_events = day.timed_events
        if not timed_events:
            if day.multi_day_event or day.all_day_events:
                return None
            return self._t("schedule.free_all_day")
        if len(timed_events) == 1:
            hour = self._hour_value(timed_events[0].start_time)
            if hour is not None and hour >= 12:
                return self._t("schedule.free_all_morning")
            return self._t("schedule.free_after", time=timed_events[0].start_time)
        last_hour = self._hour_value(timed_events[-1].start_time)
        if last_hour is not None and last_hour <= 15:
            return self._t("schedule.free_after", time=timed_events[-1].start_time)
        return None

    def _build_status_block_lines(self, day: CalendarDay) -> list[str]:
        free_time = self._free_time_line(day)
        if free_time == self._t("schedule.free_all_day"):
            return [self._t("schedule.free_all_day")]
        if free_time == self._t("schedule.free_all_morning"):
            return [self._t("schedule.free_all_morning"), self._t("schedule.enjoy")]
        if free_time:
            return [free_time]
        if not day.timed_events and (day.multi_day_event or day.all_day_events):
            return [self._t("schedule.no_timed_events")]
        if len(day.timed_events) == 1:
            return [self._t("schedule.light_day")]
        return []

    def _title_prefix_label(self) -> str:
        if self.title_prefix.lower() == "today":
            return self._t("detail.title_today")
        if self.title_prefix.lower() == "tomorrow":
            return self._t("detail.title_tomorrow")
        return self.title_prefix

    def _t(self, key: str, **kwargs) -> str:
        return translate(self.language, key, **kwargs)

    def _should_show_status_block(
        self,
        day: CalendarDay,
        box: tuple[int, int, int, int],
        current_y: int,
        rendered_timed_count: int,
    ) -> bool:
        if not self._build_status_block_lines(day):
            return False
        if len(day.timed_events) >= 3:
            return False
        left, top, right, bottom = box
        available_height = (bottom - 12) - current_y
        return available_height >= 74 and rendered_timed_count <= 2

    def _status_block_box(self, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        left, top, right, bottom = box
        return (left + 12, bottom - 86, right - 12, bottom - 12)

    def _draw_status_block(
        self,
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        lines: list[str],
    ) -> None:
        left, top, right, bottom = box
        draw.rectangle(box, fill=WHITE, outline=BLACK, width=2)
        if not lines:
            return
        if len(lines) == 1:
            font = self.day_font
            text = ellipsize(draw, lines[0], font, (right - left) - 12)
            text_width = draw.textlength(text, font=font)
            self._draw_text(draw, int((left + right - text_width) / 2), top + 22, text, BLACK, font)
            return
        primary = ellipsize(draw, lines[0], self.intel_primary_font, (right - left) - 12)
        secondary = ellipsize(draw, lines[1], self.intel_secondary_font, (right - left) - 12)
        primary_width = draw.textlength(primary, font=self.intel_primary_font)
        secondary_width = draw.textlength(secondary, font=self.intel_secondary_font)
        self._draw_text(draw, int((left + right - primary_width) / 2), top + 12, primary, BLACK, self.intel_primary_font)
        self._draw_text(draw, int((left + right - secondary_width) / 2), top + 40, secondary, BLACK, self.intel_secondary_font)

    def _hour_value(self, start_time: str) -> int | None:
        text = start_time.strip().upper()
        if not text:
            return None
        try:
            time_part, meridiem = text.split()
            hour = int(time_part.split(":")[0])
        except (ValueError, IndexError):
            return None
        if meridiem == "PM" and hour != 12:
            return hour + 12
        if meridiem == "AM" and hour == 12:
            return 0
        return hour
