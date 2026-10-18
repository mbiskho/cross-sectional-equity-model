"""Regenerate the deterministic fictional cross-sectional example."""

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "data" / "cross_sectional.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("date", "security", "value", "momentum", "quality", "forward_return"))
        for period in range(4):
            date = f"2025-{period * 3 + 1:02d}-01"
            for index in range(12):
                value = (index - 5.5) / 4 + 0.18 * math.sin(index + period)
                momentum = (index - 5.5) / 4 + 0.16 * math.cos(index * 0.7 + period)
                quality = (index - 5.5) / 4 + 0.14 * math.sin(index * 0.4 - period)
                latent = (value + momentum + quality) / 3
                forward_return = 0.001 + 0.012 * latent + 0.003 * math.sin(index * 1.7 + period * 2.1)
                writer.writerow(
                    (
                        date,
                        f"SYN{index + 1:02d}",
                        f"{value:.6f}",
                        f"{momentum:.6f}",
                        f"{quality:.6f}",
                        f"{forward_return:.6f}",
                    )
                )


if __name__ == "__main__":
    main()
