from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CalendarEvent:
    start_time: str
    compact_start_time: str = ""
    raw_title: str = ""
    display_title: str = ""
    dashboard_title: str = ""
    is_all_day: bool = False
    is_multi_day: bool = False

    def __post_init__(self) -> None:
        if not self.compact_start_time:
            object.__setattr__(self, "compact_start_time", self.start_time)
        if not self.dashboard_title:
            object.__setattr__(self, "dashboard_title", self.display_title)


@dataclass(frozen=True)
class CalendarDay:
    label: str
    date_value: date
    multi_day_event: CalendarEvent | None
    all_day_events: list[CalendarEvent]
    timed_events: list[CalendarEvent]
    visible_events: list[CalendarEvent]
    overflow_count: int = 0
