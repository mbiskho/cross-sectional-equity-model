"""Pure-standard-library cross-sectional scoring and evaluation."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable

SIGNALS = ("value", "momentum", "quality")
REQUIRED_COLUMNS = ("date", "security", *SIGNALS, "forward_return")


def load_rows(path: str | Path) -> list[dict[str, object]]:
    """Load and validate a CSV dataset."""
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(REQUIRED_COLUMNS).issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain columns: {', '.join(REQUIRED_COLUMNS)}")
        for line_number, raw in enumerate(reader, start=2):
            date = (raw.get("date") or "").strip()
            security = (raw.get("security") or "").strip()
            if not date or not security:
                raise ValueError(f"line {line_number}: date and security must be non-empty")
            key = (date, security)
            if key in seen:
                raise ValueError(f"line {line_number}: duplicate date/security pair {key}")
            seen.add(key)
            row: dict[str, object] = {"date": date, "security": security}
            for column in (*SIGNALS, "forward_return"):
                try:
                    value = float(raw[column])  # type: ignore[arg-type]
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"line {line_number}: invalid {column}") from exc
                if not math.isfinite(value):
                    raise ValueError(f"line {line_number}: {column} must be finite")
                row[column] = value
            rows.append(row)
    if not rows:
        raise ValueError("CSV contains no observations")
    return rows


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = rank
        start = end
    return ranks


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    left_ss = sum(value * value for value in left_centered)
    right_ss = sum(value * value for value in right_centered)
    if left_ss == 0 or right_ss == 0:
        return None
    return sum(a * b for a, b in zip(left_centered, right_centered)) / math.sqrt(left_ss * right_ss)


def _sample_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def analyze(rows: Iterable[dict[str, object]], quantiles: int = 5) -> dict[str, object]:
    """Score each date, calculate quantile returns, and summarize rank IC."""
    if quantiles < 2:
        raise ValueError("quantiles must be at least 2")
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row["date"])].append(row)
    if not groups:
        raise ValueError("no observations to analyze")

    date_results: list[dict[str, object]] = []
    quantile_returns: dict[int, list[float]] = defaultdict(list)
    daily_spreads: list[float] = []
    for date in sorted(groups):
        members = sorted(groups[date], key=lambda row: str(row["security"]))
        scores = [0.0] * len(members)
        for signal in SIGNALS:
            values = [float(member[signal]) for member in members]
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            scale = math.sqrt(variance)
            zscores = [(value - mean) / scale if scale else 0.0 for value in values]
            scores = [score + zscore / len(SIGNALS) for score, zscore in zip(scores, zscores)]
        ordered = sorted(range(len(members)), key=lambda i: (scores[i], str(members[i]["security"])))
        buckets: list[list[int]] = [[] for _ in range(quantiles)]
        for position, index in enumerate(ordered):
            bucket = min(quantiles - 1, position * quantiles // len(ordered))
            buckets[bucket].append(index)
        means: list[float | None] = []
        for bucket_number, indices in enumerate(buckets, start=1):
            returns = [float(members[index]["forward_return"]) for index in indices]
            bucket_mean = sum(returns) / len(returns) if returns else None
            means.append(bucket_mean)
            if bucket_mean is not None:
                quantile_returns[bucket_number].append(bucket_mean)
        forward = [float(member["forward_return"]) for member in members]
        ic = _correlation(_average_ranks(scores), _average_ranks(forward))
        spread = (
            means[-1] - means[0]
            if means and means[0] is not None and means[-1] is not None
            else None
        )
        if spread is not None:
            daily_spreads.append(spread)
        date_results.append(
            {
                "date": date,
                "rank_ic": ic,
                "quantile_returns": means,
                "top_minus_bottom_return": spread,
            }
        )

    ic_values = [float(item["rank_ic"]) for item in date_results if item["rank_ic"] is not None]
    ic_mean = sum(ic_values) / len(ic_values) if ic_values else None
    ic_std = _sample_std(ic_values)
    average_returns = [
        sum(quantile_returns[index]) / len(quantile_returns[index]) if quantile_returns[index] else None
        for index in range(1, quantiles + 1)
    ]
    quantile_summary = {}
    for index in range(1, quantiles + 1):
        values = quantile_returns[index]
        quantile_summary[str(index)] = {
            "dates_with_observations": len(values),
            "mean_forward_return": sum(values) / len(values) if values else None,
            "sample_std_of_date_returns": _sample_std(values),
            "positive_date_fraction": (
                sum(value > 0 for value in values) / len(values) if values else None
            ),
        }
    return {
        "observations": sum(len(group) for group in groups.values()),
        "dates": len(groups),
        "quantiles": quantiles,
        "mean_forward_return_by_quantile": average_returns,
        "quantile_summary": quantile_summary,
        "mean_top_minus_bottom_return": (
            sum(daily_spreads) / len(daily_spreads) if daily_spreads else None
        ),
        "top_minus_bottom_sample_std": _sample_std(daily_spreads),
        "top_minus_bottom_positive_date_fraction": (
            sum(value > 0 for value in daily_spreads) / len(daily_spreads)
            if daily_spreads
            else None
        ),
        "mean_rank_ic": ic_mean,
        "rank_ic_sample_std": ic_std,
        "rank_ic_information_ratio": ic_mean / ic_std if ic_mean is not None and ic_std else None,
        "positive_rank_ic_date_fraction": (
            sum(value > 0 for value in ic_values) / len(ic_values) if ic_values else None
        ),
        "date_results": date_results,
    }
