from processminer.analysis import find_bottlenecks, score_targets
from processminer.fixtures import write_fixtures
from processminer.miner import discover_graph


def test_planted_bottleneck_ranks_first_with_measured_queue_evidence(order_graph: dict) -> None:
    result = find_bottlenecks(order_graph)
    assert result["findings"][0]["activity"] == "pick_items"
    finding = result["findings"][0]
    assert finding["median_wait_minutes"] == 148.5
    assert finding["mean_queue_length"] > 2
    assert finding["max_queue_length"] == 11
    assert finding["evidence_pointer"] == "graph.activities.pick_items"
    assert set(finding["evidence_fields"]) == {"median_wait_minutes", "mean_queue_length"}


def test_control_log_has_no_bottleneck_flags(tmp_path) -> None:
    _, control_path = write_fixtures(tmp_path)
    result = find_bottlenecks(discover_graph(control_path))
    assert result["findings"] == []


def test_automation_candidates_rank_in_documented_order(order_graph: dict) -> None:
    result = score_targets(order_graph)
    assert [row["activity"] for row in result["ranking"][:2]] == [
        "payment_validation",
        "shipping_label_creation",
    ]
    assert "0.35 * repetition" in result["formula"]


def test_target_score_is_hand_checkable(order_graph: dict) -> None:
    result = score_targets(order_graph)
    payment = result["ranking"][0]
    inputs = payment["inputs"]
    hand_score = (
        0.35 * inputs["repetition"]
        + 0.25 * inputs["manual_actor_share"]
        + 0.20 * inputs["duration_factor"]
        + 0.20 * inputs["rule_suitability"]
    )
    assert payment["score"] == round(hand_score, 4)
    assert inputs["suitability_terms_matched"] == ["payment_validation"]


def test_target_inputs_expose_all_formula_components(order_graph: dict) -> None:
    row = score_targets(order_graph)["ranking"][0]
    assert set(row["inputs"]) >= {
        "event_count",
        "repetition",
        "manual_actor_share",
        "median_duration_minutes",
        "duration_factor",
        "rule_suitability",
    }
