import unittest
from datetime import date
from unittest.mock import patch

from config.settings import load_settings
from services.dashboard_data import build_dashboard_data


class DashboardDataTests(unittest.TestCase):
    def test_calendar_fallback_is_marked_in_status(self) -> None:
        with patch("services.dashboard_data.fetch_calendar_days", side_effect=RuntimeError("boom")):
            data = build_dashboard_data("config/settings.json")

        self.assertEqual("fallback", data.calendar_status.state)
        self.assertIn("USING SAMPLE DATA", data.calendar_status.message)

    def test_weather_fallback_is_marked_in_status(self) -> None:
        with patch("services.dashboard_data.fetch_weather_days", side_effect=RuntimeError("boom")):
            data = build_dashboard_data("config/settings.json")

        self.assertEqual("fallback", data.weather_status.state)
        self.assertIn("USING SAMPLE DATA", data.weather_status.message)


if __name__ == "__main__":
    unittest.main()
