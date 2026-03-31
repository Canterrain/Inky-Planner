from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import urlopen


OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
US_STATE_ABBREVIATIONS = {
    "AL": "ALABAMA",
    "AK": "ALASKA",
    "AZ": "ARIZONA",
    "AR": "ARKANSAS",
    "CA": "CALIFORNIA",
    "CO": "COLORADO",
    "CT": "CONNECTICUT",
    "DE": "DELAWARE",
    "FL": "FLORIDA",
    "GA": "GEORGIA",
    "HI": "HAWAII",
    "ID": "IDAHO",
    "IL": "ILLINOIS",
    "IN": "INDIANA",
    "IA": "IOWA",
    "KS": "KANSAS",
    "KY": "KENTUCKY",
    "LA": "LOUISIANA",
    "ME": "MAINE",
    "MD": "MARYLAND",
    "MA": "MASSACHUSETTS",
    "MI": "MICHIGAN",
    "MN": "MINNESOTA",
    "MS": "MISSISSIPPI",
    "MO": "MISSOURI",
    "MT": "MONTANA",
    "NE": "NEBRASKA",
    "NV": "NEVADA",
    "NH": "NEW HAMPSHIRE",
    "NJ": "NEW JERSEY",
    "NM": "NEW MEXICO",
    "NY": "NEW YORK",
    "NC": "NORTH CAROLINA",
    "ND": "NORTH DAKOTA",
    "OH": "OHIO",
    "OK": "OKLAHOMA",
    "OR": "OREGON",
    "PA": "PENNSYLVANIA",
    "RI": "RHODE ISLAND",
    "SC": "SOUTH CAROLINA",
    "SD": "SOUTH DAKOTA",
    "TN": "TENNESSEE",
    "TX": "TEXAS",
    "UT": "UTAH",
    "VT": "VERMONT",
    "VA": "VIRGINIA",
    "WA": "WASHINGTON",
    "WV": "WEST VIRGINIA",
    "WI": "WISCONSIN",
    "WY": "WYOMING",
    "DC": "DISTRICT OF COLUMBIA",
}
US_STATE_NAMES = {name: abbr for abbr, name in US_STATE_ABBREVIATIONS.items()}
COUNTRY_ALIASES = {
    "US": "US",
    "USA": "US",
    "UNITED STATES": "US",
    "UNITED STATES OF AMERICA": "US",
    "CANADA": "CA",
    "CA": "CA",
}


class GeocodingServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeocodingResult:
    name: str
    latitude: float
    longitude: float
    timezone: str | None
    country: str | None
    admin1: str | None
    country_code: str | None
    population: int | None = None

    @property
    def display_name(self) -> str:
        parts = [self.name]
        if self.admin1:
            parts.append(self.admin1)
        if self.country:
            parts.append(self.country)
        return ", ".join(part for part in parts if part)


def search_locations(query: str, *, language: str = "en", country_code: str | None = None, count: int = 5) -> list[GeocodingResult]:
    clean_query = query.strip()
    if not clean_query:
        raise GeocodingServiceError("Location query must not be empty")

    parsed = _parse_location_query(clean_query, country_code=country_code)

    params = {
        "name": parsed["name"],
        "count": 10,
        "language": language or "en",
        "format": "json",
    }
    clean_country_code = parsed["country_code"]
    if clean_country_code:
        params["countryCode"] = clean_country_code

    url = f"{OPEN_METEO_GEOCODING_URL}?{urlencode(params)}"

    try:
        with urlopen(url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise GeocodingServiceError(f"Unable to geocode location: {exc}") from exc

    results = payload.get("results") or []
    if not results:
        raise GeocodingServiceError(f"No matches found for '{clean_query}'")

    resolved: list[GeocodingResult] = []
    for item in results:
        try:
            resolved.append(
                GeocodingResult(
                    name=str(item["name"]),
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                    timezone=str(item["timezone"]) if item.get("timezone") else None,
                    country=str(item["country"]) if item.get("country") else None,
                    admin1=str(item["admin1"]) if item.get("admin1") else None,
                    country_code=str(item["country_code"]) if item.get("country_code") else None,
                    population=int(item["population"]) if item.get("population") is not None else None,
                )
            )
        except Exception:
            continue

    if not resolved:
        raise GeocodingServiceError(f"No valid matches found for '{clean_query}'")

    ranked = sorted(resolved, key=lambda result: _ranking_key(result, parsed))
    return ranked[: max(1, min(count, 10))]


def _parse_location_query(query: str, *, country_code: str | None) -> dict[str, str | None]:
    tokens = [token.strip() for token in query.split(",") if token.strip()]
    if not tokens:
        raise GeocodingServiceError("Location query must not be empty")

    name = tokens[0]
    state_hint = None
    country_hint = _normalize_country_code(country_code)

    if len(tokens) >= 2:
        second = tokens[1]
        normalized_state = _normalize_state_hint(second)
        normalized_country = _normalize_country_code(second)
        if normalized_state:
            state_hint = normalized_state
            if not country_hint:
                country_hint = "US"
        elif normalized_country and not country_hint:
            country_hint = normalized_country

    if len(tokens) >= 3 and not country_hint:
        country_hint = _normalize_country_code(tokens[2])

    return {
        "name": name,
        "state_hint": state_hint,
        "country_code": country_hint,
    }


def _normalize_state_hint(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().upper()
    if normalized in US_STATE_ABBREVIATIONS:
        return US_STATE_ABBREVIATIONS[normalized]
    return normalized if normalized in US_STATE_NAMES else None


def _normalize_country_code(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().upper()
    return COUNTRY_ALIASES.get(normalized, normalized if len(normalized) == 2 else None)


def _ranking_key(result: GeocodingResult, parsed: dict[str, str | None]) -> tuple[int, int, int, str]:
    score = 0

    desired_country = parsed.get("country_code")
    if desired_country:
        if (result.country_code or "").upper() == desired_country:
            score += 100
        else:
            score -= 100

    desired_state = parsed.get("state_hint")
    if desired_state:
        result_state = (result.admin1 or "").strip().upper()
        if result_state == desired_state:
            score += 80
        else:
            score -= 40

    desired_name = (parsed.get("name") or "").strip().upper()
    result_name = (result.name or "").strip().upper()
    if result_name == desired_name:
        score += 20
    elif result_name.startswith(desired_name):
        score += 10

    population = result.population or 0
    display_name = result.display_name.lower()
    return (-score, -population, len(display_name), display_name)
