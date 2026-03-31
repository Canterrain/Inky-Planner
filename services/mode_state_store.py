import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from config.settings import AppSettings
from models.mode import AppMode, ModeState
from services.file_io import atomic_write_text
from services.mode_state import build_mode_state


def load_persisted_mode_state(settings: AppSettings, now: datetime) -> ModeState:
    path = _resolve_state_path(settings)
    if not path.exists():
        return build_mode_state(settings, AppMode.DASHBOARD, now)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        current_mode = AppMode(payload["current_mode"])
        entered_at = datetime.fromisoformat(payload["entered_at"])
        auto_return_target = AppMode(payload["auto_return_target"]) if payload.get("auto_return_target") else None
        timeout_duration = (
            timedelta(seconds=float(payload["timeout_duration_seconds"]))
            if payload.get("timeout_duration_seconds") is not None
            else None
        )

        return ModeState(
            current_mode=current_mode,
            entered_at=entered_at,
            should_auto_return=bool(payload["should_auto_return"]),
            auto_return_target=auto_return_target,
            timeout_duration=timeout_duration,
        )
    except Exception:
        return build_mode_state(settings, AppMode.DASHBOARD, now)


def save_mode_state(settings: AppSettings, state: ModeState) -> Path:
    path = _resolve_state_path(settings)
    payload = {
        "current_mode": state.current_mode.value,
        "entered_at": state.entered_at.isoformat(),
        "should_auto_return": state.should_auto_return,
        "auto_return_target": state.auto_return_target.value if state.auto_return_target else None,
        "timeout_duration_seconds": state.timeout_duration.total_seconds() if state.timeout_duration else None,
    }
    return atomic_write_text(path, json.dumps(payload, indent=2))


def resolve_and_persist_mode(settings: AppSettings, state: ModeState, now: datetime) -> ModeState:
    active_mode = state.resolve_active_mode(now)
    if active_mode == state.current_mode:
        return state

    new_state = build_mode_state(settings, active_mode, now)
    save_mode_state(settings, new_state)
    return new_state


def _resolve_state_path(settings: AppSettings) -> Path:
    raw_path = Path(settings.mode_state_file)
    if raw_path.is_absolute():
        return raw_path
    return settings.project_root / raw_path
