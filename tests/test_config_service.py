import json
import tempfile
import unittest
from pathlib import Path

from services.config_service import build_web_settings_update, save_raw_settings


class ConfigServiceTests(unittest.TestCase):
    def test_updates_dashboard_title_and_calendar_sources(self) -> None:
        raw = {
            "dashboard_title": "Old",
            "language": "en",
            "ics_url": "a.ics",
            "calendar_sources": [
                {
                    "id": "legacy-ics",
                    "type": "ics",
                    "label": "Primary Calendar Feed",
                    "url": "a.ics",
                    "enabled": True,
                }
            ],
            "photo_folder": "photos",
            "photo_interval_seconds": 180,
            "photo_shuffle_enabled": False,
            "weather": {
                "location_query": "",
                "country_code": "",
                "latitude": 1,
                "longitude": 2,
                "timezone": "America/New_York",
                "temperature_unit": "fahrenheit",
                "thundersnow_f": 34,
                "thundersnow_c": 1,
                "snow_temp_f": 34,
                "snow_temp_c": 1,
                "recent_snow_hours": 2,
                "recent_snow_mm": 0,
                "recent_precip_minutes": 60,
                "recent_precip_mm": 0,
                "recent_snow_mm_15": 0,
            },
        }

        class FakeForm(dict):
            def getlist(self, key):
                return self[key]

        form = FakeForm(
            dashboard_title="Inky Planner",
            language="en",
            photo_folder="assets/photos",
            photo_interval_seconds="45",
            photo_shuffle_enabled="on",
            calendar_source_id=["legacy-ics", ""],
            calendar_source_label=["Family", "Work"],
            calendar_source_type=["google", "ics"],
            calendar_source_url=["calendar.ics", "work.ics"],
            calendar_source_enabled=["legacy-ics"],
            weather_location_query="Pittsburgh, PA",
            weather_country_code="US",
            weather_latitude="40.0",
            weather_longitude="-70.0",
            weather_timezone="America/New_York",
            weather_temperature_unit="fahrenheit",
            weather_thundersnow_f="34",
            weather_thundersnow_c="1",
            weather_snow_temp_f="34",
            weather_snow_temp_c="1",
            weather_recent_snow_hours="2",
            weather_recent_snow_mm="0",
            weather_recent_precip_minutes="60",
            weather_recent_precip_mm="0",
            weather_recent_snow_mm_15="0",
        )

        updated = build_web_settings_update(raw, form)
        self.assertEqual("Inky Planner", updated["dashboard_title"])
        self.assertEqual("calendar.ics", updated["ics_url"])
        self.assertEqual(45, updated["photo_interval_seconds"])
        self.assertTrue(updated["photo_shuffle_enabled"])
        self.assertEqual("PITTSBURGH, PA", updated["weather"]["location_query"].upper())
        self.assertEqual("US", updated["weather"]["country_code"])
        self.assertEqual(2, len(updated["calendar_sources"]))
        self.assertEqual("Family", updated["calendar_sources"][0]["label"])
        self.assertEqual("google", updated["calendar_sources"][0]["type"])

    def test_save_raw_settings_writes_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            original = json.loads(Path("config/settings.json").read_text(encoding="utf-8"))

            save_raw_settings(path, original)

            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("Inky Planner", loaded["dashboard_title"])

    def test_save_raw_settings_restores_previous_file_when_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            original = json.loads(Path("config/settings.json").read_text(encoding="utf-8"))
            save_raw_settings(path, original)

            broken = dict(original)
            broken["weather"] = dict(original["weather"])
            broken["weather"]["timezone"] = "Mars/Olympus"

            with self.assertRaises(ValueError):
                save_raw_settings(path, broken)

            restored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(original["weather"]["timezone"], restored["weather"]["timezone"])


if __name__ == "__main__":
    unittest.main()
