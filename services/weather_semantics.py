from dataclasses import dataclass

from services.text import translate


@dataclass(frozen=True)
class WeatherCondition:
    key: str
    icon_name: str
    label: str


@dataclass(frozen=True)
class WeatherOverrideResult:
    code: int
    used: bool
    reason: str | None = None


def interpret_openmeteo_daily_condition(
    weather_code: int,
    *,
    high_temp: int | float | None,
    low_temp: int | float | None,
    temperature_unit: str,
    language: str = "en",
    is_day: bool = True,
    thundersnow_f: float = 34,
    thundersnow_c: float = 1,
) -> WeatherCondition:
    normalized = int(weather_code)

    if _is_thundersnow(
        normalized,
        high_temp=high_temp,
        low_temp=low_temp,
        temperature_unit=temperature_unit,
        thundersnow_f=thundersnow_f,
        thundersnow_c=thundersnow_c,
    ):
        return WeatherCondition("thundersnow", "thundersnow", translate(language, "condition.thundersnow"))

    if normalized == 0:
        return WeatherCondition("clear", "clear-day" if is_day else "clear-night", translate(language, "condition.clear"))

    if normalized in (1, 2):
        return WeatherCondition("partly_cloudy", "partlycloudy-day" if is_day else "partlycloudy-night", translate(language, "condition.partly_cloudy"))

    if normalized == 3:
        return WeatherCondition("cloudy", "cloudy", translate(language, "condition.cloudy"))

    if normalized in (45, 48):
        return WeatherCondition("fog", "fog", translate(language, "condition.fog"))

    if 51 <= normalized <= 57:
        return WeatherCondition("showers", "showers-day" if is_day else "showers-night", translate(language, "condition.showers"))

    if normalized in (66, 67):
        return WeatherCondition("sleet", "sleet", translate(language, "condition.sleet"))

    if 61 <= normalized <= 65:
        return WeatherCondition("rain", "rain", translate(language, "condition.rain"))

    if 71 <= normalized <= 77:
        return WeatherCondition("snow", "snow", translate(language, "condition.snow"))

    if normalized in (80, 81, 82):
        return WeatherCondition("showers", "showers-day" if is_day else "showers-night", translate(language, "condition.showers"))

    if normalized in (85, 86):
        return WeatherCondition("snow", "snow", translate(language, "condition.snow"))

    if normalized in (95, 96, 99):
        return WeatherCondition("thunderstorm", "thunderstorm", translate(language, "condition.thunderstorm"))

    return WeatherCondition("cloudy", "cloudy", translate(language, "condition.cloudy"))


def _is_thundersnow(
    weather_code: int,
    *,
    high_temp: int | float | None,
    low_temp: int | float | None,
    temperature_unit: str,
    thundersnow_f: float,
    thundersnow_c: float,
) -> bool:
    if weather_code not in (95, 96, 99):
        return False

    representative_temp = _representative_temp(high_temp, low_temp)
    if representative_temp is None:
        return False

    threshold = thundersnow_f if temperature_unit == "fahrenheit" else thundersnow_c
    return representative_temp <= threshold


def _representative_temp(high_temp: int | float | None, low_temp: int | float | None) -> float | None:
    if high_temp is None and low_temp is None:
        return None
    if high_temp is None:
        return float(low_temp)
    if low_temp is None:
        return float(high_temp)
    return float(high_temp + low_temp) / 2.0


def apply_recent_snow_override_hourly(
    current_code: int,
    *,
    hourly_times: list[str] | None,
    hourly_snowfall: list[float | int] | None,
    hourly_codes: list[int] | None,
    now_iso: str,
    recent_snow_hours: int = 2,
    recent_snow_mm: float = 0,
) -> WeatherOverrideResult:
    if not hourly_times or hourly_snowfall is None or hourly_codes is None:
        return WeatherOverrideResult(code=current_code, used=False)

    best_index = _find_nearest_index_by_time(hourly_times, now_iso)
    if best_index < 0:
        return WeatherOverrideResult(code=current_code, used=False)

    start_index = max(0, best_index - max(0, recent_snow_hours))
    saw_snow = False
    saw_snow_code = False
    for index in range(start_index, best_index + 1):
        snowfall = float(hourly_snowfall[index] or 0)
        code = int(hourly_codes[index] or -1)
        if snowfall > recent_snow_mm:
            saw_snow = True
        if (71 <= code <= 77) or code in {85, 86}:
            saw_snow_code = True

    if not saw_snow and not saw_snow_code:
        return WeatherOverrideResult(code=current_code, used=False)

    return WeatherOverrideResult(code=73, used=True, reason="recent_snow")


def apply_active_precip_override_minutely(
    current_code: int,
    *,
    temp_now: int | float | None,
    temperature_unit: str,
    minutely_times: list[str] | None,
    minutely_precipitation: list[float | int] | None,
    minutely_snowfall: list[float | int] | None,
    now_iso: str,
    snow_temp_f: float = 34,
    snow_temp_c: float = 1,
    recent_precip_minutes: int = 60,
    recent_precip_mm: float = 0,
    recent_snow_mm_15: float = 0,
) -> WeatherOverrideResult:
    if not minutely_times or (minutely_precipitation is None and minutely_snowfall is None):
        return WeatherOverrideResult(code=current_code, used=False)

    best_index = _find_nearest_index_by_time(minutely_times, now_iso)
    if best_index < 0:
        return WeatherOverrideResult(code=current_code, used=False)

    samples_back = max(1, (max(0, recent_precip_minutes) + 14) // 15)
    start_index = max(0, best_index - samples_back)
    saw_any_precip = False
    saw_any_snowfall = False
    for index in range(start_index, best_index + 1):
        precip = float(minutely_precipitation[index] or 0) if minutely_precipitation is not None else 0
        snowfall = float(minutely_snowfall[index] or 0) if minutely_snowfall is not None else 0
        if precip > recent_precip_mm:
            saw_any_precip = True
        if snowfall > recent_snow_mm_15:
            saw_any_snowfall = True

    if not saw_any_precip and not saw_any_snowfall:
        return WeatherOverrideResult(code=current_code, used=False)

    snow_threshold = snow_temp_f if temperature_unit == "fahrenheit" else snow_temp_c
    is_snow_by_temp = temp_now is not None and float(temp_now) <= snow_threshold
    if saw_any_snowfall or (saw_any_precip and is_snow_by_temp):
        return WeatherOverrideResult(code=73, used=True, reason="active_snow")

    return WeatherOverrideResult(code=61, used=True, reason="active_rain")


def _find_nearest_index_by_time(time_values: list[str], target_iso: str) -> int:
    target = _parse_iso_minutes(target_iso)
    if target is None:
        return -1

    best_index = -1
    best_diff = None
    for index, time_value in enumerate(time_values):
        parsed = _parse_iso_minutes(time_value)
        if parsed is None:
            continue
        diff = abs(parsed - target)
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_index = index
    return best_index


def _parse_iso_minutes(value: str) -> int | None:
    from datetime import datetime

    try:
        return int(datetime.fromisoformat(value).timestamp() // 60)
    except Exception:
        return None
