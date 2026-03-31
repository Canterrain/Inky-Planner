from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class AppMode(str, Enum):
    DASHBOARD = "dashboard"
    TODAY = "today"
    TOMORROW = "tomorrow"
    PHOTO = "photo"


@dataclass(frozen=True)
class ModeState:
    current_mode: AppMode
    entered_at: datetime
    should_auto_return: bool
    auto_return_target: AppMode | None
    timeout_duration: timedelta | None

    def resolve_active_mode(self, now: datetime) -> AppMode:
        if not self.should_auto_return or self.timeout_duration is None or self.auto_return_target is None:
            return self.current_mode
        if now >= self.entered_at + self.timeout_duration:
            return self.auto_return_target
        return self.current_mode
