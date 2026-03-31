import unittest

from services.weather_semantics import (
    apply_active_precip_override_minutely,
    apply_recent_snow_override_hourly,
    interpret_openmeteo_daily_condition,
)


class WeatherSemanticsTests(unittest.TestCase):
    def test_maps_openmeteo_drizzle_to_showers(self) -> None:
        condition = interpret_openmeteo_daily_condition(
            51,
            high_temp=55,
            low_temp=42,
            temperature_unit="fahrenheit",
        )
        self.assertEqual("showers-day", condition.icon_name)
        self.assertEqual("Showers", condition.label)

    def test_maps_freezing_rain_to_sleet(self) -> None:
        condition = interpret_openmeteo_daily_condition(
            66,
            high_temp=34,
            low_temp=28,
            temperature_unit="fahrenheit",
        )
        self.assertEqual("sleet", condition.icon_name)

    def test_daily_thunderstorm_becomes_thundersnow_when_cold(self) -> None:
        condition = interpret_openmeteo_daily_condition(
            95,
            high_temp=33,
            low_temp=29,
            temperature_unit="fahrenheit",
            thundersnow_f=34,
        )
        self.assertEqual("thundersnow", condition.icon_name)
        self.assertEqual("Thundersnow", condition.label)

    def test_daily_thunderstorm_stays_thunderstorm_when_warm(self) -> None:
        condition = interpret_openmeteo_daily_condition(
            95,
            high_temp=45,
            low_temp=38,
            temperature_unit="fahrenheit",
            thundersnow_f=34,
        )
        self.assertEqual("thunderstorm", condition.icon_name)

    def test_active_precip_override_promotes_rain_when_precipitating_now(self) -> None:
        result = apply_active_precip_override_minutely(
            3,
            temp_now=45,
            temperature_unit="fahrenheit",
            minutely_times=[
                "2026-03-29T12:00",
                "2026-03-29T12:15",
                "2026-03-29T12:30",
            ],
            minutely_precipitation=[0, 0.4, 0],
            minutely_snowfall=[0, 0, 0],
            now_iso="2026-03-29T12:15",
        )
        self.assertTrue(result.used)
        self.assertEqual(61, result.code)

    def test_active_precip_override_promotes_snow_when_cold(self) -> None:
        result = apply_active_precip_override_minutely(
            3,
            temp_now=31,
            temperature_unit="fahrenheit",
            minutely_times=[
                "2026-03-29T12:00",
                "2026-03-29T12:15",
            ],
            minutely_precipitation=[0, 0.2],
            minutely_snowfall=[0, 0],
            now_iso="2026-03-29T12:15",
        )
        self.assertTrue(result.used)
        self.assertEqual(73, result.code)

    def test_recent_snow_override_promotes_snow(self) -> None:
        result = apply_recent_snow_override_hourly(
            3,
            hourly_times=[
                "2026-03-29T10:00",
                "2026-03-29T11:00",
                "2026-03-29T12:00",
            ],
            hourly_snowfall=[0, 0.1, 0],
            hourly_codes=[3, 3, 3],
            now_iso="2026-03-29T12:00",
            recent_snow_hours=2,
            recent_snow_mm=0,
        )
        self.assertTrue(result.used)
        self.assertEqual(73, result.code)


if __name__ == "__main__":
    unittest.main()
