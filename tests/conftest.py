from pathlib import Path

import pytest

from processminer.fixtures import write_fixtures
from processminer.miner import discover_graph


@pytest.fixture
def fixture_logs(tmp_path: Path) -> dict[str, Path]:
    return {path.stem: path for path in write_fixtures(tmp_path / "fixtures")}


@pytest.fixture
def order_graph(fixture_logs: dict[str, Path]) -> dict:
    return discover_graph(fixture_logs["order_fulfilment"])
