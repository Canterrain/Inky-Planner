from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from config.settings import AppSettings
from services.file_io import atomic_write_text
from services.photo_service import list_photos


@dataclass
class PhotoSlideshowState:
    order: list[str]
    position: int
    last_changed_at: datetime


def current_photo(settings: AppSettings) -> Path | None:
    photos = list_photos(settings.photo_folder, settings.project_root)
    if not photos:
        return None
    now = datetime.now(ZoneInfo(settings.weather.timezone))
    state = _load_or_initialize_state(settings, photos, now)
    return _resolve_photo_path(photos, state)


def reset_slideshow_timer(settings: AppSettings) -> None:
    photos = list_photos(settings.photo_folder, settings.project_root)
    if not photos:
        return
    now = datetime.now(ZoneInfo(settings.weather.timezone))
    state = _load_or_initialize_state(settings, photos, now)
    state.last_changed_at = now
    _save_state(settings, state)


def advance_photo_if_due(settings: AppSettings) -> bool:
    photos = list_photos(settings.photo_folder, settings.project_root)
    if len(photos) <= 1:
        return False

    now = datetime.now(ZoneInfo(settings.weather.timezone))
    state = _load_or_initialize_state(settings, photos, now)
    if now < state.last_changed_at + timedelta(seconds=settings.photo_interval_seconds):
        return False

    current_name = state.order[state.position] if state.order else None
    state.position += 1
    if state.position >= len(state.order):
        if settings.photo_shuffle_enabled:
            state.order = _build_order(photos, shuffle=True, avoid_first=current_name)
        state.position = 0
    state.last_changed_at = now
    _save_state(settings, state)
    return True


def _load_or_initialize_state(settings: AppSettings, photos: list[Path], now: datetime) -> PhotoSlideshowState:
    state_path = _state_path(settings)
    current_names = [photo.name for photo in photos]
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        state = PhotoSlideshowState(
            order=[name for name in payload.get("order", []) if name in current_names],
            position=int(payload.get("position", 0)),
            last_changed_at=datetime.fromisoformat(payload["last_changed_at"]),
        )
    except Exception:
        state = PhotoSlideshowState(order=[], position=0, last_changed_at=now)

    if sorted(state.order) != sorted(current_names):
        state.order = _build_order(photos, shuffle=settings.photo_shuffle_enabled)
        state.position = 0
        state.last_changed_at = now
        _save_state(settings, state)
    elif state.position >= len(state.order):
        state.position = 0
        _save_state(settings, state)

    if not state.order:
        state.order = _build_order(photos, shuffle=settings.photo_shuffle_enabled)
        state.position = 0
        state.last_changed_at = now
        _save_state(settings, state)

    return state


def _resolve_photo_path(photos: list[Path], state: PhotoSlideshowState) -> Path | None:
    mapping = {photo.name: photo for photo in photos}
    if not state.order:
        return photos[0] if photos else None
    return mapping.get(state.order[state.position], photos[0] if photos else None)


def _build_order(photos: list[Path], *, shuffle: bool, avoid_first: str | None = None) -> list[str]:
    names = [photo.name for photo in photos]
    if shuffle and len(names) > 1:
        random.shuffle(names)
        if avoid_first and names[0] == avoid_first:
            names.append(names.pop(0))
    return names


def _save_state(settings: AppSettings, state: PhotoSlideshowState) -> None:
    path = _state_path(settings)
    payload = {
        "order": state.order,
        "position": state.position,
        "last_changed_at": state.last_changed_at.isoformat(),
    }
    atomic_write_text(path, json.dumps(payload, indent=2))


def _state_path(settings: AppSettings) -> Path:
    return settings.project_root / "state" / "photo_slideshow.json"
