import json

import pytest

from processminer.miner import discover_graph, graph_json


EXPECTED_ACTIVITIES = [
    "order_intake",
    "payment_validation",
    "inventory_check",
    "pick_items",
    "pack_items",
    "shipping_label_creation",
    "dispatch",
]


def test_graph_discovers_planted_stages_and_ordered_transitions(order_graph: dict) -> None:
    assert list(order_graph["activities"]) == sorted(EXPECTED_ACTIVITIES)
    assert order_graph["activity_count"] == 7
    assert [(edge["from"], edge["to"], edge["frequency"]) for edge in order_graph["edges"]] == [
        ("inventory_check", "pick_items", 12),
        ("order_intake", "payment_validation", 12),
        ("pack_items", "shipping_label_creation", 12),
        ("payment_validation", "inventory_check", 12),
        ("pick_items", "pack_items", 12),
        ("shipping_label_creation", "dispatch", 12),
    ]


def test_stage_duration_and_wait_medians_match_hand_calculation(order_graph: dict) -> None:
    assert order_graph["activities"]["order_intake"]["median_duration_minutes"] == 2
    assert order_graph["activities"]["payment_validation"]["median_duration_minutes"] == 6
    assert order_graph["activities"]["inventory_check"]["median_duration_minutes"] == 2
    assert order_graph["activities"]["pick_items"]["median_duration_minutes"] == 30
    assert order_graph["activities"]["pack_items"]["median_duration_minutes"] == 8
    assert order_graph["activities"]["shipping_label_creation"]["median_duration_minutes"] == 4
    assert order_graph["activities"]["dispatch"]["median_duration_minutes"] == 2
    assert order_graph["activities"]["pick_items"]["median_wait_minutes"] == 148.5
    assert order_graph["activities"]["payment_validation"]["median_wait_minutes"] == 0


def test_queue_length_is_measured_from_arrival_and_service_timestamps(order_graph: dict) -> None:
    pick = order_graph["activities"]["pick_items"]
    assert pick["mean_queue_length"] > 2
    assert pick["max_queue_length"] == 10


def test_invalid_rows_are_named_and_valid_rows_still_mine(tmp_path) -> None:
    path = tmp_path / "mixed.csv"
    path.write_text(
        "case_id,activity,start,end,actor\n"
        "good,open,2026-01-01T09:00:00Z,2026-01-01T09:02:00Z,agent\n"
        "bad,close,not-a-time,2026-01-01T09:03:00Z,agent\n"
        "also-bad,close,2026-01-01T09:04:00Z,2026-01-01T09:03:00Z,agent\n",
        encoding="utf-8",
    )
    graph = discover_graph(path)
    assert graph["input_summary"]["events_accepted"] == 1
    assert graph["input_summary"]["rows_rejected"] == 2
    assert "row_3:invalid_start_timestamp" in graph["input_summary"]["validation_errors"]
    assert "row_4:end_before_start" in graph["input_summary"]["validation_errors"]


def test_missing_columns_raises_named_error(tmp_path) -> None:
    path = tmp_path / "missing.csv"
    path.write_text("case_id,activity,start,end\na,b,2026-01-01T00:00:00Z,2026-01-01T00:01:00Z\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing_columns:actor"):
        discover_graph(path)


def test_naive_timestamps_are_rejected_by_name(tmp_path) -> None:
    path = tmp_path / "naive.csv"
    path.write_text(
        "case_id,activity,start,end,actor\na,b,2026-01-01T00:00:00,2026-01-01T00:01:00,person\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no_valid_events"):
        discover_graph(path)


def test_graph_json_is_byte_stable(fixture_logs: dict) -> None:
    first = graph_json(discover_graph(fixture_logs["order_fulfilment"]))
    second = graph_json(discover_graph(fixture_logs["order_fulfilment"]))
    assert first == second
    assert first == graph_json(json.loads(first))
