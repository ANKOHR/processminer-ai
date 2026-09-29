"""Deterministic, fictional event logs used by the examples and tests."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIELDS = ("case_id", "activity", "start", "end", "actor")


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _event(case_id: str, activity: str, start: datetime, duration: int, actor: str) -> dict[str, str]:
    return {
        "case_id": case_id,
        "activity": activity,
        "start": _timestamp(start),
        "end": _timestamp(start + timedelta(minutes=duration)),
        "actor": actor,
    }


def order_fulfilment_events() -> list[dict[str, str]]:
    """Create 12 fictional orders with a measured queue before picking."""
    origin = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
    rows: list[dict[str, str]] = []
    previous_pick_end: datetime | None = None
    for index in range(12):
        case_id = f"SYN-ORDER-{index + 1:03d}"
        arrival = origin + timedelta(minutes=index * 3)
        current = arrival
        rows.append(_event(case_id, "order_intake", current, 2, f"agent-{index % 3 + 1}"))
        current += timedelta(minutes=2)
        rows.append(_event(case_id, "payment_validation", current, 6, f"agent-{index % 3 + 1}"))
        current += timedelta(minutes=6)
        rows.append(_event(case_id, "inventory_check", current, 2, "system"))
        pick_arrival = current + timedelta(minutes=2)
        pick_start = max(pick_arrival, previous_pick_end or pick_arrival)
        rows.append(_event(case_id, "pick_items", pick_start, 30, f"picker-{index % 2 + 1}"))
        previous_pick_end = pick_start + timedelta(minutes=30)
        current = previous_pick_end
        rows.append(_event(case_id, "pack_items", current, 8, f"packer-{index % 2 + 1}"))
        current += timedelta(minutes=8)
        rows.append(_event(case_id, "shipping_label_creation", current, 4, f"agent-{index % 3 + 1}"))
        current += timedelta(minutes=4)
        rows.append(_event(case_id, "dispatch", current, 2, "system"))
    return rows


def clean_control_events() -> list[dict[str, str]]:
    """Create a fictional, promptly serviced log with no queue or idle waits."""
    origin = datetime(2026, 2, 2, 9, 0, tzinfo=timezone.utc)
    rows: list[dict[str, str]] = []
    for index in range(8):
        case_id = f"SYN-CONTROL-{index + 1:03d}"
        current = origin + timedelta(hours=index)
        for activity, duration, actor in (
            ("order_intake", 2, "agent-1"),
            ("payment_validation", 3, "agent-1"),
            ("inventory_check", 2, "system"),
            ("pick_items", 5, "picker-1"),
            ("pack_items", 3, "packer-1"),
            ("shipping_label_creation", 2, "agent-1"),
            ("dispatch", 1, "system"),
        ):
            rows.append(_event(case_id, activity, current, duration, actor))
            current += timedelta(minutes=duration)
    return rows


def write_fixtures(output_dir: str | Path) -> list[Path]:
    """Write the fixed synthetic examples and return their paths."""
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    products = (
        ("order_fulfilment.csv", order_fulfilment_events()),
        ("clean_control.csv", clean_control_events()),
    )
    written = []
    for filename, rows in products:
        path = folder / filename
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        written.append(path)
    return written
