import json
import subprocess
import sys
from pathlib import Path

from processminer.cli import main
from processminer.fixtures import write_fixtures


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "processminer", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_states_honesty_boundary(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit as error:
        assert error.code == 0
    output = capsys.readouterr().out
    assert "synthetic and fictional" in output
    assert "real-employee monitoring" in output


def test_fixtures_cli_writes_both_synthetic_logs(tmp_path: Path) -> None:
    result = run_cli("fixtures", "--out", str(tmp_path / "data"), cwd=Path.cwd())
    assert result.returncode == 0, result.stderr
    assert "HONESTY BOUNDARY" in result.stdout
    assert (tmp_path / "data" / "order_fulfilment.csv").exists()
    assert (tmp_path / "data" / "clean_control.csv").exists()


def test_mine_cli_emits_graph_json(tmp_path: Path) -> None:
    log_path, _ = write_fixtures(tmp_path)
    result = run_cli("mine", str(log_path), cwd=Path.cwd())
    assert result.returncode == 0, result.stderr
    graph = json.loads(result.stdout)
    assert graph["activities"]["pick_items"]["event_count"] == 12


def test_bottlenecks_targets_and_reports_cli_smoke(tmp_path: Path) -> None:
    log_path, _ = write_fixtures(tmp_path / "fixtures")
    graph_path = tmp_path / "graph.json"
    mine = run_cli("mine", str(log_path), "--out", str(graph_path), cwd=Path.cwd())
    assert mine.returncode == 0, mine.stderr
    bottlenecks = run_cli("bottlenecks", str(graph_path), cwd=Path.cwd())
    targets = run_cli("targets", str(graph_path), cwd=Path.cwd())
    markdown = run_cli("report", str(graph_path), "--format", "md", cwd=Path.cwd())
    html = run_cli("report", str(graph_path), "--format", "html", cwd=Path.cwd())
    assert bottlenecks.returncode == 0 and json.loads(bottlenecks.stdout)["findings"][0]["activity"] == "pick_items"
    assert targets.returncode == 0 and json.loads(targets.stdout)["ranking"][0]["activity"] == "payment_validation"
    assert markdown.returncode == 0 and "graph.activities.pick_items" in markdown.stdout
    assert html.returncode == 0 and "HONESTY BOUNDARY" in html.stdout


def test_cli_rejects_malformed_only_input_with_named_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("case_id,activity,start,end,actor\na,b,nope,nope,x\n", encoding="utf-8")
    result = run_cli("mine", str(bad), cwd=Path.cwd())
    assert result.returncode == 2
    assert "no_valid_events" in result.stderr
