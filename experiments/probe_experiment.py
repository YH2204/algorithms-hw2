"""Compare chaining-table probe counts with the uniform-hashing estimates."""

import csv
import math
import random
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hash_table import ChainingHashTable


BUCKET_COUNT = 4093
LOAD_FACTORS = tuple(step / 4 for step in range(1, 17))
MISS_TRIALS = 4096
RANDOM_SEED = 2026
URL_ALPHABET = string.ascii_lowercase + string.digits
OUTPUT_DIRECTORY = Path(__file__).resolve().parent
CSV_PATH = OUTPUT_DIRECTORY / "results.csv"
SVG_PATH = OUTPUT_DIRECTORY / "results.svg"


def _random_url(generator):
    host = "".join(generator.choices(URL_ALPHABET, k=12))
    path = "".join(generator.choices(URL_ALPHABET, k=24))
    return f"https://{host}.example/{path}"


def _average_success_cost(table, urls):
    total_cost = 0
    for url in urls:
        found, _, cost = table.find(url)
        if not found:
            raise RuntimeError(f"Inserted URL was not found: {url}")
        total_cost += cost
    return total_cost / len(urls)


def _average_failure_cost(table, generator):
    total_cost = 0
    for _ in range(MISS_TRIALS):
        url = _random_url(generator)
        found, _, cost = table.find(url)
        if found:
            raise RuntimeError("Generated unsuccessful-search URL already exists")
        total_cost += cost
    return total_cost / MISS_TRIALS


def measure():
    generator = random.Random(RANDOM_SEED)
    rows = []

    for load_factor in LOAD_FACTORS:
        table = ChainingHashTable(max_load=None)
        table.buckets = [None] * BUCKET_COUNT
        entry_count = round(load_factor * BUCKET_COUNT)
        urls = []

        while len(urls) < entry_count:
            url = _random_url(generator)
            if url not in table:
                table.put(url, len(urls))
                urls.append(url)

        actual_load = len(table) / BUCKET_COUNT
        rows.append(
            {
                "load_factor": actual_load,
                "entries": len(table),
                "success_measured": _average_success_cost(table, urls),
                "success_theory": 1 + actual_load / 2,
                "failure_measured": _average_failure_cost(table, generator),
                "failure_theory": actual_load,
            }
        )
    return rows


def _write_csv(rows):
    fieldnames = (
        "load_factor",
        "entries",
        "success_measured",
        "success_theory",
        "failure_measured",
        "failure_theory",
    )
    with CSV_PATH.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (
                        f"{value:.6f}"
                        if isinstance(value, float)
                        else value
                    )
                    for key, value in row.items()
                }
            )


def _write_svg(rows):
    width, height = 960, 560
    left, right, top, bottom = 82, 30, 55, 76
    plot_width = width - left - right
    plot_height = height - top - bottom
    y_max = max(
        5,
        math.ceil(
            max(
                row[key]
                for row in rows
                for key in ("success_measured", "failure_measured")
            )
        ),
    )

    def x_position(load_factor):
        return left + load_factor / 4 * plot_width

    def y_position(value):
        return top + (y_max - value) / y_max * plot_height

    series = (
        ("success_measured", "Successful: measured", "#1769aa", ""),
        ("success_theory", "Successful: theory", "#1769aa", "7 5"),
        ("failure_measured", "Unsuccessful: measured", "#d1495b", ""),
        ("failure_theory", "Unsuccessful: theory", "#d1495b", "7 5"),
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Chaining hash table probe counts</title>",
        "<desc>Measured average node comparisons and theoretical estimates "
        "by load factor.</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="480" y="28" text-anchor="middle" font-family="sans-serif" '
        'font-size="20">Chaining: measured vs theoretical probe counts</text>',
    ]

    for tick in range(y_max + 1):
        y = y_position(tick)
        parts.extend(
            (
                f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" '
                f'y2="{y:.2f}" stroke="#dddddd"/>',
                f'<text x="{left-12}" y="{y+5:.2f}" text-anchor="end" '
                f'font-family="sans-serif" font-size="12">{tick}</text>',
            )
        )

    for tick in range(9):
        value = tick / 2
        x = x_position(value)
        parts.extend(
            (
                f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
                f'y2="{height-bottom}" stroke="#eeeeee"/>',
                f'<text x="{x:.2f}" y="{height-bottom+22}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="12">{value:g}</text>',
            )
        )

    parts.extend(
        (
            f'<line x1="{left}" y1="{top}" x2="{left}" '
            f'y2="{height-bottom}" stroke="#333"/>',
            f'<line x1="{left}" y1="{height-bottom}" '
            f'x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
            f'<text x="{left + plot_width/2:.2f}" y="{height-18}" '
            'text-anchor="middle" font-family="sans-serif" font-size="14">'
            "Load factor (α)</text>",
            f'<text x="20" y="{top + plot_height/2:.2f}" '
            'transform="rotate(-90 20 '
            f'{top + plot_height/2:.2f})" text-anchor="middle" '
            'font-family="sans-serif" font-size="14">'
            "Average node comparisons</text>",
        )
    )

    for index, (key, label, color, dash) in enumerate(series):
        coordinates = " ".join(
            f"{x_position(row['load_factor']):.2f},"
            f"{y_position(row[key]):.2f}"
            for row in rows
        )
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(
            f'<polyline points="{coordinates}" fill="none" stroke="{color}" '
            f'stroke-width="2.5"{dash_attribute}/>'
        )
        legend_y = top + 18 + index * 22
        parts.extend(
            (
                f'<line x1="{left+18}" y1="{legend_y}" x2="{left+48}" '
                f'y2="{legend_y}" stroke="{color}" stroke-width="2.5"'
                f'{dash_attribute}/>',
                f'<text x="{left+55}" y="{legend_y+4}" '
                f'font-family="sans-serif" font-size="12">{label}</text>',
            )
        )

    parts.append("</svg>")
    SVG_PATH.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main():
    rows = measure()
    _write_csv(rows)
    _write_svg(rows)

    print(
        f"{'α':>6} {'n':>7} {'성공 평균':>12} {'성공 이론':>12} "
        f"{'실패 평균':>12} {'실패 이론':>12}"
    )
    for row in rows:
        print(
            f"{row['load_factor']:6.2f} {row['entries']:7d} "
            f"{row['success_measured']:12.4f} "
            f"{row['success_theory']:12.4f} "
            f"{row['failure_measured']:12.4f} "
            f"{row['failure_theory']:12.4f}"
        )
    print(f"\nCSV: {CSV_PATH}")
    print(f"SVG: {SVG_PATH}")


if __name__ == "__main__":
    main()
