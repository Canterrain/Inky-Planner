from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from models.dashboard import DashboardData
from services.dashboard_data import build_dashboard_data


DASHBOARD_CACHE_TTL_SECONDS = 180


@dataclass
class _DashboardCacheEntry:
    settings_mtime_ns: int
    built_at_monotonic: float
    data: DashboardData


_CACHE: dict[Path, _DashboardCacheEntry] = {}


def get_dashboard_data_cached(
    settings_path: str | Path,
    *,
    max_age_seconds: int = DASHBOARD_CACHE_TTL_SECONDS,
) -> DashboardData:
    path = Path(settings_path).resolve()
    settings_mtime_ns = path.stat().st_mtime_ns
    cached = _CACHE.get(path)
    now = monotonic()

    if (
        cached is not None
        and cached.settings_mtime_ns == settings_mtime_ns
        and now - cached.built_at_monotonic <= max_age_seconds
    ):
        return cached.data

    data = build_dashboard_data(path)
    _CACHE[path] = _DashboardCacheEntry(
        settings_mtime_ns=settings_mtime_ns,
        built_at_monotonic=now,
        data=data,
    )
    return data


def clear_dashboard_data_cache(settings_path: str | Path | None = None) -> None:
    if settings_path is None:
        _CACHE.clear()
        return
    _CACHE.pop(Path(settings_path).resolve(), None)
