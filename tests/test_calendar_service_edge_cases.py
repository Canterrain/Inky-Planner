import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from config.settings import load_settings
from services.calendar_service import _build_calendar_days


class CalendarServiceEdgeCaseTests(unittest.TestCase):
    def test_skips_cancelled_events(self) -> None:
        calendar = Calendar()
        event = Event()
        event.add("summary", "Cancelled Thing")
        event.add("dtstart", date(2026, 3, 30))
        event.add("dtend", date(2026, 3, 31))
        event.add("status", "CANCELLED")
        calendar.add_component(event)

        settings = load_settings("config/settings.json")
        days = _build_calendar_days(calendar, settings, date(2026, 3, 30), 5, ZoneInfo(settings.weather.timezone))

        self.assertIsNone(days[0].multi_day_event)
        self.assertEqual([], days[0].all_day_events)
        self.assertEqual([], days[0].timed_events)

    def test_ignores_components_without_dtstart(self) -> None:
        calendar = Calendar()
        event = Event()
        event.add("summary", "Broken Event")
        calendar.add_component(event)

        settings = load_settings("config/settings.json")
        days = _build_calendar_days(calendar, settings, date(2026, 3, 30), 5, ZoneInfo(settings.weather.timezone))

        self.assertEqual([], days[0].timed_events)

    def test_skips_timed_events_with_end_before_start(self) -> None:
        calendar = Calendar()
        event = Event()
        event.add("summary", "Broken Time Event")
        settings = load_settings("config/settings.json")
        timezone = ZoneInfo(settings.weather.timezone)
        event.add("dtstart", datetime(2026, 3, 30, 12, 0, tzinfo=timezone))
        event.add("dtend", datetime(2026, 3, 30, 11, 0, tzinfo=timezone))
        calendar.add_component(event)

        days = _build_calendar_days(calendar, settings, date(2026, 3, 30), 5, ZoneInfo(settings.weather.timezone))

        self.assertEqual([], days[0].timed_events)

    def test_respects_exdate_for_recurring_event(self) -> None:
        calendar = Calendar()
        event = Event()
        settings = load_settings("config/settings.json")
        timezone = ZoneInfo(settings.weather.timezone)
        event.add("summary", "Recurring Skip")
        event.add("dtstart", datetime(2026, 3, 30, 9, 0, tzinfo=timezone))
        event.add("dtend", datetime(2026, 3, 30, 10, 0, tzinfo=timezone))
        event.add("rrule", {"freq": ["daily"], "count": [3]})
        event.add("exdate", datetime(2026, 3, 31, 9, 0, tzinfo=timezone))
        calendar.add_component(event)

        days = _build_calendar_days(calendar, settings, date(2026, 3, 30), 5, timezone)

        self.assertEqual(1, len(days[0].timed_events))
        self.assertEqual([], days[1].timed_events)
        self.assertEqual(1, len(days[2].timed_events))

    def test_same_time_events_sort_by_title(self) -> None:
        calendar = Calendar()
        settings = load_settings("config/settings.json")
        timezone = ZoneInfo(settings.weather.timezone)

        first = Event()
        first.add("summary", "Zoo Visit")
        first.add("dtstart", datetime(2026, 3, 30, 9, 0, tzinfo=timezone))
        first.add("dtend", datetime(2026, 3, 30, 10, 0, tzinfo=timezone))
        calendar.add_component(first)

        second = Event()
        second.add("summary", "Alpha Meeting")
        second.add("dtstart", datetime(2026, 3, 30, 9, 0, tzinfo=timezone))
        second.add("dtend", datetime(2026, 3, 30, 10, 0, tzinfo=timezone))
        calendar.add_component(second)

        days = _build_calendar_days(calendar, settings, date(2026, 3, 30), 5, timezone)

        self.assertEqual("Alpha Meeting", days[0].timed_events[0].display_title)
        self.assertEqual("Zoo Visit", days[0].timed_events[1].display_title)


if __name__ == "__main__":
    unittest.main()
