import json
import unittest
from unittest.mock import patch

from services.geocoding_service import GeocodingServiceError, search_locations


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class GeocodingServiceTests(unittest.TestCase):
    def test_search_locations_returns_results(self) -> None:
        payload = {
            "results": [
                {
                    "name": "Pittsburgh",
                    "latitude": 40.4406,
                    "longitude": -79.9959,
                    "timezone": "America/New_York",
                    "country": "United States",
                    "admin1": "Pennsylvania",
                    "country_code": "US",
                    "population": 302971,
                }
            ]
        }
        with patch("services.geocoding_service.urlopen", return_value=_FakeResponse(payload)):
            results = search_locations("Pittsburgh, PA", country_code="US")
        self.assertEqual(1, len(results))
        self.assertEqual("Pittsburgh, Pennsylvania, United States", results[0].display_name)
        self.assertEqual("America/New_York", results[0].timezone)

    def test_search_locations_ranks_state_match_first(self) -> None:
        payload = {
            "results": [
                {
                    "name": "Loveland",
                    "latitude": 39.2689,
                    "longitude": -84.2638,
                    "timezone": "America/New_York",
                    "country": "United States",
                    "admin1": "Ohio",
                    "country_code": "US",
                    "population": 13390,
                },
                {
                    "name": "Loveland",
                    "latitude": 40.3978,
                    "longitude": -105.0749,
                    "timezone": "America/Denver",
                    "country": "United States",
                    "admin1": "Colorado",
                    "country_code": "US",
                    "population": 76995,
                },
            ]
        }
        with patch("services.geocoding_service.urlopen", return_value=_FakeResponse(payload)):
            results = search_locations("Loveland, OH", country_code="")
        self.assertEqual("Ohio", results[0].admin1)

    def test_search_locations_uses_country_hint_from_query(self) -> None:
        payload = {
            "results": [
                {
                    "name": "Aurora",
                    "latitude": 39.7294,
                    "longitude": -104.8319,
                    "timezone": "America/Denver",
                    "country": "United States",
                    "admin1": "Colorado",
                    "country_code": "US",
                },
                {
                    "name": "Aurora",
                    "latitude": 43.9995,
                    "longitude": -79.4663,
                    "timezone": "America/Toronto",
                    "country": "Canada",
                    "admin1": "Ontario",
                    "country_code": "CA",
                },
            ]
        }
        with patch("services.geocoding_service.urlopen", return_value=_FakeResponse(payload)):
            results = search_locations("Aurora, ON, Canada")
        self.assertEqual("Canada", results[0].country)

    def test_search_locations_raises_for_no_matches(self) -> None:
        with patch("services.geocoding_service.urlopen", return_value=_FakeResponse({"results": []})):
            with self.assertRaises(GeocodingServiceError):
                search_locations("nowhere")


if __name__ == "__main__":
    unittest.main()
