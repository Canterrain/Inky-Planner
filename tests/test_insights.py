import unittest

from models.calendar import CalendarDay, CalendarEvent
from models.weather import WeatherDay
from services.insights import build_day_insights


class InsightTests(unittest.TestCase):
    def test_weather_and_next_event_insights_are_prioritized(self) -> None:
        day = CalendarDay(
            label="Fri",
            date_value=__import__("datetime").date(2026, 3, 27),
            multi_day_event=None,
            all_day_events=[],
            timed_events=[
                CalendarEvent(
                    start_time="3:30 PM",
                    raw_title="Sam - Dentist Appointment",
                    display_title="Dentist Appointment",
                )
            ],
            visible_events=[],
            overflow_count=0,
        )
        weather = WeatherDay(
            label="Fri",
            source_weather_code=61,
            effective_weather_code=61,
            condition_key="rain",
            icon_name="rain",
            condition_label="Rain",
            high_temp=52,
            low_temp=41,
        )

        insights = build_day_insights(day, weather, mode_name="today")
        self.assertEqual("Rain likely today.", insights[0])
        self.assertEqual("Next: Dentist Appointment at 3:30 PM", insights[1])


if __name__ == "__main__":
    unittest.main()
