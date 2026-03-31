from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config.settings import load_settings
from models.dashboard import DashboardData, DataSourceStatus
from services.calendar_service import CalendarServiceError, fallback_calendar_days, fetch_calendar_days
from services.mock_data import fallback_weather_days
from services.text import format_updated_at, translate
from services.weather_service import WeatherServiceError, fetch_weather_days


def build_dashboard_data(settings_path: str | Path) -> DashboardData:
    settings = load_settings(settings_path)
    now = datetime.now(ZoneInfo(settings.weather.timezone))
    start_date = now.date()

    calendar_days, calendar_status = _safe_calendar_days(settings, start_date)
    weather_days, weather_status = _safe_weather_days(settings)

    return DashboardData(
        language=settings.language,
        title=settings.dashboard_title,
        updated_at=format_updated_at(now, settings.language),
        calendar_days=calendar_days,
        weather_days=weather_days,
        calendar_status=calendar_status,
        weather_status=weather_status,
    )


def _safe_calendar_days(settings, start_date):
    try:
        return (
            fetch_calendar_days(settings, start_date),
            DataSourceStatus(source="calendar", state="live", message="CALENDAR LIVE"),
        )
    except Exception as exc:
        print(f"[calendar] error={exc} fallback=sample-data")
        return (
            fallback_calendar_days(settings, start_date),
            DataSourceStatus(source="calendar", state="fallback", message=translate(settings.language, "status.calendar_fallback")),
        )


def _safe_weather_days(settings):
    try:
        return (
            fetch_weather_days(settings),
            DataSourceStatus(source="weather", state="live", message="WEATHER LIVE"),
        )
    except Exception as exc:
        print(f"[weather] error={exc} fallback=sample-data")
        return (
            fallback_weather_days(settings.language),
            DataSourceStatus(source="weather", state="fallback", message=translate(settings.language, "status.weather_fallback")),
        )
