from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from icalendar import Calendar
from recurring_ical_events import of

from config.settings import AppSettings, CalendarSourceSettings
from models.calendar import CalendarDay, CalendarEvent
from services.mock_data import build_mock_calendar_days
from services.text import format_clock, weekday_abbrev


VISIBLE_EVENTS_PER_DAY = 3
REMOTE_CALENDAR_TIMEOUT_SECONDS = 5


class CalendarServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class CalendarSourceTestResult:
    source_id: str
    label: str
    source_type: str
    source_url: str
    success: bool
    event_count: int
    preview_lines: list[str]
    error: str | None = None


def fetch_calendar_days(settings: AppSettings, start_date: date, day_count: int = 5) -> list[CalendarDay]:
    try:
        timezone = ZoneInfo(settings.weather.timezone)
        timed_events_by_day, all_day_events_by_day, multi_day_events_by_day = _initialize_event_buckets(start_date, day_count)

        calendar = _load_calendar(settings)
        if calendar is not None:
            _populate_ics_buckets(
                timed_events_by_day,
                all_day_events_by_day,
                multi_day_events_by_day,
                calendar,
                settings,
                start_date,
                day_count,
                timezone,
            )

        return _build_calendar_days_from_buckets(
            settings,
            start_date,
            day_count,
            timed_events_by_day,
            all_day_events_by_day,
            multi_day_events_by_day,
        )
    except Exception as exc:
        raise CalendarServiceError(f"Unable to fetch calendar data: {exc}") from exc


def fallback_calendar_days(settings: AppSettings, start_date: date) -> list[CalendarDay]:
    return build_mock_calendar_days(start_date, settings.language)


def inspect_calendar_sources(
    settings: AppSettings,
    start_date: date,
    day_count: int = 5,
    preview_limit: int = 4,
    source_id: str | None = None,
) -> list[CalendarSourceTestResult]:
    results: list[CalendarSourceTestResult] = []
    enabled_sources = [source for source in settings.calendar_sources if source.enabled and source.url.strip()]
    if not enabled_sources and settings.ics_url.strip():
        enabled_sources = [
            CalendarSourceSettings(
                id="legacy-ics",
                source_type="ics",
                label="Primary Calendar Feed",
                url=settings.ics_url,
                enabled=True,
            )
        ]
    if source_id:
        enabled_sources = [source for source in enabled_sources if source.id == source_id]

    for source in enabled_sources:
        isolated_settings = replace(settings, calendar_sources=[source], ics_url=source.url)
        try:
            days = fetch_calendar_days(isolated_settings, start_date, day_count)
            preview_lines = _preview_lines(days, preview_limit)
            event_count = sum(
                len(day.timed_events) + len(day.all_day_events) + (1 if day.multi_day_event is not None else 0)
                for day in days
            )
            results.append(
                CalendarSourceTestResult(
                    source_id=source.id,
                    label=source.label,
                    source_type=source.source_type,
                    source_url=source.url,
                    success=True,
                    event_count=event_count,
                    preview_lines=preview_lines,
                )
            )
        except Exception as exc:
            results.append(
                CalendarSourceTestResult(
                    source_id=source.id,
                    label=source.label,
                    source_type=source.source_type,
                    source_url=source.url,
                    success=False,
                    event_count=0,
                    preview_lines=[],
                    error=str(exc),
                )
            )
    return results


def _load_calendar(settings: AppSettings) -> Calendar | None:
    source_urls = [source.url for source in settings.calendar_sources if source.enabled and source.url.strip()]
    if not source_urls and settings.ics_url.strip():
        source_urls = [settings.ics_url]
    if not source_urls:
        return None

    merged = Calendar()
    merged.add("PRODID", "-//Inky Planner//Merged Calendar//EN")
    merged.add("VERSION", "2.0")
    merged.add("CALSCALE", "GREGORIAN")

    for source_url in source_urls:
        calendar = Calendar.from_ical(_load_ics_bytes(source_url, settings))
        for component in calendar.subcomponents:
            merged.add_component(component)

    return merged


def _load_ics_bytes(ics_target: str, settings: AppSettings) -> bytes:
    ics_target = ics_target.strip()
    parsed = urlparse(ics_target)

    if parsed.scheme in ("http", "https"):
        with urlopen(ics_target, timeout=REMOTE_CALENDAR_TIMEOUT_SECONDS) as response:
            return response.read()

    if parsed.scheme == "webcal":
        http_target = ics_target.replace("webcal://", "https://", 1)
        with urlopen(http_target, timeout=REMOTE_CALENDAR_TIMEOUT_SECONDS) as response:
            return response.read()

    if parsed.scheme == "file":
        return Path(parsed.path).read_bytes()

    path = Path(ics_target)
    candidates = [path, settings.project_root / ics_target, settings.settings_path.parent / ics_target]
    for candidate in candidates:
        if candidate.exists():
            return candidate.read_bytes()

    raise FileNotFoundError(f"ICS source not found: {ics_target}")


def _populate_ics_buckets(
    timed_events_by_day: dict[date, list[tuple[tuple[int, time, str], CalendarEvent]]],
    all_day_events_by_day: dict[date, list[CalendarEvent]],
    multi_day_events_by_day: dict[date, list[CalendarEvent]],
    calendar: Calendar,
    settings: AppSettings,
    start_date: date,
    day_count: int,
    timezone: ZoneInfo,
) -> None:
    calendar = _sanitize_calendar(calendar)
    range_start = datetime.combine(start_date, time.min, tzinfo=timezone)
    range_end = range_start + timedelta(days=day_count)
    occurrences = of(calendar, skip_bad_series=True).between(range_start, range_end)

    for component in occurrences:
        classified = _component_to_events(component, settings, timezone, start_date, day_count)
        for event_day, bucket_name, sort_key, event in classified:
            if bucket_name == "multi_day" and event_day in multi_day_events_by_day:
                multi_day_events_by_day[event_day].append(event)
            elif bucket_name == "all_day" and event_day in all_day_events_by_day:
                all_day_events_by_day[event_day].append(event)
            elif bucket_name == "timed" and event_day in timed_events_by_day:
                timed_events_by_day[event_day].append((sort_key, event))

def _initialize_event_buckets(
    start_date: date,
    day_count: int,
) -> tuple[
    dict[date, list[tuple[tuple[int, time, str], CalendarEvent]]],
    dict[date, list[CalendarEvent]],
    dict[date, list[CalendarEvent]],
]:
    timed_events_by_day = {start_date + timedelta(days=offset): [] for offset in range(day_count)}
    all_day_events_by_day = {start_date + timedelta(days=offset): [] for offset in range(day_count)}
    multi_day_events_by_day = {start_date + timedelta(days=offset): [] for offset in range(day_count)}
    return timed_events_by_day, all_day_events_by_day, multi_day_events_by_day


def _build_calendar_days_from_buckets(
    settings: AppSettings,
    start_date: date,
    day_count: int,
    timed_events_by_day: dict[date, list[tuple[tuple[int, time, str], CalendarEvent]]],
    all_day_events_by_day: dict[date, list[CalendarEvent]],
    multi_day_events_by_day: dict[date, list[CalendarEvent]],
) -> list[CalendarDay]:
    calendar_days: list[CalendarDay] = []
    for offset in range(day_count):
        current_day = start_date + timedelta(days=offset)
        day_events = [event for _, event in sorted(timed_events_by_day[current_day], key=lambda item: item[0])]
        multi_day_event = sorted(
            multi_day_events_by_day[current_day],
            key=lambda event: event.display_title.lower(),
        )
        all_day_events = sorted(
            all_day_events_by_day[current_day],
            key=lambda event: event.display_title.lower(),
        )
        calendar_days.append(
            CalendarDay(
                label=weekday_abbrev(current_day, settings.language),
                date_value=current_day,
                multi_day_event=multi_day_event[0] if multi_day_event else None,
                all_day_events=all_day_events,
                timed_events=day_events,
                visible_events=day_events[:VISIBLE_EVENTS_PER_DAY],
                overflow_count=max(0, len(day_events) - VISIBLE_EVENTS_PER_DAY),
            )
        )

    return calendar_days


def _build_calendar_days(
    calendar: Calendar,
    settings: AppSettings,
    start_date: date,
    day_count: int,
    timezone: ZoneInfo,
) -> list[CalendarDay]:
    timed_events_by_day, all_day_events_by_day, multi_day_events_by_day = _initialize_event_buckets(start_date, day_count)
    _populate_ics_buckets(
        timed_events_by_day,
        all_day_events_by_day,
        multi_day_events_by_day,
        calendar,
        settings,
        start_date,
        day_count,
        timezone,
    )
    return _build_calendar_days_from_buckets(
        settings,
        start_date,
        day_count,
        timed_events_by_day,
        all_day_events_by_day,
        multi_day_events_by_day,
    )


def _preview_lines(days: list[CalendarDay], limit: int) -> list[str]:
    lines: list[str] = []
    for day in days:
        if day.multi_day_event is not None:
            lines.append(f"{day.label}: {day.multi_day_event.display_title} (all day)")
        for event in day.all_day_events:
            lines.append(f"{day.label}: {event.display_title} (all day)")
        for event in day.visible_events:
            lines.append(f"{day.label}: {event.start_time} {event.display_title}")
        if len(lines) >= limit:
            break
    return lines[:limit]


def _sanitize_calendar(calendar: Calendar) -> Calendar:
    sanitized = Calendar()
    for key, value in calendar.items():
        sanitized.add(key, value)

    for component in calendar.subcomponents:
        if component.name != "VEVENT":
            sanitized.add_component(component)
            continue
        if component.get("DTSTART") is None:
            continue
        start_value = component.decoded("DTSTART")
        end_value = component.decoded("DTEND") if component.get("DTEND") is not None else None
        if isinstance(start_value, datetime) and isinstance(end_value, datetime) and end_value <= start_value:
            continue
        if isinstance(start_value, date) and not isinstance(start_value, datetime):
            if isinstance(end_value, datetime):
                if end_value.date() <= start_value:
                    continue
            elif isinstance(end_value, date) and end_value <= start_value:
                continue
        sanitized.add_component(component)

    return sanitized


def _component_to_events(
    component,
    settings: AppSettings,
    timezone: ZoneInfo,
    start_date: date,
    day_count: int,
) -> list[tuple[date, str, tuple[int, time, str] | None, CalendarEvent]]:
    status = str(component.get("STATUS", "")).upper()
    if status == "CANCELLED":
        return []

    raw_title = str(component.get("SUMMARY", "Untitled Event"))
    display_title = raw_title
    dashboard_title = _dashboard_title(raw_title)

    if component.get("DTSTART") is None:
        return []

    start_value = component.decoded("DTSTART")
    end_value = component.decoded("DTEND") if component.get("DTEND") is not None else None
    if not isinstance(start_value, (date, datetime)):
        return []
    is_all_day = isinstance(start_value, date) and not isinstance(start_value, datetime)
    visible_dates = {start_date + timedelta(days=offset) for offset in range(day_count)}

    if is_all_day:
        event_end_date = _all_day_end_date(start_value, end_value)
        affected_dates = [
            current_day
            for current_day in _date_range(start_value, event_end_date)
            if current_day in visible_dates
        ]
        if not affected_dates:
            return []

        is_multi_day = len(list(_date_range(start_value, event_end_date))) > 1
        bucket_name = "multi_day" if is_multi_day else "all_day"
        results: list[tuple[date, str, tuple[int, time, str] | None, CalendarEvent]] = []
        for current_day in affected_dates:
            results.append(
                (
                    current_day,
                    bucket_name,
                    None,
                    CalendarEvent(
                        start_time="",
                        compact_start_time="",
                        raw_title=raw_title,
                        display_title=display_title,
                        dashboard_title=dashboard_title,
                        is_all_day=True,
                        is_multi_day=is_multi_day,
                    ),
                )
            )
        return results

    localized = _to_local_datetime(start_value, timezone)
    if end_value is not None and isinstance(end_value, datetime):
        localized_end = _to_local_datetime(end_value, timezone)
        if localized_end <= localized:
            return []
    event_day = localized.date()
    if event_day not in visible_dates:
        return []
    sort_key = (1, localized.timetz().replace(tzinfo=None), raw_title.lower())

    return [(
        event_day,
        "timed",
        sort_key,
        CalendarEvent(
            start_time=format_clock(localized, settings.language),
            compact_start_time=_compact_time(localized),
            raw_title=raw_title,
            display_title=display_title,
            dashboard_title=dashboard_title,
            is_all_day=False,
            is_multi_day=False,
        ),
    )]


def _compact_time(value: datetime) -> str:
    hour = value.strftime("%I").lstrip("0") or "12"
    minute = value.strftime("%M")
    suffix = value.strftime("%p")[0]
    if minute == "00":
        return f"{hour}{suffix}"
    return f"{hour}:{minute}{suffix}"


def _dashboard_title(raw_title: str) -> str:
    title = " ".join(raw_title.split())

    stripped = _strip_leading_owner(title)
    if stripped:
        title = stripped

    replacements = {
        "appointment": "appt",
        "appointments": "appts",
        "committee": "comm.",
        "meeting": "mtg",
        "meetings": "mtgs",
        "thursday": "Thurs",
        "wednesday": "Wed",
        "tuesday": "Tues",
        "monday": "Mon",
        "friday": "Fri",
        "saturday": "Sat",
        "sunday": "Sun",
        "with": "w/",
        " and ": " & ",
    }

    lowered = title.lower()
    for source, target in replacements.items():
        if source.startswith(" ") and source.endswith(" "):
            lowered = lowered.replace(source, target)
        else:
            lowered = lowered.replace(source, target.lower())

    words = lowered.split()
    if not words:
        return raw_title

    restored: list[str] = []
    for index, word in enumerate(words):
        if word in {"thurs", "wed", "tues", "mon", "fri", "sat", "sun"}:
            restored.append(word.title())
        elif word in {"appt", "appts", "comm.", "mtg", "mtgs", "w/"}:
            restored.append(word)
        elif index == 0:
            restored.append(word.capitalize())
        else:
            restored.append(word)

    return " ".join(restored)


def _strip_leading_owner(title: str) -> str:
    for separator in (":", " - "):
        if separator not in title:
            continue
        prefix, suffix = title.split(separator, 1)
        prefix = prefix.strip()
        suffix = suffix.strip()
        if not suffix:
            return title
        if len(prefix) <= 18 and len(suffix) >= 4:
            return suffix
    return title


def _to_local_datetime(value: datetime, timezone: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def _all_day_end_date(start_value: date, end_value) -> date:
    if end_value is None:
        return start_value + timedelta(days=1)
    if isinstance(end_value, datetime):
        end_date = end_value.date()
    else:
        end_date = end_value
    if end_date <= start_value:
        return start_value + timedelta(days=1)
    return end_date


def _date_range(start_value: date, exclusive_end: date):
    current_day = start_value
    while current_day < exclusive_end:
        yield current_day
        current_day += timedelta(days=1)
