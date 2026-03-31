import unittest
from pathlib import Path

from services.photo_service import pick_photo


class PhotoServiceTests(unittest.TestCase):
    def test_pick_photo_returns_first_alphabetically(self) -> None:
        selected = pick_photo("assets/photos", Path.cwd())
        self.assertIsNotNone(selected)
        self.assertEqual("sample_photo.png", selected.name)


if __name__ == "__main__":
    unittest.main()
