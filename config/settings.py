import json
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from models.mode import AppMode
from services.text import SUPPORTED_LANGUAGES


@dataclass(frozen=True)
class WeatherSettings:
    location_query: str
    country_code: str
    latitude: float
    longitude: float
    timezone: str
    temperature_unit: str
    thundersnow_f: float
    thundersnow_c: float
    snow_temp_f: float
    snow_temp_c: float
    recent_snow_hours: int
    recent_snow_mm: float
    recent_precip_minutes: int
    recent_precip_mm: float
    recent_snow_mm_15: float


@dataclass(frozen=True)
class CalendarSourceSettings:
    id: str
    source_type: str
    label: str
    url: str
    enabled: bool


@dataclass(frozen=True)
class AppSettings:
    language: str
    dashboard_title: str
    ics_url: str
    calendar_sources: list[CalendarSourceSettings]
    weather: WeatherSettings
    refresh_interval_minutes: int
    photo_folder: str
    photo_interval_seconds: int
    photo_shuffle_enabled: bool
    temporary_mode_timeout_minutes: int
    default_preview_mode: AppMode
    mode_state_file: str
    preview_output_enabled: bool
    hardware_display_enabled: bool
    spectra_mode: str
    palette_debug_enabled: bool
    settings_path: Path

    @property
    def project_root(self) -> Path:
        return self.settings_path.parent.parent


def load_settings(settings_path: str | Path) -> AppSettings:
    path = Path(settings_path)
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return parse_settings(raw, path)


def parse_settings(raw: dict, settings_path: str | Path) -> AppSettings:
    path = Path(settings_path)

    raw_sources = raw.get("calendar_sources") or []
    if not raw_sources and str(raw.get("ics_url", "")).strip():
        raw_sources = [
            {
                "id": "legacy-ics",
                "type": "ics",
                "label": "Primary Calendar Feed",
                "url": str(raw["ics_url"]),
                "enabled": True,
            }
        ]
    calendar_sources = [
        CalendarSourceSettings(
            id=str(source.get("id", f"source-{index}")),
            source_type=str(source.get("type", "ics")),
            label=str(source.get("label", f"Calendar {index + 1}")),
            url=str(source.get("url", "")),
            enabled=bool(source.get("enabled", True)),
        )
        for index, source in enumerate(raw_sources)
        if str(source.get("url", "")).strip()
    ]

    weather = WeatherSettings(
        location_query=str(raw["weather"].get("location_query", "")),
        country_code=str(raw["weather"].get("country_code", "")),
        latitude=float(raw["weather"]["latitude"]),
        longitude=float(raw["weather"]["longitude"]),
        timezone=str(raw["weather"]["timezone"]),
        temperature_unit=str(raw["weather"]["temperature_unit"]),
        thundersnow_f=float(raw["weather"].get("thundersnow_f", 34)),
        thundersnow_c=float(raw["weather"].get("thundersnow_c", 1)),
        snow_temp_f=float(raw["weather"].get("snow_temp_f", 34)),
        snow_temp_c=float(raw["weather"].get("snow_temp_c", 1)),
        recent_snow_hours=int(raw["weather"].get("recent_snow_hours", 2)),
        recent_snow_mm=float(raw["weather"].get("recent_snow_mm", 0)),
        recent_precip_minutes=int(raw["weather"].get("recent_precip_minutes", 60)),
        recent_precip_mm=float(raw["weather"].get("recent_precip_mm", 0)),
        recent_snow_mm_15=float(raw["weather"].get("recent_snow_mm_15", 0)),
    )

    settings = AppSettings(
        language=str(raw.get("language", "en")),
        dashboard_title=str(raw.get("dashboard_title", "Inky Planner")),
        ics_url=str(raw["ics_url"]),
        calendar_sources=calendar_sources,
        weather=weather,
        refresh_interval_minutes=int(raw["refresh_interval_minutes"]),
        photo_folder=str(raw["photo_folder"]),
        photo_interval_seconds=int(raw.get("photo_interval_seconds", 180)),
        photo_shuffle_enabled=bool(raw.get("photo_shuffle_enabled", False)),
        temporary_mode_timeout_minutes=int(raw["temporary_mode_timeout_minutes"]),
        default_preview_mode=AppMode(str(raw.get("default_preview_mode", "dashboard"))),
        mode_state_file=str(raw.get("mode_state_file", "state/mode_state.json")),
        preview_output_enabled=bool(raw.get("preview_output_enabled", False)),
        hardware_display_enabled=bool(raw.get("hardware_display_enabled", False)),
        spectra_mode=str(raw.get("spectra_mode", "atkinson")),
        palette_debug_enabled=bool(raw.get("palette_debug_enabled", False)),
        settings_path=path,
    )
    _validate_settings(settings)
    return settings


def _validate_settings(settings: AppSettings) -> None:
    if not settings.ics_url.strip() and not any(
        source.enabled and source.url.strip()
        for source in settings.calendar_sources
    ):
        raise ValueError("Invalid settings: configure at least one calendar feed")

    try:
        ZoneInfo(settings.weather.timezone)
    except Exception as exc:
        raise ValueError(f"Invalid settings: unsupported timezone '{settings.weather.timezone}'") from exc

    if settings.weather.temperature_unit not in {"fahrenheit", "celsius"}:
        raise ValueError("Invalid settings: weather.temperature_unit must be 'fahrenheit' or 'celsius'")

    if settings.language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Invalid settings: language must be one of {', '.join(SUPPORTED_LANGUAGES)}")

    if settings.spectra_mode not in {"off", "quantize", "floyd", "atkinson"}:
        raise ValueError("Invalid settings: spectra_mode must be one of off, quantize, floyd, atkinson")

    if settings.refresh_interval_minutes <= 0:
        raise ValueError("Invalid settings: refresh_interval_minutes must be greater than 0")

    if settings.photo_interval_seconds <= 0:
        raise ValueError("Invalid settings: photo_interval_seconds must be greater than 0")

    if settings.temporary_mode_timeout_minutes <= 0:
        raise ValueError("Invalid settings: temporary_mode_timeout_minutes must be greater than 0")

    if settings.weather.recent_snow_hours < 0:
        raise ValueError("Invalid settings: weather.recent_snow_hours must be 0 or greater")

    if settings.weather.recent_precip_minutes < 0:
        raise ValueError("Invalid settings: weather.recent_precip_minutes must be 0 or greater")
