import json
from pathlib import Path

import pytest

import cli_report


def test_load_rows_reads_results_array(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(
        json.dumps({"title": "Line A", "results": [{"status": "pass", "lot_id": "L1"}]}),
        encoding="utf-8",
    )
    title, rows = cli_report.load_rows(path)
    assert title == "Line A"
    assert len(rows) == 1


def test_normalize_maps_aliases() -> None:
    row = cli_report.normalize({"result": "OK", "name": "thickness", "actual": "10"})
    assert row["status"] == "ok"
    assert row["check"] == "thickness"
    assert row["value"] == "10"


@pytest.mark.parametrize(
    ("status", "code"),
    [("pass", 0), ("fail", 1), ("hold", 2)],
)
def test_main_exit_codes(tmp_path: Path, status: str, code: int) -> None:
    path = tmp_path / "rows.json"
    path.write_text(
        json.dumps({"results": [{"status": status, "lot_id": "L1", "check": "x"}]}),
        encoding="utf-8",
    )
    assert cli_report.main(["-f", str(path), "--no-progress", "--no-color"]) == code


def test_main_missing_file() -> None:
    with pytest.raises(SystemExit, match="file not found"):
        cli_report.main(["-f", "missing.json", "--no-progress"])
