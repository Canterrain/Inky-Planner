import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from config.settings import load_settings
from models.mode import AppMode
from services.mode_state import build_mode_state
from services.mode_state_store import load_persisted_mode_state, save_mode_state


class ModeStateStoreTests(unittest.TestCase):
    def test_save_and_load_mode_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = load_settings("config/settings.json")
            temp_path = Path(temp_dir) / "mode_state.json"
            settings = settings.__class__(**{**settings.__dict__, "mode_state_file": str(temp_path)})

            entered_at = datetime(2026, 3, 27, 10, 0)
            state = build_mode_state(settings, AppMode.TODAY, entered_at)
            save_mode_state(settings, state)

            loaded = load_persisted_mode_state(settings, entered_at)
            self.assertEqual(AppMode.TODAY, loaded.current_mode)
            self.assertTrue(loaded.should_auto_return)

    def test_invalid_state_falls_back_to_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = load_settings("config/settings.json")
            temp_path = Path(temp_dir) / "mode_state.json"
            temp_path.write_text("{bad json", encoding="utf-8")
            settings = settings.__class__(**{**settings.__dict__, "mode_state_file": str(temp_path)})

            loaded = load_persisted_mode_state(settings, datetime(2026, 3, 27, 10, 0))
            self.assertEqual(AppMode.DASHBOARD, loaded.current_mode)


if __name__ == "__main__":
    unittest.main()
