"""Stable Markdown and HTML reporting from a serialized graph."""

from __future__ import annotations

import html

from .analysis import find_bottlenecks, score_targets
from .miner import HONESTY_BOUNDARY


def _num(value: float) -> str:
    return f"{value:g}"


def render_markdown(graph: dict) -> str:
    bottlenecks = find_bottlenecks(graph)
    targets = score_targets(graph)
    summary = graph["input_summary"]
    lines = [
        "# ProcessMiner AI report",
        "",
        f"> HONESTY BOUNDARY: {graph.get('honesty_boundary', HONESTY_BOUNDARY)}",
        "",
        "## Process summary",
        "",
        f"- Cases: {summary['case_count']}",
        f"- Accepted events: {summary['events_accepted']}",
        f"- Rejected rows: {summary['rows_rejected']}",
        f"- Discovered activities: {graph['activity_count']}",
        f"- Observed transitions: {len(graph['edges'])}",
        "",
        "## Discovered graph",
        "",
        "Edges are ordered per case by event start time. Frequencies count observed case transitions.",
        "",
        "| From | To | Frequency |",
        "|---|---|---:|",
    ]
    for edge in graph["edges"]:
        lines.append(f"| `{edge['from']}` | `{edge['to']}` | {edge['frequency']} |")
    lines.extend(["", "## Stage timing and queues", "", "| Activity | Events | Median duration (min) | Median wait (min) | Mean queue | Max queue |", "|---|---:|---:|---:|---:|---:|"])
    for activity, metrics in graph["activities"].items():
        lines.append(
            f"| `{activity}` | {metrics['event_count']} | {_num(metrics['median_duration_minutes'])} | "
            f"{_num(metrics['median_wait_minutes'])} | {_num(metrics['mean_queue_length'])} | {metrics['max_queue_length']} |"
        )
    lines.extend(["", "## Bottleneck findings", ""])
    if not bottlenecks["findings"]:
        lines.append("No stages met the documented wait or queue thresholds.")
    else:
        lines.append("Thresholds: median wait at least 10 minutes or mean queue length at least 2. Ranked by maximum normalized threshold impact.")
        lines.append("")
        for finding in bottlenecks["findings"]:
            lines.append(
                f"- **{finding['activity']}**: median wait {_num(finding['median_wait_minutes'])} min; "
                f"mean queue {_num(finding['mean_queue_length'])}; max queue {finding['max_queue_length']}; "
                f"evidence `{finding['evidence_pointer']}`; fields `{', '.join(finding['evidence_fields'])}`."
            )
    lines.extend(["", "## Ranked automation targets", "", f"Formula: `{targets['formula']}`.", ""])
    lines.append("Repetition is event count divided by the most frequent activity count. Duration factor is median duration divided by the longest median. Manual share treats actors named system, bot, automation, automated, service, or api as automated. Suitability is a fixed keyword rule.")
    lines.append("")
    for row in targets["ranking"]:
        inputs = row["inputs"]
        lines.append(
            f"{row['rank']}. **{row['activity']}** score {row['score']:.4f}; "
            f"events={inputs['event_count']}, repetition={inputs['repetition']:.4f}, "
            f"manual_share={inputs['manual_actor_share']:.3f}, duration_factor={inputs['duration_factor']:.4f}, "
            f"suitability={inputs['rule_suitability']:.1f}. Evidence `graph.activities.{row['activity']}`."
        )
    if summary["validation_errors"]:
        lines.extend(["", "## Rejected row details", ""])
        lines.extend(f"- `{issue}`" for issue in summary["validation_errors"])
    return "\n".join(lines) + "\n"


def render_html(graph: dict) -> str:
    bottlenecks = find_bottlenecks(graph)
    targets = score_targets(graph)
    summary = graph["input_summary"]
    banner = html.escape(graph.get("honesty_boundary", HONESTY_BOUNDARY))
    summary_items = "".join(
        f"<dt>{html.escape(label)}</dt><dd>{value}</dd>"
        for label, value in (
            ("Cases", summary["case_count"]),
            ("Accepted events", summary["events_accepted"]),
            ("Rejected rows", summary["rows_rejected"]),
            ("Discovered activities", graph["activity_count"]),
            ("Observed transitions", len(graph["edges"])),
        )
    )
    edge_rows = "".join(
        f"<tr><td>{html.escape(edge['from'])}</td><td>{html.escape(edge['to'])}</td><td>{edge['frequency']}</td></tr>"
        for edge in graph["edges"]
    ) or '<tr><td colspan="3">No transitions found.</td></tr>'
    stage_rows = "".join(
        "<tr>"
        f"<td>{html.escape(activity)}</td><td>{metrics['event_count']}</td>"
        f"<td>{_num(metrics['median_duration_minutes'])}</td><td>{_num(metrics['median_wait_minutes'])}</td>"
        f"<td>{_num(metrics['mean_queue_length'])}</td><td>{metrics['max_queue_length']}</td></tr>"
        for activity, metrics in graph["activities"].items()
    )
    if bottlenecks["findings"]:
        bottleneck_rows = "".join(
            "<tr>"
            f"<td>{html.escape(row['activity'])}</td><td>{row['impact_score']:.3f}</td>"
            f"<td>{_num(row['median_wait_minutes'])}</td><td>{_num(row['mean_queue_length'])}</td>"
            f"<td>{row['max_queue_length']}</td><td><code>{html.escape(row['evidence_pointer'])}</code></td></tr>"
            for row in bottlenecks["findings"]
        )
    else:
        bottleneck_rows = '<tr><td colspan="6">No stages met the documented wait or queue thresholds.</td></tr>'
    target_rows = "".join(
        "<tr>"
        f"<td>{row['rank']}</td><td>{html.escape(row['activity'])}</td><td>{row['score']:.4f}</td>"
        f"<td>{row['inputs']['repetition']:.4f}</td><td>{row['inputs']['manual_actor_share']:.3f}</td>"
        f"<td>{row['inputs']['duration_factor']:.4f}</td><td>{row['inputs']['rule_suitability']:.1f}</td>"
        f"<td><code>graph.activities.{html.escape(row['activity'])}</code></td></tr>"
        for row in targets["ranking"]
    )
    rejected_rows = "".join(f"<li><code>{html.escape(issue)}</code></li>" for issue in summary["validation_errors"])
    rejected_section = f"<h2>Rejected row details</h2><ul>{rejected_rows}</ul>" if rejected_rows else ""
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>ProcessMiner AI report</title><style>body{font:16px/1.55 system-ui,sans-serif;"
        "max-width:1200px;margin:2rem auto;padding:0 1rem;color:#18212f}"
        ".honesty{padding:1rem;background:#fff4cc;border:1px solid #d7aa32;font-weight:600}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0 2rem}th,td{padding:.55rem .7rem;"
        "border-bottom:1px solid #d9e0e8;text-align:left}th{background:#f3f6fa}code{overflow-wrap:anywhere}"
        "</style>"
        f"</head><body><h1>ProcessMiner AI report</h1><p class=\"honesty\">HONESTY BOUNDARY: {banner}</p>"
        f"<h2>Process summary</h2><dl>{summary_items}</dl>"
        "<h2>Discovered graph</h2><p>Edges are ordered per case by event start time. Frequencies count observed adjacent transitions.</p>"
        "<table><thead><tr><th>From</th><th>To</th><th>Frequency</th></tr></thead><tbody>"
        f"{edge_rows}</tbody></table>"
        "<h2>Stage timing and queues</h2><table><thead><tr><th>Activity</th><th>Events</th><th>Median duration (min)</th>"
        "<th>Median wait (min)</th><th>Mean queue</th><th>Max queue</th></tr></thead><tbody>"
        f"{stage_rows}</tbody></table>"
        "<h2>Bottleneck findings</h2><p>Thresholds: median wait at least 10 minutes or mean queue length at least 2."
        " Findings sort by normalized threshold impact.</p><table><thead><tr><th>Activity</th><th>Impact</th>"
        "<th>Median wait (min)</th><th>Mean queue</th><th>Max queue</th><th>Evidence pointer</th></tr></thead><tbody>"
        f"{bottleneck_rows}</tbody></table>"
        f"<h2>Ranked automation targets</h2><p>Formula: <code>{html.escape(targets['formula'])}</code></p>"
        "<table><thead><tr><th>Rank</th><th>Activity</th><th>Score</th><th>Repetition</th><th>Manual share</th>"
        "<th>Duration factor</th><th>Suitability</th><th>Evidence pointer</th></tr></thead><tbody>"
        f"{target_rows}</tbody></table>{rejected_section}</body></html>\n"
    )
