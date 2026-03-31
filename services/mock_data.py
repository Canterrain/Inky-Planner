from datetime import date, datetime, timedelta

from models.calendar import CalendarDay, CalendarEvent
from models.dashboard import DashboardData, DataSourceStatus
from models.weather import WeatherDay
from services.text import format_updated_at, translate, weekday_abbrev


VISIBLE_EVENTS_PER_DAY = 3


def _build_event(start_time: str, raw_title: str) -> CalendarEvent:
    return CalendarEvent(
        start_time=start_time,
        compact_start_time=start_time,
        raw_title=raw_title,
        display_title=raw_title,
        dashboard_title=raw_title,
        is_all_day=False,
        is_multi_day=False,
    )


def _calendar_seed() -> list[list[tuple[str, str]]]:
    return [
        [
            ("8:00 AM", "Alex: School Board Check-In"),
            ("3:30 PM", "Sam - Dentist Appointment"),
            ("6:00 PM", "Family Dinner at Nana's House"),
        ],
        [
            ("7:15 AM", "Taylor: Soccer Practice"),
            ("12:00 PM", "Alex lunch with team"),
            ("4:45 PM", "Sam piano pickup"),
            ("6:30 PM", "Alex: Parent Committee Meeting"),
            ("8:00 PM", "Neighborhood Planning Call"),
        ],
        [
            ("9:00 AM", "Project Work Block"),
            ("1:15 PM", "Sam - Library Volunteers"),
            ("5:00 PM", "Taylor science fair setup"),
        ],
        [
            ("8:30 AM", "Alex: Political Meeting"),
            ("2:00 PM", "HVAC service window"),
        ],
        [
            ("10:00 AM", "Sam birthday prep"),
            ("1:00 PM", "Taylor: Half Day Pickup"),
            ("7:00 PM", "Movie Night"),
        ],
    ]


def build_mock_calendar_days(start_date: date, language: str = "en") -> list[CalendarDay]:
    calendar_days: list[CalendarDay] = []

    for offset, seeded_events in enumerate(_calendar_seed()):
        day_date = start_date + timedelta(days=offset)
        events = [_build_event(start_time, raw_title) for start_time, raw_title in seeded_events]
        visible_events = events[:VISIBLE_EVENTS_PER_DAY]
        overflow_count = max(0, len(events) - VISIBLE_EVENTS_PER_DAY)
        calendar_days.append(
            CalendarDay(
                label=weekday_abbrev(day_date, language),
                date_value=day_date,
                multi_day_event=None,
                all_day_events=[],
                timed_events=events,
                visible_events=visible_events,
                overflow_count=overflow_count,
            )
        )

    return calendar_days


def fallback_weather_days(language: str = "en") -> list[WeatherDay]:
    return [
        WeatherDay(label=weekday_abbrev(date(2026, 3, 30), language), source_weather_code=0, effective_weather_code=0, condition_key="clear", icon_name="clear-day", condition_label=translate(language, "condition.clear"), high_temp=63, low_temp=45, temperature_unit="fahrenheit", feels_like_high=64, feels_like_low=43, rain_chance=0, wind_speed=6, wind_speed_unit="mph"),
        WeatherDay(label=weekday_abbrev(date(2026, 3, 31), language), source_weather_code=2, effective_weather_code=2, condition_key="partly_cloudy", icon_name="partlycloudy-day", condition_label=translate(language, "condition.partly_cloudy"), high_temp=61, low_temp=44, temperature_unit="fahrenheit", feels_like_high=60, feels_like_low=42, rain_chance=10, wind_speed=8, wind_speed_unit="mph"),
        WeatherDay(label=weekday_abbrev(date(2026, 4, 1), language), source_weather_code=61, effective_weather_code=61, condition_key="rain", icon_name="rain", condition_label=translate(language, "condition.rain"), high_temp=57, low_temp=41, temperature_unit="fahrenheit", feels_like_high=54, feels_like_low=39, rain_chance=75, wind_speed=14, wind_speed_unit="mph", active_precip_override_used=True),
        WeatherDay(label=weekday_abbrev(date(2026, 4, 2), language), source_weather_code=3, effective_weather_code=3, condition_key="cloudy", icon_name="cloudy", condition_label=translate(language, "condition.cloudy"), high_temp=54, low_temp=39, temperature_unit="fahrenheit", feels_like_high=52, feels_like_low=36, rain_chance=15, wind_speed=9, wind_speed_unit="mph"),
        WeatherDay(label=weekday_abbrev(date(2026, 4, 3), language), source_weather_code=95, effective_weather_code=95, condition_key="thundersnow", icon_name="thundersnow", condition_label=translate(language, "condition.thundersnow"), high_temp=33, low_temp=28, temperature_unit="fahrenheit", feels_like_high=30, feels_like_low=24, rain_chance=70, wind_speed=18, wind_speed_unit="mph", thundersnow_used=True),
    ]


def build_mock_dashboard_data() -> DashboardData:
    start_date = date(2026, 3, 30)

    return DashboardData(
        language="en",
        title="Inky Planner",
        updated_at=format_updated_at(datetime(2026, 3, 27, 14, 36), "en"),
        calendar_days=build_mock_calendar_days(start_date, "en"),
        weather_days=fallback_weather_days("en"),
        calendar_status=DataSourceStatus(source="calendar", state="fallback", message=translate("en", "status.calendar_fallback")),
        weather_status=DataSourceStatus(source="weather", state="fallback", message=translate("en", "status.weather_fallback")),
    )
