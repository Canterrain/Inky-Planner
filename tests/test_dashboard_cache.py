import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.dashboard_cache import clear_dashboard_data_cache, get_dashboard_data_cached


class DashboardCacheTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_dashboard_data_cache()

    def test_reuses_cached_data_within_ttl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text("{}", encoding="utf-8")

            first = object()
            second = object()
            with patch("services.dashboard_cache.build_dashboard_data", side_effect=[first, second]) as build_mock:
                self.assertIs(first, get_dashboard_data_cached(settings_path, max_age_seconds=180))
                self.assertIs(first, get_dashboard_data_cached(settings_path, max_age_seconds=180))

            build_mock.assert_called_once()

    def test_rebuilds_when_settings_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text("{}", encoding="utf-8")

            first = object()
            second = object()
            with patch("services.dashboard_cache.build_dashboard_data", side_effect=[first, second]) as build_mock:
                self.assertIs(first, get_dashboard_data_cached(settings_path, max_age_seconds=180))
                settings_path.write_text('{"language":"de"}', encoding="utf-8")
                self.assertIs(second, get_dashboard_data_cached(settings_path, max_age_seconds=180))

            self.assertEqual(2, build_mock.call_count)


if __name__ == "__main__":
    unittest.main()
