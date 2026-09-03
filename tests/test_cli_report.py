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


def test_load_rows_accepts_root_array(tmp_path: Path) -> None:
    path = tmp_path / "rows.json"
    path.write_text(json.dumps([{"status": "pass", "lot_id": "L1"}]), encoding="utf-8")
    title, rows = cli_report.load_rows(path)
    assert title == ""
    assert len(rows) == 1


def test_load_rows_rejects_empty_rows(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"results": []}), encoding="utf-8")
    with pytest.raises(SystemExit, match="no rows to render"):
        cli_report.load_rows(path)


def test_load_rows_rejects_missing_array_key(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"title": "No rows"}), encoding="utf-8")
    with pytest.raises(SystemExit, match="must contain rows"):
        cli_report.load_rows(path)


def test_summary_includes_skip_count(capsys) -> None:
    rows = [
        cli_report.normalize({"status": "pass"}),
        cli_report.normalize({"status": "skip"}),
    ]
    cli_report.summary(False, rows)
    output = capsys.readouterr().out
    assert "skip=1" in output


def test_main_title_override(tmp_path: Path, capsys) -> None:
    path = tmp_path / "rows.json"
    path.write_text(
        json.dumps(
            {
                "title": "File title",
                "results": [{"status": "pass", "lot_id": "L1", "check": "x"}],
            }
        ),
        encoding="utf-8",
    )
    assert (
        cli_report.main(
            ["-f", str(path), "--title", "CLI override", "--no-progress", "--no-color"]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "CLI override" in output
    assert "File title" not in output
