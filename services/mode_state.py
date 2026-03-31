from datetime import datetime, timedelta

from config.settings import AppSettings
from models.mode import AppMode, ModeState


TEMPORARY_MODES = {AppMode.TODAY, AppMode.TOMORROW}


def build_mode_state(settings: AppSettings, mode: AppMode, entered_at: datetime) -> ModeState:
    should_auto_return = mode in TEMPORARY_MODES
    return ModeState(
        current_mode=mode,
        entered_at=entered_at,
        should_auto_return=should_auto_return,
        auto_return_target=AppMode.DASHBOARD if should_auto_return else None,
        timeout_duration=timedelta(minutes=settings.temporary_mode_timeout_minutes) if should_auto_return else None,
    )
