"""Regenerate white-background SVG/PNG research charts using only the standard library."""

from __future__ import annotations

import math
import struct
import sys
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cross_sectional.engine import analyze, load_rows  # noqa: E402

WIDTH, HEIGHT = 1200, 675
NAVY = "#17324d"
BLUE = "#3478b8"
TEAL = "#25a18e"
ORANGE = "#e58b32"
PALE = "#e9eff5"
GRID = "#dce3ea"
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    " ": ("00000",) * 7,
}


class Scene:
    def __init__(self) -> None:
        self.pixels = bytearray([255]) * (WIDTH * HEIGHT * 3)
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
            '<rect width="100%" height="100%" fill="white"/>',
        ]

    @staticmethod
    def rgb(color: str) -> tuple[int, int, int]:
        return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))

    def pixel(self, x: int, y: int, color: str) -> None:
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            offset = (y * WIDTH + x) * 3
            self.pixels[offset:offset + 3] = bytes(self.rgb(color))

    def rect(self, x: int, y: int, width: int, height: int, color: str) -> None:
        self.svg.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{color}"/>')
        red, green, blue = self.rgb(color)
        for row in range(max(0, y), min(HEIGHT, y + height)):
            start = (row * WIDTH + max(0, x)) * 3
            stop = (row * WIDTH + min(WIDTH, x + width)) * 3
            self.pixels[start:stop] = bytes((red, green, blue)) * max(0, min(WIDTH, x + width) - max(0, x))

    def line(self, x1: int, y1: int, x2: int, y2: int, color: str, size: int = 2) -> None:
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{size}"/>')
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        sx, sy = (1 if x1 < x2 else -1), (1 if y1 < y2 else -1)
        error = dx - dy
        while True:
            radius = size // 2
            for oy in range(-radius, radius + 1):
                for ox in range(-radius, radius + 1):
                    self.pixel(x1 + ox, y1 + oy, color)
            if x1 == x2 and y1 == y2:
                break
            doubled = 2 * error
            if doubled > -dy:
                error -= dy
                x1 += sx
            if doubled < dx:
                error += dx
                y1 += sy

    def circle(self, x: int, y: int, radius: int, color: str) -> None:
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color}"/>')
        for oy in range(-radius, radius + 1):
            for ox in range(-radius, radius + 1):
                if ox * ox + oy * oy <= radius * radius:
                    self.pixel(x + ox, y + oy, color)

    def text(self, x: int, y: int, value: str, color: str = NAVY, scale: int = 2) -> None:
        value = value.upper()
        self.svg.append(
            f'<text x="{x}" y="{y + 7 * scale}" fill="{color}" font-family="Arial,sans-serif" '
            f'font-size="{7 * scale}px" font-weight="600">{escape(value)}</text>'
        )
        cursor = x
        for character in value:
            glyph = FONT.get(character, FONT[" "])
            for row, pattern in enumerate(glyph):
                for column, bit in enumerate(pattern):
                    if bit == "1":
                        for oy in range(scale):
                            for ox in range(scale):
                                self.pixel(cursor + column * scale + ox, y + row * scale + oy, color)
            cursor += 6 * scale

    def save(self, name: str) -> None:
        target = ROOT / "reports"
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{name}.svg").write_text("\n".join(self.svg + ["</svg>"]), encoding="utf-8")
        raw = b"".join(b"\x00" + bytes(self.pixels[row * WIDTH * 3:(row + 1) * WIDTH * 3]) for row in range(HEIGHT))

        def chunk(kind: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">2I5B", WIDTH, HEIGHT, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(raw, 9))
        png += chunk(b"IEND", b"")
        (target / f"{name}.png").write_bytes(png)


def header(scene: Scene, title: str, subtitle: str) -> None:
    scene.text(55, 35, title, NAVY, 4)
    scene.text(58, 86, subtitle, BLUE, 2)
    scene.line(55, 125, 1140, 125, GRID, 2)


def main() -> None:
    result = analyze(load_rows(ROOT / "data" / "cross_sectional.csv"))
    means = [float(value) for value in result["mean_forward_return_by_quantile"]]
    overview = Scene()
    header(overview, "MODEL OVERVIEW", "MEAN FORWARD RETURN BY SCORE QUANTILE")
    overview.text(
        58,
        140,
        f"IC {result['mean_rank_ic']:.3f} ICIR {result['rank_ic_information_ratio']:.3f} "
        f"POS IC {result['positive_rank_ic_date_fraction']:.2f} "
        f"TOP BOT {result['mean_top_minus_bottom_return']:.3%}",
        NAVY,
        2,
    )
    left, right, top, bottom = 130, 1090, 190, 555
    low = min(0.0, min(means)) - 0.004
    high = max(0.0, max(means)) + 0.004
    ymap = lambda value: int(bottom - (value - low) / (high - low) * (bottom - top))
    for step in range(5):
        value = low + (high - low) * step / 4
        y = ymap(value)
        overview.line(left, y, right, y, GRID, 1)
        overview.text(58, y - 8, f"{value * 100:.1f}%", "#617487", 1)
    baseline = ymap(0.0)
    overview.line(left, baseline, right, baseline, NAVY, 2)
    band = (right - left) / len(means)
    for index, value in enumerate(means):
        x = int(left + index * band + band * 0.24)
        width = int(band * 0.52)
        y = ymap(value)
        overview.rect(x, min(y, baseline), width, max(2, abs(baseline - y)), BLUE if index < len(means) - 1 else TEAL)
        overview.text(x + width // 2 - 12, bottom + 18, f"Q{index + 1}", NAVY, 2)
    overview.text(430, 615, "LOW SCORE TO HIGH SCORE", NAVY, 2)
    overview.save("overview")

    workflow = Scene()
    header(workflow, "RANK IC WORKFLOW", "SPEARMAN SCORE-RETURN CORRELATION BY DATE")
    workflow.text(
        58,
        140,
        f"MEAN IC {result['mean_rank_ic']:.3f} ICIR {result['rank_ic_information_ratio']:.3f} "
        f"POSITIVE DATES {result['positive_rank_ic_date_fraction']:.2f}",
        NAVY,
        2,
    )
    dates = [str(item["date"]) for item in result["date_results"]]
    ics = [float(item["rank_ic"]) if item["rank_ic"] is not None else 0.0 for item in result["date_results"]]
    left, right, top, bottom = 130, 1090, 190, 550
    low, high = -1.0, 1.0
    ymap = lambda value: int(bottom - (value - low) / (high - low) * (bottom - top))
    for step in range(5):
        value = low + (high - low) * step / 4
        y = ymap(value)
        workflow.line(left, y, right, y, GRID, 1)
        workflow.text(62, y - 7, f"{value:.1f}", "#617487", 1)
    workflow.line(left, ymap(0), right, ymap(0), NAVY, 2)
    points = []
    for index, (date, value) in enumerate(zip(dates, ics)):
        x = int(left + index * (right - left) / max(1, len(ics) - 1))
        y = ymap(value)
        points.append((x, y))
        workflow.text(x - 17, bottom + 18, date[-5:], "#617487", 1)
    for first, second in zip(points, points[1:]):
        workflow.line(*first, *second, TEAL, 4)
    for x, y in points:
        workflow.circle(x, y, 7, ORANGE)
    workflow.text(475, 615, "DATE ORDER", NAVY, 2)
    workflow.save("workflow")


if __name__ == "__main__":
    main()
