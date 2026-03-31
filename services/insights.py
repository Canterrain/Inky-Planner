from models.calendar import CalendarDay
from models.weather import WeatherDay
from services.text import translate


def build_day_insights(day: CalendarDay, weather: WeatherDay, *, mode_name: str, language: str = "en") -> list[str]:
    insights: list[str] = []

    weather_line = _weather_insight(weather, mode_name, language)
    if weather_line:
        insights.append(weather_line)

    next_event_line = _next_event_insight(day, mode_name, language)
    if next_event_line:
        insights.append(next_event_line)

    return insights[:2]


def _weather_insight(weather: WeatherDay, mode_name: str, language: str) -> str:
    subject = translate(language, f"subject.{mode_name}")
    icon = weather.icon_name
    spread = weather.high_temp - weather.low_temp

    if icon in {"rain", "showers-day", "showers-night"}:
        return translate(language, "insight.rain_likely", subject=subject)
    if icon == "thunderstorm":
        return translate(language, "insight.storm_risk", subject=subject)
    if icon == "snow":
        return translate(language, "insight.snow_expected", subject=subject)
    if icon == "sleet":
        return translate(language, "insight.wintry_mix", subject=subject)
    if icon == "wind":
        return translate(language, "insight.windy_conditions", subject=subject)
    if icon == "fog":
        return translate(language, "insight.low_visibility", subject=subject)
    if spread >= 15:
        return translate(language, "insight.cold_morning_warmer_later")
    if weather.high_temp <= 45:
        return translate(language, "insight.cool_through_day")
    if icon in {"clear-day", "clear-night"}:
        return translate(language, "insight.clear_steady")
    return translate(language, "insight.conditions", condition=weather.condition_label, subject=subject)


def _next_event_insight(day: CalendarDay, mode_name: str, language: str) -> str | None:
    if day.timed_events:
        event = day.timed_events[0]
        if mode_name == "today":
            return translate(language, "insight.next_event", title=event.display_title, time=event.start_time)
        return translate(language, "insight.first_event", title=event.display_title, time=event.start_time)

    if day.all_day_events:
        return translate(language, "insight.all_day", title=day.all_day_events[0].display_title)

    if day.multi_day_event:
        return translate(language, "insight.all_day", title=day.multi_day_event.display_title)

    return None
