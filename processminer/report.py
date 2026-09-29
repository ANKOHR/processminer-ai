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
    markdown = render_markdown(graph)
    # Keep the HTML renderer dependency-free. Convert the stable report rows into escaped HTML.
    escaped = html.escape(markdown)
    banner = html.escape(graph.get("honesty_boundary", HONESTY_BOUNDARY))
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>ProcessMiner AI report</title><style>body{font:16px/1.55 system-ui,sans-serif;"
        "max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18212f}"
        ".honesty{padding:1rem;background:#fff4cc;border:1px solid #d7aa32;font-weight:600}"
        "pre{white-space:pre-wrap;background:#f5f7fa;padding:1rem;border-radius:8px}</style>"
        f"</head><body><h1>ProcessMiner AI report</h1><p class=\"honesty\">HONESTY BOUNDARY: {banner}</p>"
        f"<pre>{escaped}</pre></body></html>\n"
    )
