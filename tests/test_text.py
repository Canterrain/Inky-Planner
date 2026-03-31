import unittest

from datetime import datetime

from services.text import format_clock, format_updated_at, translate, weekday_abbrev


class TextTests(unittest.TestCase):
    def test_translate_known_key(self) -> None:
        self.assertEqual("Rain", translate("en", "condition.rain"))

    def test_translate_formats_placeholders(self) -> None:
        self.assertEqual("FREE AFTER 3 PM", translate("en", "schedule.free_after", time="3 PM"))

    def test_translate_weather_fact(self) -> None:
        self.assertEqual("WIND 12 MPH", translate("en", "weather.fact_wind", value=12, unit="MPH"))

    def test_translate_falls_back_to_key_for_unknown_entry(self) -> None:
        self.assertEqual("missing.key", translate("en", "missing.key"))

    def test_translate_german_known_key(self) -> None:
        self.assertEqual("Regen", translate("de", "condition.rain"))

    def test_translate_french_known_key(self) -> None:
        self.assertEqual("Pluie", translate("fr", "condition.rain"))

    def test_weekday_abbrev_localizes(self) -> None:
        sample = datetime(2026, 3, 30)
        self.assertEqual("Mo", weekday_abbrev(sample, "de"))
        self.assertEqual("Lun", weekday_abbrev(sample, "fr"))

    def test_format_clock_localizes(self) -> None:
        sample = datetime(2026, 3, 30, 14, 5)
        self.assertEqual("2:05 PM", format_clock(sample, "en"))
        self.assertEqual("14:05", format_clock(sample, "de"))

    def test_format_updated_at_localizes(self) -> None:
        sample = datetime(2026, 3, 30, 14, 5)
        self.assertIn("Aktualisiert", format_updated_at(sample, "de"))
        self.assertIn("Mis à jour", format_updated_at(sample, "fr"))


if __name__ == "__main__":
    unittest.main()
