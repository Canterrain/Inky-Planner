from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherDay:
    label: str
    source_weather_code: int | None
    effective_weather_code: int | None
    condition_key: str
    icon_name: str
    condition_label: str
    high_temp: int
    low_temp: int
    temperature_unit: str = "fahrenheit"
    feels_like_high: int | None = None
    feels_like_low: int | None = None
    rain_chance: int | None = None
    wind_speed: int | None = None
    wind_speed_unit: str = "mph"
    active_precip_override_used: bool = False
    recent_snow_override_used: bool = False
    thundersnow_used: bool = False
