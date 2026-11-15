"""Plot personal Naive figures and team comparisons from preserved measurements.

Usage:
    python code/plot_figures.py

Defaults are relative to this script's repository root. Custom paths:
    python code/plot_figures.py --csv /path/to/summary.csv \
        --naive-output-dir /path/to/naive --team-output-dir /path/to/team

The script reads existing measurements; it does not run an algorithm or write
to the source CSV. Requires matplotlib. Labels use the bundled DejaVu Sans font.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


SOURCE_SHA256 = "a43aa645633a0f686a1e68c259a87a0e9ab8901b1006ee3abe1521b5019920d9"
FIGSIZE = (10, 6)
DPI = 180
COLORS = {"random": "#225E9B", "ecoli": "#087E71"}
SOURCE_LABELS = {"random": "Random DNA", "ecoli": "E. coli DNA"}
ALGORITHMS = ("Naive", "KMP", "Boyer-Moore")
ALGORITHM_COLORS = {"Naive": "#536273", "KMP": "#087E8C", "Boyer-Moore": "#B84B2D"}
ALGORITHM_MARKERS = {"Naive": "o", "KMP": "s", "Boyer-Moore": "^"}


def configure_font():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.unicode_minus": False,
        "axes.labelcolor": "#333C46",
        "text.color": "#202B36",
        "xtick.color": "#465260",
        "ytick.color": "#465260",
        "savefig.facecolor": "white",
    })


def read_rows(csv_path):
    raw = csv_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("The CSV differs from the preserved November 4 summary.")
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 333
    assert Counter(row["algorithm"] for row in rows) == {algorithm: 111 for algorithm in ALGORITHMS}
    assert len({(row["case_id"], row["algorithm"]) for row in rows}) == 333
    assert all(row["correct"] == "True" and int(row["repeats"]) == 5 for row in rows)
    naive = [row for row in rows if row["algorithm"] == "Naive"]
    assert len(naive) == 111
    assert Counter(row["experiment"] for row in naive) == {"1": 30, "2": 54, "3": 27}
    assert all(row["correct"] == "True" and int(row["repeats"]) == 5 for row in naive)
    return rows


def aggregate(naive, experiment, dimension):
    output = {}
    for source in ("random", "ecoli"):
        selected = [r for r in naive if r["experiment"] == str(experiment) and r["source"] == source]
        points = []
        for value in sorted({int(r[dimension]) for r in selected}):
            group = [r for r in selected if int(r[dimension]) == value]
            assert len(group) == 3
            assert {r["pattern_id"] for r in group} == {"p01", "p02", "p03"}
            if experiment == 1:
                assert all(int(r["m"]) == 32 for r in group)
            else:
                assert all(int(r["n"]) == 1_000_000 for r in group)
            points.append((value, statistics.mean(float(r["mean_ms"]) for r in group)))
        output[source] = points
    return output


def frame(title, subtitle, footer):
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.105, right=0.965, bottom=0.24, top=0.78)
    fig.text(0.105, 0.93, title, ha="left", va="top", fontsize=18, fontweight="bold")
    fig.text(0.105, 0.865, subtitle, ha="left", va="top", fontsize=11, color="#566270")
    fig.text(0.105, 0.105, footer, ha="left", va="top", fontsize=9, color="#566270", linespacing=1.6)
    ax.spines[["top", "right"]].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#CAD1D8")
    ax.grid(axis="y", color="#E6EAF0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_ylabel("Mean runtime (ms)", labelpad=9)
    ax.tick_params(axis="both", length=3, color="#CAD1D8")
    return fig, ax


def save(fig, path, naive_only=True):
    text_labels = [obj.get_text() for obj in fig.findobj(matplotlib.text.Text)]
    if naive_only:
        assert all("KMP" not in text and "Boyer" not in text for text in text_labels)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def plot_length(points, output_dir):
    fig, ax = frame(
        "Naive Search: Runtime vs. DNA Length",
        "Pattern length: 32 bases | Random and E. coli DNA",
        "Each point averages three pattern-level means; each pattern was measured five times.\n"
        "Measured Nov 4, 2026 | Timing includes preprocessing, search, and the complete result list.",
    )
    for source, marker, style in (("random", "o", "-"), ("ecoli", "s", "--")):
        values = points[source]
        x = [n / 1_000_000 for n, _ in values]
        y = [mean for _, mean in values]
        ax.plot(x, y, color=COLORS[source], marker=marker, linestyle=style,
                linewidth=2, markersize=5.5, label=SOURCE_LABELS[source])
        ax.annotate(f"{y[-1]:.3f} ms", (x[-1], y[-1]),
                    xytext=(-5, 13 if source == "random" else -31),
                    textcoords="offset points", ha="right", color=COLORS[source], fontsize=10)
    ax.set_xlabel("DNA length n (million bases)", labelpad=8)
    ax.set_xticks([0.1, 0.5, 1, 2, 4], ["0.1", "0.5", "1", "2", "4"])
    ax.set_xlim(-0.025, 4.2)
    ax.set_ylim(0, 215)
    ax.set_yticks([0, 50, 100, 150, 200])
    ax.legend(loc="upper left", frameon=False)
    save(fig, output_dir / "naive_dna_length.png")


def plot_pattern(points, output_dir):
    fig, ax = frame(
        "Naive Search: Runtime vs. Pattern Length",
        "DNA length: 1,000,000 bases | Pattern lengths: 4–1,000 bases",
        "Each point averages three pattern-level means; each pattern was measured five times.\n"
        "Measured Nov 4, 2026 | Logarithmic x-axis; the y-axis starts at zero.",
    )
    for source, marker, style in (("random", "o", "-"), ("ecoli", "s", "--")):
        values = points[source]
        x = [m for m, _ in values]
        y = [mean for _, mean in values]
        ax.plot(x, y, color=COLORS[source], marker=marker, linestyle=style,
                linewidth=2, markersize=5.5, label=SOURCE_LABELS[source])
    ax.set_xscale("log", base=2)
    lengths = [4, 8, 16, 32, 64, 128, 256, 512, 1000]
    ax.set_xticks(lengths, [str(m) for m in lengths])
    ax.set_xlim(3.5, 1150)
    ax.set_ylim(0, 60)
    ax.set_yticks([0, 10, 20, 30, 40, 50, 60])
    ax.set_xlabel("Pattern length m (bases, logarithmic scale)", labelpad=8)
    ax.legend(loc="lower left", frameon=False)
    observed = [y for values in points.values() for _, y in values]
    ax.text(0.98, 0.91, f"Observed means: {min(observed):.2f}–{max(observed):.2f} ms",
            transform=ax.transAxes, ha="right", va="top", fontsize=10, color="#465260")
    save(fig, output_dir / "naive_pattern_length.png")


def plot_repeats(naive, output_dir):
    selected = [r for r in naive if r["experiment"] == "3" and r["repeat_unit"] == "A"]
    assert len(selected) == 9 and all(int(r["m"]) == 32 for r in selected)
    fig, ax = frame(
        "Naive Search: Runtime on Repetitive DNA",
        "Repeated A | Pattern length: 32 bases | All overlapping matches returned",
        "A-only input: nine conditions. Each point is the mean of five timed runs.\n"
        "Measured Nov 4, 2026 | Timing includes preprocessing, search, and the complete result list.",
    )
    conditions = (
        ("start_mismatch", "First-character mismatch", "#596776", "^", "-.", 12),
        ("end_mismatch", "Last-character mismatch", "#225E9B", "o", "--", -32),
        ("many_matches", "Full match at every valid alignment", "#BB6B31", "s", "-", 12),
    )
    output = {}
    for condition, label, color, marker, style, offset in conditions:
        rows = sorted((r for r in selected if r["condition"] == condition), key=lambda r: int(r["n"]))
        assert [int(r["n"]) for r in rows] == [10_000, 20_000, 70_000]
        x = [int(r["n"]) for r in rows]
        y = [float(r["mean_ms"]) for r in rows]
        output[condition] = list(zip(x, y))
        ax.plot(x, y, label=label, color=color, marker=marker, linestyle=style,
                linewidth=2, markersize=5.5)
        ax.annotate(f"{y[-1]:.3f} ms", (x[-1], y[-1]), xytext=(-4, offset),
                    textcoords="offset points", ha="right", fontsize=10, color=color)
    ax.set_xlabel("DNA length n (bases)", labelpad=8)
    ax.set_xticks([10_000, 20_000, 70_000])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_xlim(6_000, 74_000)
    ax.set_ylim(0, 73)
    ax.set_yticks([0, 10, 20, 30, 40, 50, 60, 70])
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    save(fig, output_dir / "naive_repeat_conditions.png")
    return output


def group_mean(rows, field, expected_count, **selection):
    selected = [row for row in rows if all(str(row.get(k)) == str(v) for k, v in selection.items())]
    assert len(selected) == expected_count, (selection, len(selected))
    if expected_count == 3:
        assert {row["pattern_id"] for row in selected} == {"p01", "p02", "p03"}
    return statistics.mean(float(row[field]) for row in selected)


def team_frame(title, subtitle, panel_count, footer, sharey=False):
    width = 12 if panel_count == 2 else 13.2
    fig, axes = plt.subplots(1, panel_count, figsize=(width, 6), dpi=DPI, sharey=sharey)
    fig.subplots_adjust(left=0.075, right=0.975, bottom=0.24, top=0.68, wspace=0.23)
    fig.text(0.075, 0.94, title, ha="left", va="top", fontsize=18, fontweight="bold")
    fig.text(0.075, 0.875, subtitle, ha="left", va="top", fontsize=11, color="#566270")
    fig.text(0.075, 0.105, footer, ha="left", va="top", fontsize=9, color="#566270", linespacing=1.6)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#CAD1D8")
        ax.grid(axis="y", color="#E6EAF0", linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(axis="both", length=3, color="#CAD1D8", labelsize=10)
    return fig, axes


def team_dual(rows, experiment, field, filename, ylabel, title, subtitle, footer, output_dir, scale=1):
    dimension = "n" if experiment == 1 else "m"
    xs = sorted({int(r[dimension]) for r in rows if r["experiment"] == str(experiment)})
    data = {
        source: {
            algorithm: [group_mean(rows, field, 3, experiment=experiment, source=source,
                                   algorithm=algorithm, **{dimension: x}) / scale for x in xs]
            for algorithm in ALGORITHMS
        }
        for source in ("random", "ecoli")
    }
    y_max = max(y for source in data.values() for series in source.values() for y in series)
    fig, axes = team_frame(title, subtitle, 2, footer, sharey=True)
    for ax, source in zip(axes, ("random", "ecoli")):
        for algorithm in ALGORITHMS:
            ax.plot(xs, data[source][algorithm], label=algorithm, color=ALGORITHM_COLORS[algorithm],
                    marker=ALGORITHM_MARKERS[algorithm], markersize=5, linewidth=1.9)
        ax.set_title(SOURCE_LABELS[source], fontsize=12, pad=12, fontweight="bold")
        ax.set_ylim(0, y_max * 1.12)
        if dimension == "m":
            ax.set_xscale("log", base=2)
            ax.set_xticks(xs, [str(x) for x in xs])
            ax.tick_params(axis="x", labelsize=9)
            ax.set_xlabel("Pattern length m (bases, log scale)", labelpad=8)
        else:
            ax.set_xticks(xs, [f"{x / 1_000_000:g}" for x in xs])
            ax.set_xlabel("DNA length n (million bases)", labelpad=8)
    axes[0].set_ylabel(ylabel, labelpad=10)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.53, 0.825),
               ncol=3, frameon=False, fontsize=10)
    save(fig, output_dir / filename, naive_only=False)
    return {"x": xs, "values": data, "unit_scale": scale}


def team_repeats(rows, output_dir):
    conditions = (
        ("end_mismatch", "Last-character mismatch"),
        ("start_mismatch", "First-character mismatch"),
        ("many_matches", "Repeated full matches"),
    )
    xs = [10_000, 20_000, 70_000]
    fig, axes = team_frame(
        "Repetitive DNA: Runtime by Match Condition",
        "Repeated A | Pattern length: 32 bases | All overlapping matches returned",
        3,
        "Each point is the mean of five timed runs. Only the nine core A-repeat conditions are shown.\n"
        "Measured Nov 4, 2026 | Panel y-axis ranges differ; all start at zero.",
    )
    data = {}
    for ax, (condition, title) in zip(axes, conditions):
        data[condition] = {}
        for algorithm in ALGORITHMS:
            ys = [group_mean(rows, "mean_ms", 1, experiment=3, repeat_unit="A", condition=condition,
                             algorithm=algorithm, n=n) for n in xs]
            data[condition][algorithm] = ys
            ax.plot(xs, ys, color=ALGORITHM_COLORS[algorithm], label=algorithm,
                    marker=ALGORITHM_MARKERS[algorithm], linewidth=1.9, markersize=5)
        ax.set_title(title, fontsize=11, pad=12, fontweight="bold")
        ax.set_xlabel("DNA length n (thousand bases)", labelpad=8, fontsize=10)
        ax.set_xticks(xs, ["10", "20", "70"])
        ax.set_ylabel("Mean runtime (ms)", labelpad=8, fontsize=10)
        ymax = max(y for ys in data[condition].values() for y in ys)
        ax.set_ylim(0, ymax * 1.12)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.53, 0.825),
               ncol=3, frameon=False, fontsize=10)
    save(fig, output_dir / "experiment3_time.png", naive_only=False)
    return data


def plot_team(rows, output_dir):
    common = "Each point averages three pattern-level means; each pattern was measured five times.\nMeasured Nov 4, 2026."
    results = {}
    results["experiment1_time"] = team_dual(
        rows, 1, "mean_ms", "experiment1_time.png", "Mean runtime (ms)",
        "DNA Length and Runtime", "Pattern length: 32 bases | Timing includes preprocessing, search, and the complete result list.",
        common, output_dir)
    results["experiment2_time"] = team_dual(
        rows, 2, "mean_ms", "experiment2_time.png", "Mean runtime (ms)",
        "Pattern Length and Runtime", "DNA length: 1,000,000 bases | All overlapping matches returned",
        common, output_dir)
    results["experiment2_comparisons"] = team_dual(
        rows, 2, "search_comparisons", "experiment2_comparisons.png", "Search comparisons (millions)",
        "Pattern Length and Search Comparisons", "DNA length: 1,000,000 bases | Search-stage character comparisons only",
        "Each point averages three pattern conditions. Comparison counting was separate from timing.\n"
        "Measured Nov 4, 2026 | Preprocessing comparisons are excluded from this figure.", output_dir, scale=1_000_000)
    results["experiment2_memory"] = team_dual(
        rows, 2, "peak_python_bytes", "experiment2_memory.png", "Peak traced allocation (KiB)",
        "Pattern Length and Peak Traced Allocation", "DNA length: 1,000,000 bases | New Python allocations measured with tracemalloc",
        "Each point averages three pattern conditions; memory was sampled once per condition, separately from timing.\n"
        "Measured Nov 4, 2026 | Includes output lists; excludes preloaded input strings. This is not process RSS.", output_dir, scale=1024)
    results["experiment3_time"] = team_repeats(rows, output_dir)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    repo_root = Path(__file__).resolve().parent.parent
    parser.add_argument("--csv", type=Path, default=repo_root / "results/20261104/summary.csv")
    parser.add_argument("--naive-output-dir", type=Path, default=repo_root / "figures/naive")
    parser.add_argument("--team-output-dir", type=Path, default=repo_root / "figures/team")
    args = parser.parse_args()
    configure_font()
    rows = read_rows(args.csv)
    naive = [row for row in rows if row["algorithm"] == "Naive"]
    args.naive_output_dir.mkdir(parents=True, exist_ok=True)
    args.team_output_dir.mkdir(parents=True, exist_ok=True)
    length = aggregate(naive, 1, "n")
    pattern = aggregate(naive, 2, "m")
    plot_length(length, args.naive_output_dir)
    plot_pattern(pattern, args.naive_output_dir)
    repeat = plot_repeats(naive, args.naive_output_dir)
    team = plot_team(rows, args.team_output_dir)
    assert hashlib.sha256(args.csv.read_bytes()).hexdigest() == SOURCE_SHA256
    print(json.dumps({
        "source_sha256": SOURCE_SHA256,
        "algorithm": "Naive",
        "dimensions_px": [int(FIGSIZE[0] * DPI), int(FIGSIZE[1] * DPI)],
        "experiment1": length,
        "experiment2": pattern,
        "experiment3_A_only": repeat,
        "team_charts": team,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
