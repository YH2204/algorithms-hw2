"""Compare chaining and linear-probing search costs with theory."""

import csv
import math
import random
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hash_table import ChainingHashTable, LinearProbingHashTable


TABLE_SIZE = 4093
LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
MISS_TRIALS = 4096
RANDOM_SEED = 2026
URL_ALPHABET = string.ascii_lowercase + string.digits
OUTPUT_DIRECTORY = Path(__file__).resolve().parent
CSV_PATH = OUTPUT_DIRECTORY / "compare_results.csv"
SVG_PATH = OUTPUT_DIRECTORY / "compare_results.svg"


def _random_url(generator):
    host = "".join(generator.choices(URL_ALPHABET, k=12))
    path = "".join(generator.choices(URL_ALPHABET, k=24))
    return f"https://{host}.example/{path}"


def _make_unique_urls(generator, count):
    seen = ChainingHashTable(max_load=None)
    seen.buckets = [None] * TABLE_SIZE
    urls = []
    while len(urls) < count:
        url = _random_url(generator)
        if url not in seen:
            seen.put(url, None)
            urls.append(url)
    return urls


def _make_miss_urls(generator, count, chaining, linear):
    urls = []
    while len(urls) < count:
        url = _random_url(generator)
        if url not in chaining and url not in linear:
            urls.append(url)
    return urls


def _average_cost(table, urls, should_find):
    total_cost = 0
    for url in urls:
        found, _, cost = table.find(url)
        if found != should_find:
            raise RuntimeError(f"Unexpected search result for {url}")
        total_cost += cost
    return total_cost / len(urls)


def measure():
    generator = random.Random(RANDOM_SEED)
    max_entries = round(LOAD_FACTORS[-1] * TABLE_SIZE)
    urls = _make_unique_urls(generator, max_entries)
    rows = []

    for target_load in LOAD_FACTORS:
        entry_count = round(target_load * TABLE_SIZE)
        chaining = ChainingHashTable(max_load=None)
        linear = LinearProbingHashTable(max_load=None)
        chaining.buckets = [None] * TABLE_SIZE
        linear.slots = [None] * TABLE_SIZE

        for index, url in enumerate(urls[:entry_count]):
            chaining.put(url, index)
            linear.put(url, index)

        if len(chaining) != len(linear):
            raise RuntimeError("The tables contain different numbers of keys")
        actual_load = len(chaining) / TABLE_SIZE
        misses = _make_miss_urls(
            generator,
            MISS_TRIALS,
            chaining,
            linear,
        )
        rows.append(
            {
                "target_load_factor": target_load,
                "load_factor": actual_load,
                "entries": entry_count,
                "chaining_success_measured": _average_cost(
                    chaining,
                    urls[:entry_count],
                    True,
                ),
                "chaining_success_theory": 1 + actual_load / 2,
                "chaining_failure_measured": _average_cost(
                    chaining,
                    misses,
                    False,
                ),
                "chaining_failure_theory": actual_load,
                "linear_success_measured": _average_cost(
                    linear,
                    urls[:entry_count],
                    True,
                ),
                "linear_success_theory": (
                    1 + 1 / (1 - actual_load)
                ) / 2,
                "linear_failure_measured": _average_cost(
                    linear,
                    misses,
                    False,
                ),
                "linear_failure_theory": (
                    1 + 1 / (1 - actual_load) ** 2
                ) / 2,
            }
        )
    return rows


def _write_csv(rows):
    fieldnames = tuple(rows[0].keys())
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
                    key: f"{value:.6f}" if isinstance(value, float) else value
                    for key, value in row.items()
                }
            )


def _write_svg(rows):
    width, height = 1400, 700
    left, right, top, bottom = 82, 35, 122, 76
    plot_width = width - left - right
    plot_height = height - top - bottom
    all_values = tuple(
        row[key]
        for row in rows
        for key in (
            "chaining_success_measured",
            "chaining_success_theory",
            "chaining_failure_measured",
            "chaining_failure_theory",
            "linear_success_measured",
            "linear_success_theory",
            "linear_failure_measured",
            "linear_failure_theory",
        )
    )
    y_min = min(all_values) / 1.5
    y_max = 10 ** math.ceil(math.log10(max(all_values)))

    def x_position(load_factor):
        return left + (
            (load_factor - LOAD_FACTORS[0])
            / (LOAD_FACTORS[-1] - LOAD_FACTORS[0])
            * plot_width
        )

    def y_position(value):
        log_min = math.log10(y_min)
        log_max = math.log10(y_max)
        return top + (log_max - math.log10(value)) / (log_max - log_min) * plot_height

    series = (
        ("chaining_success_measured", "Chaining success: measured", "#1769aa", ""),
        ("chaining_success_theory", "Chaining success: theory", "#1769aa", "7 5"),
        ("chaining_failure_measured", "Chaining failure: measured", "#d1495b", ""),
        ("chaining_failure_theory", "Chaining failure: theory", "#d1495b", "7 5"),
        ("linear_success_measured", "Linear success: measured", "#27864b", ""),
        ("linear_success_theory", "Linear success: theory", "#27864b", "7 5"),
        ("linear_failure_measured", "Linear failure: measured", "#8b5aa8", ""),
        ("linear_failure_theory", "Linear failure: theory", "#8b5aa8", "7 5"),
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Chaining and linear probing search cost comparison</title>",
        "<desc>Measured average comparisons and slot visits compared with "
        "theoretical estimates for successful and unsuccessful searches on "
        "a logarithmic vertical scale.</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="30" text-anchor="middle" '
        'font-family="sans-serif" font-size="21">'
        "Chaining vs linear probing: measured and theoretical costs</text>",
    ]

    for index, (key, label, color, dash) in enumerate(series):
        column = index % 4
        row_number = index // 4
        legend_x = left + column * 320
        legend_y = 63 + row_number * 22
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        parts.extend(
            (
                f'<line x1="{legend_x}" y1="{legend_y}" '
                f'x2="{legend_x+30}" y2="{legend_y}" stroke="{color}" '
                f'stroke-width="2.5"{dash_attribute}/>',
                f'<text x="{legend_x+38}" y="{legend_y+4}" '
                f'font-family="sans-serif" font-size="12">{label}</text>',
            )
        )

    y_ticks = []
    first_exponent = math.floor(math.log10(y_min)) - 1
    last_exponent = math.ceil(math.log10(y_max))
    for exponent in range(first_exponent, last_exponent + 1):
        for multiplier in (1, 2, 5):
            value = multiplier * 10**exponent
            if y_min <= value <= y_max:
                y_ticks.append(value)
    for value in y_ticks:
        y = y_position(value)
        parts.extend(
            (
                f'<line x1="{left}" y1="{y:.2f}" x2="{width-right}" '
                f'y2="{y:.2f}" stroke="#dddddd"/>',
                f'<text x="{left-12}" y="{y+5:.2f}" text-anchor="end" '
                f'font-family="sans-serif" font-size="12">{value:g}</text>',
            )
        )

    for target_load in LOAD_FACTORS:
        x = x_position(target_load)
        parts.extend(
            (
                f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
                f'y2="{height-bottom}" stroke="#eeeeee"/>',
                f'<text x="{x:.2f}" y="{height-bottom+22}" '
                'text-anchor="middle" font-family="sans-serif" '
                f'font-size="12">{target_load:.1f}</text>',
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
            "Average comparisons / slots visited (log scale)</text>",
        )
    )

    for key, _, color, dash in series:
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

    parts.append("</svg>")
    SVG_PATH.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main():
    rows = measure()
    _write_csv(rows)
    _write_svg(rows)

    print(
        f"{'α':>5} {'n':>6} {'Chain hit':>11} {'Chain miss':>11} "
        f"{'Linear hit':>11} {'Linear miss':>12}"
    )
    for row in rows:
        print(
            f"{row['load_factor']:5.2f} {row['entries']:6d} "
            f"{row['chaining_success_measured']:5.2f}/"
            f"{row['chaining_success_theory']:.2f} "
            f"{row['chaining_failure_measured']:5.2f}/"
            f"{row['chaining_failure_theory']:.2f} "
            f"{row['linear_success_measured']:5.2f}/"
            f"{row['linear_success_theory']:.2f} "
            f"{row['linear_failure_measured']:5.2f}/"
            f"{row['linear_failure_theory']:.2f}"
        )
    print(f"\nCSV: {CSV_PATH}")
    print(f"SVG: {SVG_PATH}")


if __name__ == "__main__":
    main()
