import json
import tempfile
import unittest
from pathlib import Path

from config.settings import load_settings


class SettingsValidationTests(unittest.TestCase):
    def _write_settings(self, raw: dict) -> str:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "settings.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return str(path)

    def _base_settings(self) -> dict:
        return {
            "language": "en",
            "dashboard_title": "Inky Planner",
            "ics_url": "assets/sample_family_calendar.ics",
            "calendar_sources": [
                {
                    "id": "legacy-ics",
                    "type": "ics",
                    "label": "Primary Calendar Feed",
                    "url": "assets/sample_family_calendar.ics",
                    "enabled": True,
                }
            ],
            "weather": {
                "location_query": "",
                "country_code": "",
                "latitude": 40.7128,
                "longitude": -74.0060,
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
            "photo_folder": "assets/photos",
            "photo_interval_seconds": 180,
            "photo_shuffle_enabled": False,
            "mode_state_file": "state/mode_state.json",
            "temporary_mode_timeout_minutes": 10,
            "default_preview_mode": "dashboard",
            "preview_output_enabled": True,
            "hardware_display_enabled": False,
            "spectra_mode": "atkinson",
            "palette_debug_enabled": True,
            "refresh_interval_minutes": 30,
        }

    def test_rejects_missing_all_calendar_feeds(self) -> None:
        raw = self._base_settings()
        raw["ics_url"] = "   "
        raw["calendar_sources"] = []
        with self.assertRaisesRegex(ValueError, "calendar feed"):
            load_settings(self._write_settings(raw))

    def test_rejects_invalid_temperature_unit(self) -> None:
        raw = self._base_settings()
        raw["weather"]["temperature_unit"] = "kelvin"
        with self.assertRaisesRegex(ValueError, "temperature_unit"):
            load_settings(self._write_settings(raw))

    def test_rejects_invalid_spectra_mode(self) -> None:
        raw = self._base_settings()
        raw["spectra_mode"] = "broken"
        with self.assertRaisesRegex(ValueError, "spectra_mode"):
            load_settings(self._write_settings(raw))

    def test_rejects_unsupported_language(self) -> None:
        raw = self._base_settings()
        raw["language"] = "es"
        with self.assertRaisesRegex(ValueError, "language"):
            load_settings(self._write_settings(raw))

    def test_accepts_german_language(self) -> None:
        raw = self._base_settings()
        raw["language"] = "de"
        settings = load_settings(self._write_settings(raw))
        self.assertEqual("de", settings.language)

    def test_accepts_french_language(self) -> None:
        raw = self._base_settings()
        raw["language"] = "fr"
        settings = load_settings(self._write_settings(raw))
        self.assertEqual("fr", settings.language)

    def test_rejects_negative_recent_precip_minutes(self) -> None:
        raw = self._base_settings()
        raw["weather"]["recent_precip_minutes"] = -1
        with self.assertRaisesRegex(ValueError, "recent_precip_minutes"):
            load_settings(self._write_settings(raw))

    def test_rejects_non_positive_photo_interval_seconds(self) -> None:
        raw = self._base_settings()
        raw["photo_interval_seconds"] = 0
        with self.assertRaisesRegex(ValueError, "photo_interval_seconds"):
            load_settings(self._write_settings(raw))


if __name__ == "__main__":
    unittest.main()
