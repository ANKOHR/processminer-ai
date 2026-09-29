import json

from processminer.report import render_html, render_markdown


def test_markdown_contains_findings_evidence_and_honesty_banner(order_graph: dict) -> None:
    report = render_markdown(order_graph)
    assert "HONESTY BOUNDARY" in report
    assert "synthetic and fictional" in report
    assert "pick_items" in report
    assert "148.5" in report
    assert "graph.activities.pick_items" in report
    assert "payment_validation" in report


def test_html_contains_honesty_banner_and_measured_findings(order_graph: dict) -> None:
    report = render_html(order_graph)
    assert "HONESTY BOUNDARY" in report
    assert "synthetic and fictional" in report
    assert "graph.activities.pick_items" in report
    assert "148.5" in report


def test_reports_are_byte_identical_across_reruns(order_graph: dict) -> None:
    reloaded = json.loads(json.dumps(order_graph, sort_keys=True))
    assert render_markdown(order_graph).encode() == render_markdown(reloaded).encode()
    assert render_html(order_graph).encode() == render_html(reloaded).encode()
