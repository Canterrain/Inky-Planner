import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.settings import load_settings
from models.mode import AppMode
from services.runtime import refresh_app, should_refresh_dashboard_on_idle


class RuntimePerformanceTests(unittest.TestCase):
    def test_dashboard_idle_refresh_respects_interval(self) -> None:
        settings = load_settings("config/settings.json")

        self.assertFalse(
            should_refresh_dashboard_on_idle(
                settings,
                AppMode.DASHBOARD,
                last_refresh_monotonic=0.0,
                now_monotonic=(settings.refresh_interval_minutes * 60) - 1,
            )
        )
        self.assertTrue(
            should_refresh_dashboard_on_idle(
                settings,
                AppMode.DASHBOARD,
                last_refresh_monotonic=0.0,
                now_monotonic=settings.refresh_interval_minutes * 60,
            )
        )

    def test_dashboard_idle_refresh_skips_non_dashboard_modes(self) -> None:
        settings = load_settings("config/settings.json")

        self.assertFalse(
            should_refresh_dashboard_on_idle(
                settings,
                AppMode.TODAY,
                last_refresh_monotonic=0.0,
                now_monotonic=settings.refresh_interval_minutes * 60,
            )
        )

    def test_photo_mode_refresh_skips_dashboard_data_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = load_settings("config/settings.json")
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(settings.settings_path.read_text(encoding="utf-8"), encoding="utf-8")

            with patch("services.runtime.get_dashboard_data_cached", side_effect=AssertionError("should not build dashboard data")), patch(
                "renderer.mode_dispatch.current_photo", return_value=None
            ):
                refresh_app(
                    settings_path,
                    mode_override=AppMode.PHOTO,
                    preview_only=True,
                    output_dir=temp_dir,
                )


if __name__ == "__main__":
    unittest.main()
