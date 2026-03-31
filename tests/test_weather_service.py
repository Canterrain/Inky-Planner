import unittest

from renderer.icons import load_weather_icon_asset
from services.weather_service import map_weather_code
from services.weather_icons import SUPPORTED_ICON_NAMES, map_weather_code_to_icon
from services.weather_semantics import interpret_openmeteo_daily_condition


class WeatherServiceTests(unittest.TestCase):
    def test_maps_clear_code_to_supported_icon(self) -> None:
        self.assertEqual("clear-day", map_weather_code(0))

    def test_maps_partly_cloudy_codes(self) -> None:
        self.assertEqual("partlycloudy-day", map_weather_code(2))

    def test_unknown_code_falls_back_to_cloudy(self) -> None:
        self.assertEqual("cloudy", map_weather_code(999))

    def test_supports_night_variants(self) -> None:
        self.assertEqual("clear-night", map_weather_code_to_icon(0, is_day=False).icon_name)
        self.assertEqual("showers-night", map_weather_code_to_icon(51, is_day=False).icon_name)

    def test_supported_icon_names_are_documented(self) -> None:
        self.assertIn("clear-day", SUPPORTED_ICON_NAMES)
        self.assertIn("partlycloudy-night", SUPPORTED_ICON_NAMES)
        self.assertIn("thunderstorm", SUPPORTED_ICON_NAMES)

    def test_supported_asset_backed_icons_load(self) -> None:
        for icon_name in [
            "clear-day",
            "clear-night",
            "partlycloudy-day",
            "partlycloudy-night",
            "cloudy",
            "fog",
            "rain",
            "showers-day",
            "showers-night",
            "thunderstorm",
            "snow",
            "sleet",
        ]:
            with self.subTest(icon_name=icon_name):
                self.assertIsNotNone(load_weather_icon_asset(icon_name, 48))

    def test_semantics_can_map_thundersnow(self) -> None:
        condition = interpret_openmeteo_daily_condition(
            95,
            high_temp=32,
            low_temp=28,
            temperature_unit="fahrenheit",
            thundersnow_f=34,
        )
        self.assertEqual("thundersnow", condition.icon_name)

    def test_condition_exposes_language_neutral_key(self) -> None:
        condition = interpret_openmeteo_daily_condition(
            61,
            high_temp=55,
            low_temp=42,
            temperature_unit="fahrenheit",
        )
        self.assertEqual("rain", condition.key)


if __name__ == "__main__":
    unittest.main()
