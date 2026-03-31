import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen

from config.settings import AppSettings
from models.weather import WeatherDay
from services.text import weekday_abbrev
from services.weather_semantics import (
    apply_active_precip_override_minutely,
    apply_recent_snow_override_hourly,
    interpret_openmeteo_daily_condition,
)


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TIMEOUT_SECONDS = 5


class WeatherServiceError(RuntimeError):
    pass


def fetch_weather_days(settings: AppSettings, day_count: int = 5) -> list[WeatherDay]:
    params = urlencode(
        {
            "latitude": settings.weather.latitude,
            "longitude": settings.weather.longitude,
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "apparent_temperature_max,apparent_temperature_min,"
                "precipitation_probability_max,wind_speed_10m_max"
            ),
            "current": "temperature_2m,weather_code,is_day",
            "hourly": "weather_code,snowfall",
            "minutely_15": "precipitation,snowfall",
            "temperature_unit": settings.weather.temperature_unit,
            "timezone": settings.weather.timezone,
            "forecast_days": day_count,
        }
    )
    url = f"{OPEN_METEO_URL}?{params}"

    try:
        with urlopen(url, timeout=WEATHER_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise WeatherServiceError(f"Unable to fetch weather data: {exc}") from exc

    daily = payload.get("daily")
    if not daily:
        raise WeatherServiceError("Weather response did not include daily forecast data")

    try:
        dates = daily["time"]
        codes = daily["weather_code"]
        highs = daily["temperature_2m_max"]
        lows = daily["temperature_2m_min"]
    except KeyError as exc:
        raise WeatherServiceError(f"Weather response missing required daily field: {exc}") from exc

    feels_like_highs = daily.get("apparent_temperature_max", [])
    feels_like_lows = daily.get("apparent_temperature_min", [])
    rain_chances = daily.get("precipitation_probability_max", [])
    wind_speeds = daily.get("wind_speed_10m_max", [])
    current = payload.get("current") or {}
    hourly = payload.get("hourly") or {}
    minutely = payload.get("minutely_15") or {}
    wind_speed_unit = "mph" if settings.weather.temperature_unit == "fahrenheit" else "km/h"

    weather_days: list[WeatherDay] = []
    for index in range(min(day_count, len(dates))):
        daily_weather_code = int(codes[index])
        weather_code = daily_weather_code
        active_precip_used = False
        recent_snow_used = False

        if index == 0:
            weather_code, active_precip_used, recent_snow_used = _resolve_current_day_code(
                settings,
                default_code=weather_code,
                current=current,
                hourly=hourly,
                minutely=minutely,
            )

        condition = interpret_openmeteo_daily_condition(
            weather_code,
            high_temp=highs[index],
            low_temp=lows[index],
            temperature_unit=settings.weather.temperature_unit,
            language=settings.language,
            is_day=True,
            thundersnow_f=settings.weather.thundersnow_f,
            thundersnow_c=settings.weather.thundersnow_c,
        )
        weather_days.append(
            WeatherDay(
                label=_weekday_label(dates[index], settings.language),
                source_weather_code=daily_weather_code,
                effective_weather_code=weather_code,
                condition_key=condition.key,
                icon_name=condition.icon_name,
                condition_label=condition.label,
                high_temp=round(highs[index]),
                low_temp=round(lows[index]),
                temperature_unit=settings.weather.temperature_unit,
                feels_like_high=round(feels_like_highs[index]) if index < len(feels_like_highs) else None,
                feels_like_low=round(feels_like_lows[index]) if index < len(feels_like_lows) else None,
                rain_chance=round(rain_chances[index]) if index < len(rain_chances) else None,
                wind_speed=round(wind_speeds[index]) if index < len(wind_speeds) else None,
                wind_speed_unit=wind_speed_unit,
                active_precip_override_used=active_precip_used,
                recent_snow_override_used=recent_snow_used,
                thundersnow_used=condition.icon_name == "thundersnow",
            )
        )

    return weather_days


def map_weather_code(code: int) -> str:
    return interpret_openmeteo_daily_condition(
        code,
        high_temp=None,
        low_temp=None,
        temperature_unit="fahrenheit",
        language="en",
    ).icon_name


def _weekday_label(iso_date: str, language: str) -> str:
    return weekday_abbrev(datetime.fromisoformat(iso_date), language)


def _resolve_current_day_code(settings: AppSettings, *, default_code: int, current: dict, hourly: dict, minutely: dict) -> tuple[int, bool, bool]:
    current_code = int(current.get("weather_code", default_code))
    current_temp = current.get("temperature_2m")
    current_time = current.get("time")
    if not current_time:
        return current_code, False, False

    minutely_override = apply_active_precip_override_minutely(
        current_code,
        temp_now=current_temp,
        temperature_unit=settings.weather.temperature_unit,
        minutely_times=minutely.get("time"),
        minutely_precipitation=minutely.get("precipitation"),
        minutely_snowfall=minutely.get("snowfall"),
        now_iso=current_time,
        snow_temp_f=settings.weather.snow_temp_f,
        snow_temp_c=settings.weather.snow_temp_c,
        recent_precip_minutes=settings.weather.recent_precip_minutes,
        recent_precip_mm=settings.weather.recent_precip_mm,
        recent_snow_mm_15=settings.weather.recent_snow_mm_15,
    )
    if minutely_override.used:
        return minutely_override.code, True, False

    hourly_override = apply_recent_snow_override_hourly(
        current_code,
        hourly_times=hourly.get("time"),
        hourly_snowfall=hourly.get("snowfall"),
        hourly_codes=hourly.get("weather_code"),
        now_iso=current_time,
        recent_snow_hours=settings.weather.recent_snow_hours,
        recent_snow_mm=settings.weather.recent_snow_mm,
    )
    if hourly_override.used:
        return hourly_override.code, False, True

    return current_code, False, False
