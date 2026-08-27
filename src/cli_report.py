#!/usr/bin/env python3
"""Render QA / inspection JSON as a colored terminal report."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
WHITE = "\033[37m"


STATUS_STYLE = {
    "pass": (GREEN, "PASS"),
    "ok": (GREEN, "PASS"),
    "fail": (RED, "FAIL"),
    "ng": (RED, "FAIL"),
    "hold": (YELLOW, "HOLD"),
    "skip": (DIM, "SKIP"),
}


def colorize(enabled: bool, code: str, text: str) -> str:
    if not enabled:
        return text
    return f"{code}{text}{RESET}"


def load_rows(path: Path) -> tuple[str, list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    title = ""
    rows: list[dict[str, Any]]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        title = str(data.get("title") or data.get("name") or "")
        for key in ("rows", "items", "results", "checks"):
            if isinstance(data.get(key), list):
                rows = data[key]
                break
        else:
            raise SystemExit("JSON object must contain rows/items/results/checks array")
    else:
        raise SystemExit("JSON root must be array or object")
    if not rows:
        raise SystemExit("no rows to render")
    return title, rows


def field(row: dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        if k in row and row[k] is not None:
            return str(row[k])
    return default


def normalize(row: dict[str, Any]) -> dict[str, str]:
    status = field(row, "status", "result", default="skip").strip().lower()
    return {
        "lot_id": field(row, "lot_id", "lot", "id", default="-"),
        "check": field(row, "check", "name", "metric", default="-"),
        "status": status,
        "value": field(row, "value", "actual", default=""),
        "limit": field(row, "limit", "spec", default=""),
        "note": field(row, "note", "message", default=""),
    }


def progress_bar(enabled: bool, ratio: float, width: int = 28) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = int(round(width * ratio))
    bar = "#" * filled + "-" * (width - filled)
    label = f"[{bar}] {int(ratio * 100):3d}%"
    return colorize(enabled, CYAN, label)


def table(enabled: bool, rows: list[dict[str, str]]) -> None:
    headers = ("LOT", "CHECK", "STATUS", "VALUE", "LIMIT", "NOTE")
    cells = []
    for r in rows:
        style, label = STATUS_STYLE.get(r["status"], (WHITE, r["status"].upper() or "?"))
        cells.append(
            (
                r["lot_id"],
                r["check"],
                colorize(enabled, style + BOLD, f"{label:4s}"),
                r["value"],
                r["limit"],
                r["note"],
            )
        )
    # width calc without ANSI for status column
    plain_status = [STATUS_STYLE.get(r["status"], (WHITE, r["status"].upper() or "?"))[1] for r in rows]
    widths = [
        max(len(headers[0]), *(len(c[0]) for c in cells)),
        max(len(headers[1]), *(len(c[1]) for c in cells)),
        max(len(headers[2]), *(len(s) for s in plain_status)),
        max(len(headers[3]), *(len(c[3]) for c in cells)),
        max(len(headers[4]), *(len(c[4]) for c in cells)),
        max(len(headers[5]), *(len(c[5]) for c in cells)),
    ]
    cols = shutil.get_terminal_size((100, 20)).columns
    fixed = sum(widths[:5]) + 2 * 5
    widths[5] = max(8, min(widths[5], max(8, cols - fixed - 2)))

    print(
        colorize(enabled, DIM, "  ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers)))
    )
    print(colorize(enabled, DIM, "  ".join("-" * widths[i] for i in range(6))))
    for r, cell in zip(rows, cells):
        style, label = STATUS_STYLE.get(r["status"], (WHITE, r["status"].upper() or "?"))
        status_col = colorize(enabled, style + BOLD, f"{label:<{widths[2]}}")
        note = cell[5][: widths[5]]
        print(
            f"{cell[0]:<{widths[0]}}  {cell[1]:<{widths[1]}}  {status_col}  "
            f"{cell[3]:<{widths[3]}}  {cell[4]:<{widths[4]}}  {note:<{widths[5]}}"
        )


def summary(enabled: bool, rows: list[dict[str, str]]) -> None:
    counts = {"pass": 0, "fail": 0, "hold": 0, "skip": 0, "other": 0}
    for r in rows:
        key = r["status"]
        if key in ("ok",):
            key = "pass"
        if key in ("ng",):
            key = "fail"
        if key in counts:
            counts[key] += 1
        else:
            counts["other"] += 1
    total = len(rows)
    passed = counts["pass"]
    print()
    print(progress_bar(enabled, passed / total if total else 0.0))
    bits = [
        colorize(enabled, GREEN, f"pass={counts['pass']}"),
        colorize(enabled, RED, f"fail={counts['fail']}"),
        colorize(enabled, YELLOW, f"hold={counts['hold']}"),
        colorize(enabled, DIM, f"skip={counts['skip']}"),
    ]
    print("  ".join(bits) + (f"  other={counts['other']}" if counts["other"] else ""))


def animate_progress(enabled: bool, steps: int = 12) -> None:
    for i in range(steps + 1):
        sys.stdout.write("\r" + progress_bar(enabled, i / steps) + " loading")
        sys.stdout.flush()
        time.sleep(0.03)
    sys.stdout.write("\r" + " " * 48 + "\r")
    sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Colored terminal report for inspection JSON")
    p.add_argument("--file", "-f", type=Path, required=True)
    p.add_argument("--title", default="")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--no-progress", action="store_true", help="Skip intro progress animation")
    args = p.parse_args(argv)

    if not args.file.is_file():
        raise SystemExit(f"file not found: {args.file}")

    enabled = not args.no_color and sys.stdout.isatty()
    file_title, raw_rows = load_rows(args.file)
    rows = [normalize(r) for r in raw_rows]
    title = args.title or file_title or "Inspection report"

    if not args.no_progress:
        animate_progress(enabled)

    print(colorize(enabled, BOLD, title))
    print(colorize(enabled, DIM, f"source: {args.file}  rows: {len(rows)}"))
    print()
    table(enabled, rows)
    summary(enabled, rows)

    failed = sum(1 for r in rows if r["status"] in {"fail", "ng"})
    held = sum(1 for r in rows if r["status"] == "hold")
    if failed:
        print(colorize(enabled, RED + BOLD, "\nResult: FAIL"))
        return 1
    if held:
        print(colorize(enabled, YELLOW + BOLD, "\nResult: HOLD"))
        return 2
    print(colorize(enabled, GREEN + BOLD, "\nResult: PASS"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
