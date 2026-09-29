from pathlib import Path

from processminer.fixtures import FIELDS, write_fixtures


def test_fixtures_are_deterministic(tmp_path: Path) -> None:
    first = write_fixtures(tmp_path / "first")
    second = write_fixtures(tmp_path / "second")
    assert [path.name for path in first] == ["order_fulfilment.csv", "clean_control.csv"]
    assert [path.read_bytes() for path in first] == [path.read_bytes() for path in second]


def test_fixtures_have_declared_csv_fields_and_synthetic_ids(tmp_path: Path) -> None:
    order_log, control_log = write_fixtures(tmp_path)
    for path in (order_log, control_log):
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        assert tuple(first_line.split(",")) == FIELDS
        assert "SYN-" in path.read_text(encoding="utf-8")


def test_order_fixture_contains_planted_bottleneck_and_candidates(tmp_path: Path) -> None:
    path, _ = write_fixtures(tmp_path)
    contents = path.read_text(encoding="utf-8")
    assert "pick_items" in contents
    assert "payment_validation" in contents
    assert "shipping_label_creation" in contents
