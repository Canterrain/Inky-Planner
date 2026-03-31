import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.photo_slideshow import advance_photo_if_due, current_photo, reset_slideshow_timer


class PhotoSlideshowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project_root = Path(self.temp_dir.name)
        self.photo_dir = self.project_root / "assets" / "photos"
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        (self.photo_dir / "a.jpg").write_bytes(b"a")
        (self.photo_dir / "b.jpg").write_bytes(b"b")

    def _settings(self, *, shuffle: bool = False, interval_seconds: int = 30):
        weather = type("Weather", (), {"timezone": "America/New_York"})()
        return type(
            "Settings",
            (),
            {
                "photo_folder": "assets/photos",
                "project_root": self.project_root,
                "photo_shuffle_enabled": shuffle,
                "photo_interval_seconds": interval_seconds,
                "weather": weather,
            },
        )()

    def test_current_photo_returns_first_photo_in_order_mode(self) -> None:
        settings = self._settings(shuffle=False)
        selected = current_photo(settings)
        self.assertIsNotNone(selected)
        self.assertEqual("a.jpg", selected.name)

    def test_advance_photo_if_due_moves_to_next_photo(self) -> None:
        settings = self._settings(shuffle=False, interval_seconds=1)
        first = current_photo(settings)
        self.assertEqual("a.jpg", first.name)
        reset_slideshow_timer(settings)

        state_path = self.project_root / "state" / "photo_slideshow.json"
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        payload["last_changed_at"] = "2000-01-01T00:00:00-05:00"
        state_path.write_text(json.dumps(payload), encoding="utf-8")

        self.assertTrue(advance_photo_if_due(settings))
        second = current_photo(settings)
        self.assertEqual("b.jpg", second.name)

    def test_shuffle_mode_still_selects_a_real_photo(self) -> None:
        settings = self._settings(shuffle=True)
        selected = current_photo(settings)
        self.assertIn(selected.name, {"a.jpg", "b.jpg"})

    def test_shuffle_wrap_avoids_repeating_last_photo_first(self) -> None:
        settings = self._settings(shuffle=True, interval_seconds=1)
        state_path = self.project_root / "state" / "photo_slideshow.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "order": ["a.jpg", "b.jpg"],
                    "position": 1,
                    "last_changed_at": "2000-01-01T00:00:00-05:00",
                }
            ),
            encoding="utf-8",
        )
        with patch("services.photo_slideshow.random.shuffle", side_effect=lambda items: None):
            self.assertTrue(advance_photo_if_due(settings))
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual("a.jpg", payload["order"][0])
        self.assertEqual(0, payload["position"])


if __name__ == "__main__":
    unittest.main()
