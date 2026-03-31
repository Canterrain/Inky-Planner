import unittest
from datetime import date

from config.settings import load_settings
from services.calendar_service import _compact_time, _dashboard_title, fetch_calendar_days
from datetime import datetime


class CalendarServiceTests(unittest.TestCase):
    def test_reads_local_sample_ics(self) -> None:
        settings = load_settings("config/settings.json")
        days = fetch_calendar_days(settings, date(2026, 3, 27))

        self.assertEqual(5, len(days))
        self.assertEqual("Fri", days[0].label)
        self.assertGreaterEqual(len(days[0].visible_events), 1)
        self.assertGreaterEqual(len(days[0].timed_events), len(days[0].visible_events))

    def test_detects_multi_day_and_single_day_all_day_events(self) -> None:
        settings = load_settings("config/settings.json")
        days = fetch_calendar_days(settings, date(2026, 3, 31))

        self.assertIsNotNone(days[0].multi_day_event)
        self.assertEqual("Sam: Spring Break Trip", days[0].multi_day_event.display_title)
        self.assertTrue(days[0].multi_day_event.is_multi_day)
        self.assertEqual("Sam: Spring Break Trip", days[1].multi_day_event.display_title)
        self.assertIsNone(days[2].multi_day_event)

        self.assertGreaterEqual(len(days[0].all_day_events), 1)
        self.assertTrue(days[0].all_day_events[0].is_all_day)
        self.assertFalse(days[0].all_day_events[0].is_multi_day)

    def test_dashboard_title_compacts_common_noise(self) -> None:
        self.assertEqual("Dentist appt", _dashboard_title("Sam - Dentist Appointment"))
        self.assertEqual("Parent comm. mtg", _dashboard_title("Alex: Parent Committee Meeting"))
        self.assertEqual("Maundy Thurs service", _dashboard_title("Maundy Thursday service"))

    def test_compact_time_uses_short_dashboard_format(self) -> None:
        self.assertEqual("10A", _compact_time(datetime(2026, 3, 31, 10, 0)))
        self.assertEqual("10:30A", _compact_time(datetime(2026, 3, 31, 10, 30)))


if __name__ == "__main__":
    unittest.main()
