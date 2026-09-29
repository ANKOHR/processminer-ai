"""Command line interface for the deterministic process mining workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import find_bottlenecks, score_targets
from .fixtures import write_fixtures
from .miner import HONESTY_BOUNDARY, discover_graph, graph_json
from .report import render_html, render_markdown

DESCRIPTION = (
    "ProcessMiner AI performs deterministic, rule-based process mining on CSV event logs. "
    "Bundled fixtures are synthetic and fictional. No learned model, live source, real-company claim, "
    "or real-employee monitoring is involved."
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="processminer", description=DESCRIPTION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fixtures = subparsers.add_parser("fixtures", help="write deterministic synthetic example logs", description=DESCRIPTION)
    fixtures.add_argument("--out", required=True, help="directory to receive the two synthetic CSV logs")

    mine = subparsers.add_parser("mine", help="discover activities, transitions, timings, and queues", description=DESCRIPTION)
    mine.add_argument("log", help="CSV event log")
    mine.add_argument("--out", help="write graph JSON to this path instead of stdout")

    bottlenecks = subparsers.add_parser("bottlenecks", help="rank threshold findings from graph JSON", description=DESCRIPTION)
    bottlenecks.add_argument("graph", help="graph JSON from processminer mine")
    bottlenecks.add_argument("--out", help="write findings JSON to this path instead of stdout")

    targets = subparsers.add_parser("targets", help="score activities using the documented fixed formula", description=DESCRIPTION)
    targets.add_argument("graph", help="graph JSON from processminer mine")
    targets.add_argument("--out", help="write ranked targets JSON to this path instead of stdout")

    report = subparsers.add_parser("report", help="render a stable Markdown or HTML report", description=DESCRIPTION)
    report.add_argument("graph", help="graph JSON from processminer mine")
    report.add_argument("--format", choices=("md", "html"), default="md")
    report.add_argument("--out", help="write report to this path instead of stdout")
    return parser


def _read_graph(path: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as stream:
        graph = json.load(stream)
    if not isinstance(graph, dict) or "activities" not in graph or "edges" not in graph:
        raise ValueError("invalid_graph_json: expected activities and edges")
    return graph


def _write_or_print(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {output}")
    else:
        sys.stdout.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "fixtures":
            paths = write_fixtures(args.out)
            print("HONESTY BOUNDARY: Synthetic, fictional example logs only. " + HONESTY_BOUNDARY)
            for path in paths:
                print(path)
        elif args.command == "mine":
            graph = discover_graph(args.log)
            _write_or_print(graph_json(graph), args.out)
            if graph["input_summary"]["validation_errors"]:
                for issue in graph["input_summary"]["validation_errors"]:
                    print("Rejected " + issue, file=sys.stderr)
        elif args.command == "bottlenecks":
            output = json.dumps(find_bottlenecks(_read_graph(args.graph)), indent=2, sort_keys=True) + "\n"
            _write_or_print(output, args.out)
        elif args.command == "targets":
            output = json.dumps(score_targets(_read_graph(args.graph)), indent=2, sort_keys=True) + "\n"
            _write_or_print(output, args.out)
        elif args.command == "report":
            graph = _read_graph(args.graph)
            content = render_html(graph) if args.format == "html" else render_markdown(graph)
            _write_or_print(content, args.out)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"processminer: {error}", file=sys.stderr)
        return 2
