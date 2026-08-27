# cli-report

Render inspection / QA summaries in a readable terminal layout.

Inspired by rich console libraries (tables, status colors, progress) — stdlib ANSI only, no dependencies.

## Usage

```bash
python src/cli_report.py -f samples/inspection.json
```

Options:

- `--no-color` — plain text output
- `--no-progress` — skip intro animation
- `--title "Line 3 hold review"` — override report title

Exit codes: `0` pass, `1` fail, `2` hold.

Requires **Python 3.10+**. Sample fixture: `samples/inspection.json`.

## License

MIT
