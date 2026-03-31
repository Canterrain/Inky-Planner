import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from web.app import create_app


class WebAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = self.app.test_client()

    def test_settings_page_loads(self) -> None:
        response = self.client.get("/settings")
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Inky Planner Config", response.data)

    def test_test_weather_action_handles_success(self) -> None:
        with patch("web.app.fetch_weather_days", return_value=[object(), object()]):
            response = self.client.post("/actions/test-weather", follow_redirects=True)
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Weather OK", response.data)

    def test_test_calendar_action_redirects_back_to_settings(self) -> None:
        with patch("web.app.fetch_calendar_days", return_value=[object(), object()]), patch(
            "web.app.inspect_calendar_sources",
            return_value=[
                type(
                    "CalendarResult",
                    (),
                    {
                        "source_id": "family",
                        "label": "Family",
                        "source_type": "ics",
                        "source_url": "https://example.com/family.ics",
                        "success": True,
                        "event_count": 2,
                        "preview_lines": ["Mon: 8:00 AM Team Check-In"],
                        "error": None,
                    },
                )()
            ],
        ):
            response = self.client.post("/actions/test-calendar", follow_redirects=True)
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Calendar OK", response.data)
        self.assertIn(b"Calendar Test Results", response.data)
        self.assertIn(b"Family", response.data)

    def test_refresh_action_requests_hardware_refresh_when_enabled(self) -> None:
        settings = type(
            "Settings",
            (),
            {
                "project_root": None,
            },
        )()
        with patch("web.app.load_settings", return_value=settings), patch("web.app.request_refresh") as request_refresh_mock:
            response = self.client.post("/actions/refresh", follow_redirects=True)
        self.assertEqual(200, response.status_code)
        request_refresh_mock.assert_called_once()
        self.assertIn(b"Hardware refresh requested", response.data)

    def test_geocode_action_shows_choices(self) -> None:
        result = type(
            "Result",
            (),
            {
                "display_name": "Pittsburgh, Pennsylvania, United States",
                "name": "Pittsburgh",
                "latitude": 40.4406,
                "longitude": -79.9959,
                "timezone": "America/New_York",
                "country": "United States",
                "admin1": "Pennsylvania",
                "country_code": "US",
            },
        )()
        with patch("web.app.search_locations", return_value=[result]):
            response = self.client.post(
                "/actions/geocode",
                data={
                    "dashboard_title": "Inky Planner",
                    "language": "en",
                    "ics_url": "assets/sample_family_calendar.ics",
                    "photo_folder": "assets/photos",
                    "weather_location_query": "Pittsburgh, PA",
                    "weather_country_code": "US",
                    "weather_latitude": "40.0",
                    "weather_longitude": "-79.0",
                    "weather_timezone": "America/New_York",
                    "weather_temperature_unit": "fahrenheit",
                    "weather_thundersnow_f": "34",
                    "weather_thundersnow_c": "1",
                    "weather_snow_temp_f": "34",
                    "weather_snow_temp_c": "1",
                    "weather_recent_snow_hours": "2",
                    "weather_recent_snow_mm": "0",
                    "weather_recent_precip_minutes": "60",
                    "weather_recent_precip_mm": "0",
                    "weather_recent_snow_mm_15": "0",
                    "rule_label": "",
                    "rule_match_text": "",
                    "rule_color": "",
                },
                follow_redirects=True,
            )
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Location Matches", response.data)
        self.assertIn(b"Use This Location", response.data)

    def test_apply_geocode_action_handles_success(self) -> None:
        response = self.client.post(
            "/actions/apply-geocode",
            data={
                "pending_settings_json": "{\"dashboard_title\": \"Inky Planner\", \"language\": \"en\", \"ics_url\": \"assets/sample_family_calendar.ics\", \"photo_folder\": \"assets/photos\", \"weather\": {\"location_query\": \"Pittsburgh, PA\", \"country_code\": \"US\", \"latitude\": 40.0, \"longitude\": -79.0, \"timezone\": \"America/New_York\", \"temperature_unit\": \"fahrenheit\", \"thundersnow_f\": 34, \"thundersnow_c\": 1, \"snow_temp_f\": 34, \"snow_temp_c\": 1, \"recent_snow_hours\": 2, \"recent_snow_mm\": 0, \"recent_precip_minutes\": 60, \"recent_precip_mm\": 0, \"recent_snow_mm_15\": 0}, \"refresh_interval_minutes\": 30, \"temporary_mode_timeout_minutes\": 10, \"default_preview_mode\": \"dashboard\", \"mode_state_file\": \"state/mode_state.json\", \"preview_output_enabled\": true, \"hardware_display_enabled\": false, \"spectra_mode\": \"off\", \"palette_debug_enabled\": true}",
                "result_name": "Pittsburgh",
                "result_latitude": "40.4406",
                "result_longitude": "-79.9959",
                "result_timezone": "America/New_York",
                "result_country": "United States",
                "result_admin1": "Pennsylvania",
                "result_country_code": "US",
            },
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Location selected", response.data)
        self.assertIn(b"Click Save Changes to refresh the display", response.data)

    def test_photo_upload_stages_changes_without_refresh(self) -> None:
        settings = type("Settings", (), {"photo_folder": "assets/photos", "project_root": None})()
        with patch("web.app.load_settings", return_value=settings), patch("web.app.save_uploaded_photos", return_value=[object()]):
            response = self.client.post(
                "/photos/upload",
                data={"photos": (BytesIO(b"fake"), "test.jpg")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Uploaded 1 photo", response.data)
        self.assertIn(b"Click Save Changes to refresh the display", response.data)

    def test_export_config_returns_json_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            backup = Path(temp_dir) / "settings-manual-export.json"
            backup.write_text('{"dashboard_title": "Inky Planner"}', encoding="utf-8")
            with patch("web.app.create_settings_backup", return_value=backup):
                response = self.client.get("/config/export")
                response.get_data()
                response.close()
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/json", response.mimetype)
        self.assertIn("attachment;", response.headers.get("Content-Disposition", ""))

    def test_import_config_redirects_with_success_message(self) -> None:
        with patch("web.app.import_settings_backup", return_value=Path("config/backups/settings-pre-import.json")):
            response = self.client.post(
                "/config/import",
                data={"settings_file": (BytesIO(b'{"dashboard_title":"Inky Planner"}'), "settings.json")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Settings imported successfully", response.data)

    def test_language_preview_redirects_back_to_settings_with_translated_ui(self) -> None:
        response = self.client.post(
            "/actions/preview-language",
            data={
                "dashboard_title": "Inky Planner",
                "language": "de",
                "photo_folder": "assets/photos",
                "photo_interval_seconds": "180",
                "weather_location_query": "Pittsburgh, PA",
                "weather_country_code": "US",
                "weather_latitude": "40.4406",
                "weather_longitude": "-79.9959",
                "weather_timezone": "America/New_York",
                "weather_temperature_unit": "fahrenheit",
                "weather_thundersnow_f": "34",
                "weather_thundersnow_c": "1",
                "weather_snow_temp_f": "34",
                "weather_snow_temp_c": "1",
                "weather_recent_snow_hours": "2",
                "weather_recent_snow_mm": "0",
                "weather_recent_precip_minutes": "60",
                "weather_recent_precip_mm": "0",
                "weather_recent_snow_mm_15": "0",
                "calendar_source_id": ["legacy-ics"],
                "calendar_source_label": ["Primary Calendar Feed"],
                "calendar_source_type": ["ics"],
                "calendar_source_url": ["assets/sample_family_calendar.ics"],
                "calendar_source_enabled": ["legacy-ics"],
            },
            follow_redirects=True,
        )
        self.assertEqual(200, response.status_code)
        self.assertIn(b"Allgemein", response.data)
        self.assertIn(b"Deutsch", response.data)


if __name__ == "__main__":
    unittest.main()
