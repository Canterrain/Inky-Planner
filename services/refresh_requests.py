from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config.settings import AppSettings
from services.file_io import atomic_write_text


def request_refresh(settings: AppSettings) -> Path:
    path = _resolve_refresh_request_path(settings)
    return atomic_write_text(path, datetime.utcnow().isoformat())


def consume_refresh_request(settings: AppSettings) -> bool:
    path = _resolve_refresh_request_path(settings)
    if not path.exists():
        return False
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


def _resolve_refresh_request_path(settings: AppSettings) -> Path:
    return settings.project_root / "state" / "refresh_request.flag"
