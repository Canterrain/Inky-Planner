from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from config.settings import load_settings
from services.file_io import atomic_write_text


def _safe_getlist(form: dict, key: str) -> list[str]:
    getter = getattr(form, "getlist", None)
    if callable(getter):
        try:
            return getter(key)
        except Exception:
            return []
    value = form.get(key, [])
    if isinstance(value, list):
        return value
    return [value]


def load_raw_settings(settings_path: str | Path) -> dict:
    path = Path(settings_path)
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return _normalize_raw_settings(raw)


def save_raw_settings(settings_path: str | Path, raw_settings: dict) -> None:
    path = Path(settings_path)
    original = path.read_text(encoding="utf-8") if path.exists() else None
    rendered = json.dumps(raw_settings, indent=2)
    atomic_write_text(path, rendered)
    try:
        load_settings(path)
    except Exception:
        if original is not None:
            atomic_write_text(path, original)
        raise


def build_web_settings_update(raw_settings: dict, form: dict) -> dict:
    updated = _normalize_raw_settings(raw_settings)
    updated["dashboard_title"] = form.get("dashboard_title", updated.get("dashboard_title", "Inky Planner")).strip() or "Inky Planner"
    updated["language"] = form.get("language", updated.get("language", "en")).strip() or "en"
    updated["photo_folder"] = form.get("photo_folder", updated.get("photo_folder", "")).strip()
    updated["photo_interval_seconds"] = int(form.get("photo_interval_seconds", updated.get("photo_interval_seconds", 180)))
    updated["photo_shuffle_enabled"] = form.get("photo_shuffle_enabled") == "on"

    weather = dict(updated.get("weather", {}))
    weather["location_query"] = form.get("weather_location_query", weather.get("location_query", "")).strip()
    weather["country_code"] = form.get("weather_country_code", weather.get("country_code", "")).strip().upper()
    weather["latitude"] = float(form.get("weather_latitude", weather.get("latitude", 0)))
    weather["longitude"] = float(form.get("weather_longitude", weather.get("longitude", 0)))
    weather["timezone"] = form.get("weather_timezone", weather.get("timezone", "")).strip()
    weather["temperature_unit"] = form.get("weather_temperature_unit", weather.get("temperature_unit", "fahrenheit")).strip()
    weather["thundersnow_f"] = float(form.get("weather_thundersnow_f", weather.get("thundersnow_f", 34)))
    weather["thundersnow_c"] = float(form.get("weather_thundersnow_c", weather.get("thundersnow_c", 1)))
    weather["snow_temp_f"] = float(form.get("weather_snow_temp_f", weather.get("snow_temp_f", 34)))
    weather["snow_temp_c"] = float(form.get("weather_snow_temp_c", weather.get("snow_temp_c", 1)))
    weather["recent_snow_hours"] = int(form.get("weather_recent_snow_hours", weather.get("recent_snow_hours", 2)))
    weather["recent_snow_mm"] = float(form.get("weather_recent_snow_mm", weather.get("recent_snow_mm", 0)))
    weather["recent_precip_minutes"] = int(form.get("weather_recent_precip_minutes", weather.get("recent_precip_minutes", 60)))
    weather["recent_precip_mm"] = float(form.get("weather_recent_precip_mm", weather.get("recent_precip_mm", 0)))
    weather["recent_snow_mm_15"] = float(form.get("weather_recent_snow_mm_15", weather.get("recent_snow_mm_15", 0)))
    updated["weather"] = weather

    source_ids = _safe_getlist(form, "calendar_source_id")
    source_labels = _safe_getlist(form, "calendar_source_label")
    source_types = _safe_getlist(form, "calendar_source_type")
    source_urls = _safe_getlist(form, "calendar_source_url")
    enabled_source_ids = set(_safe_getlist(form, "calendar_source_enabled"))
    calendar_sources = []
    for index, raw_url in enumerate(source_urls):
        url = raw_url.strip()
        if not url:
            continue
        source_id = source_ids[index].strip() if index < len(source_ids) else ""
        final_id = source_id or f"source-{uuid4().hex[:8]}"
        label = source_labels[index].strip() if index < len(source_labels) else ""
        source_type = source_types[index].strip() if index < len(source_types) else "ics"
        enabled = final_id in enabled_source_ids or (not source_id and "" in enabled_source_ids)
        calendar_sources.append(
            {
                "id": final_id,
                "type": source_type or "ics",
                "label": label or f"Calendar Feed {len(calendar_sources) + 1}",
                "url": url,
                "enabled": enabled,
            }
        )

    updated["calendar_sources"] = calendar_sources
    if calendar_sources:
        primary = next((source for source in calendar_sources if source["enabled"] and source.get("url")), None)
        if primary is not None:
            updated["ics_url"] = primary["url"]

    return updated


def apply_geocoding_result(raw_settings: dict, *, location_query: str, country_code: str, result) -> dict:
    updated = _normalize_raw_settings(raw_settings)
    weather = dict(updated.get("weather", {}))
    weather["location_query"] = location_query.strip()
    weather["country_code"] = country_code.strip().upper()
    weather["latitude"] = result.latitude
    weather["longitude"] = result.longitude
    if result.timezone:
        weather["timezone"] = result.timezone
    updated["weather"] = weather
    return updated


def _normalize_raw_settings(raw_settings: dict) -> dict:
    updated = dict(raw_settings)
    updated.setdefault("photo_folder", "assets/photos")
    updated.setdefault("photo_interval_seconds", 180)
    updated.setdefault("photo_shuffle_enabled", False)
    updated.setdefault("spectra_mode", "atkinson")
    weather = dict(updated.get("weather", {}))
    weather.setdefault("location_query", "")
    weather.setdefault("country_code", "")
    updated["weather"] = weather
    raw_sources = updated.get("calendar_sources") or []
    if not raw_sources and str(updated.get("ics_url", "")).strip():
        raw_sources = [
            {
                "id": "legacy-ics",
                "type": "ics",
                "label": "Primary Calendar Feed",
                "url": str(updated["ics_url"]).strip(),
                "enabled": True,
            }
        ]
    updated["calendar_sources"] = raw_sources
    return updated
