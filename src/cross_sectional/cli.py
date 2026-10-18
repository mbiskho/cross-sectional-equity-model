"""Command-line interface for the synthetic cross-sectional study."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import analyze, load_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate transparent synthetic cross-sectional signals.")
    parser.add_argument("--data", default="data/cross_sectional.csv", help="CSV input path")
    parser.add_argument("--quantiles", type=int, default=5, help="number of score groups (minimum 2)")
    parser.add_argument(
        "--output",
        default="data/metrics.json",
        help="JSON summary output path (default: data/metrics.json)",
    )
    args = parser.parse_args()
    try:
        result = analyze(load_rows(args.data), args.quantiles)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, indent=2, sort_keys=True)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0
