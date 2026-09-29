"""CSV validation and deterministic process graph discovery."""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

HONESTY_BOUNDARY = (
    "This is deterministic, rule-based process mining on declared CSV inputs. "
    "Bundled fixture logs are synthetic and fictional. It is not a learned model "
    "or live analysis, and makes no claim about a real company's process or real employee monitoring."
)
REQUIRED_COLUMNS = ("case_id", "activity", "start", "end", "actor")
AUTOMATED_ACTORS = {"system", "bot", "automation", "automated", "service", "api"}


@dataclass(frozen=True)
class Event:
    case_id: str
    activity: str
    start: datetime
    end: datetime
    actor: str
    row_number: int


@dataclass
class ParseResult:
    events: list[Event]
    issues: list[str]
    row_count: int


def _parse_timestamp(raw: str, field: str) -> tuple[datetime | None, str | None]:
    try:
        value = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None, f"invalid_{field}_timestamp"
    if value.tzinfo is None or value.utcoffset() is None:
        return None, f"timezone_required_{field}"
    return value.astimezone(timezone.utc), None


def parse_csv(path: str | Path) -> ParseResult:
    """Read valid events while collecting stable, row-specific rejection reasons."""
    events: list[Event] = []
    issues: list[str] = []
    row_count = 0
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        missing = [name for name in REQUIRED_COLUMNS if name not in headers]
        if missing:
            raise ValueError("missing_columns:" + ",".join(missing))
        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            errors: list[str] = []
            if None in row:
                errors.append("extra_fields")
            values = {field: (row.get(field) or "").strip() for field in REQUIRED_COLUMNS}
            for field in REQUIRED_COLUMNS:
                if not values[field]:
                    errors.append(f"empty_{field}")
            start, start_error = _parse_timestamp(values["start"], "start") if values["start"] else (None, None)
            end, end_error = _parse_timestamp(values["end"], "end") if values["end"] else (None, None)
            if start_error:
                errors.append(start_error)
            if end_error:
                errors.append(end_error)
            if start and end and end < start:
                errors.append("end_before_start")
            if errors:
                issues.append(f"row_{row_number}:" + ",".join(errors))
                continue
            assert start is not None and end is not None
            events.append(Event(values["case_id"], values["activity"], start, end, values["actor"], row_number))
    if not events:
        raise ValueError("no_valid_events; rejected_rows=" + str(len(issues)))
    return ParseResult(events, issues, row_count)


def _minutes(delta_seconds: float) -> float:
    return round(delta_seconds / 60, 3)


def _median(values: Iterable[float]) -> float:
    return round(float(statistics.median(list(values))), 3)


def discover_graph(path: str | Path) -> dict:
    parsed = parse_csv(path)
    by_case: dict[str, list[Event]] = defaultdict(list)
    for event in parsed.events:
        by_case[event.case_id].append(event)

    durations: dict[str, list[float]] = defaultdict(list)
    waits: dict[str, list[float]] = defaultdict(list)
    actors: dict[str, list[str]] = defaultdict(list)
    arrivals: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    transitions: Counter[tuple[str, str]] = Counter()

    for case_id in sorted(by_case):
        case_events = sorted(by_case[case_id], key=lambda item: (item.start, item.end, item.activity, item.row_number))
        previous: Event | None = None
        for event in case_events:
            duration = _minutes((event.end - event.start).total_seconds())
            arrival = previous.end if previous else event.start
            wait = max(0.0, _minutes((event.start - arrival).total_seconds()))
            durations[event.activity].append(duration)
            waits[event.activity].append(wait)
            actors[event.activity].append(event.actor)
            arrivals[event.activity].append((arrival, event.start))
            if previous:
                transitions[(previous.activity, event.activity)] += 1
            previous = event

    activities = {}
    for activity in sorted(durations):
        queue_lengths = []
        for arrival, service_start in arrivals[activity]:
            # A case is queued when it has arrived but its service has not started.
            queue_lengths.append(sum(1 for other_arrival, other_start in arrivals[activity]
                                     if other_arrival <= arrival and other_start > arrival))
        actor_values = actors[activity]
        manual_share = round(sum(actor.strip().lower() not in AUTOMATED_ACTORS for actor in actor_values) / len(actor_values), 3)
        activities[activity] = {
            "event_count": len(durations[activity]),
            "median_duration_minutes": _median(durations[activity]),
            "median_wait_minutes": _median(waits[activity]),
            "mean_wait_minutes": round(statistics.fmean(waits[activity]), 3),
            "mean_queue_length": round(statistics.fmean(queue_lengths), 3),
            "max_queue_length": max(queue_lengths, default=0),
            "manual_actor_share": manual_share,
        }

    edges = [
        {"from": source, "to": target, "frequency": frequency}
        for (source, target), frequency in sorted(transitions.items())
    ]
    return {
        "schema_version": 1,
        "honesty_boundary": HONESTY_BOUNDARY,
        "analysis": "deterministic_rule_based",
        "input_summary": {
            "rows_read": parsed.row_count,
            "events_accepted": len(parsed.events),
            "rows_rejected": len(parsed.issues),
            "case_count": len(by_case),
            "validation_errors": parsed.issues,
        },
        "activity_count": len(activities),
        "activities": activities,
        "edges": edges,
    }


def graph_json(graph: dict) -> str:
    return json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
