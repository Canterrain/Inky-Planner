from dataclasses import dataclass

from models.calendar import CalendarDay
from models.weather import WeatherDay


@dataclass(frozen=True)
class DataSourceStatus:
    source: str
    state: str
    message: str

    @property
    def is_live(self) -> bool:
        return self.state == "live"


@dataclass(frozen=True)
class DashboardData:
    language: str
    title: str
    updated_at: str
    calendar_days: list[CalendarDay]
    weather_days: list[WeatherDay]
    calendar_status: DataSourceStatus
    weather_status: DataSourceStatus
