from dataclasses import dataclass

from services.weather_semantics import interpret_openmeteo_daily_condition


@dataclass(frozen=True)
class WeatherIconSpec:
    icon_name: str
    label: str


def map_weather_code_to_icon(code: int, *, is_day: bool = True) -> WeatherIconSpec:
    condition = interpret_openmeteo_daily_condition(
        code,
        high_temp=None,
        low_temp=None,
        temperature_unit="fahrenheit",
        language="en",
        is_day=is_day,
    )
    return WeatherIconSpec(condition.icon_name, condition.label)


SUPPORTED_ICON_NAMES = [
    "clear-day",
    "clear-night",
    "partlycloudy-day",
    "partlycloudy-night",
    "cloudy",
    "fog",
    "rain",
    "showers-day",
    "showers-night",
    "thunderstorm",
    "snow",
    "sleet",
    "thundersnow",
]
