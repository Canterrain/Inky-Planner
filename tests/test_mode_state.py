import unittest
from datetime import datetime

from config.settings import load_settings
from models.mode import AppMode
from services.mode_state import build_mode_state


class ModeStateTests(unittest.TestCase):
    def test_temporary_mode_auto_returns_to_dashboard(self) -> None:
        settings = load_settings("config/settings.json")
        entered_at = datetime(2026, 3, 27, 9, 0)
        state = build_mode_state(settings, AppMode.TODAY, entered_at)

        resolved = state.resolve_active_mode(datetime(2026, 3, 27, 9, 11))
        self.assertEqual(AppMode.DASHBOARD, resolved)

    def test_persistent_photo_mode_does_not_auto_return(self) -> None:
        settings = load_settings("config/settings.json")
        entered_at = datetime(2026, 3, 27, 9, 0)
        state = build_mode_state(settings, AppMode.PHOTO, entered_at)

        resolved = state.resolve_active_mode(datetime(2026, 3, 27, 12, 0))
        self.assertEqual(AppMode.PHOTO, resolved)


if __name__ == "__main__":
    unittest.main()
