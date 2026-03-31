import unittest

from hardware.buttons import BUTTON_PIN_MAP
from models.mode import AppMode


class ButtonMappingTests(unittest.TestCase):
    def test_button_pin_map_matches_requested_modes(self) -> None:
        self.assertEqual(("A", AppMode.DASHBOARD), BUTTON_PIN_MAP[5])
        self.assertEqual(("B", AppMode.TODAY), BUTTON_PIN_MAP[6])
        self.assertEqual(("C", AppMode.TOMORROW), BUTTON_PIN_MAP[16])
        self.assertEqual(("D", AppMode.PHOTO), BUTTON_PIN_MAP[24])


if __name__ == "__main__":
    unittest.main()
