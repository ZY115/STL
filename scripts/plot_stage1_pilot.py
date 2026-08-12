#!/usr/bin/env python3
"""Create reproducible figures for the completed Stage I pilot analysis."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from safety_stl.pilot_runner import CONDITION_ORDER, load_json_mapping, sha256_file


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = REPOSITORY_ROOT / "results" / "stage1_pilot"
DEFAULT_ANALYSIS = DEFAULT_RESULTS / "analysis"
TRAINING_SEEDS = (1101, 2202, 3303, 4404, 5505)
LABELS = {
    "task_only": "Task only",
    "native_cost": "Native cost",
    "gold_stl_cost": "Gold STL cost",
}
COLORS = {
    "task_only": "#4C78A8",
    "native_cost": "#F58518",
    "gold_stl_cost": "#54A24B",
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--analysis-dir", type=Path, default=DEFAULT_ANALYSIS)
    return parser.parse_args(argv)


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_progress(path: Path) -> List[Dict[str, float]]:
    return [
        {key: float(value) for key, value in row.items()}
        for row in read_csv(path)
    ]


def load_progress_matrix(
    results_dir: Path,
) -> Tuple[Dict[str, Dict[int, List[Dict[str, float]]]], Dict[str, str]]:
    curves: Dict[str, Dict[int, List[Dict[str, float]]]] = {
        condition: {} for condition in CONDITION_ORDER
    }
    sources: Dict[str, str] = {}
    for condition in CONDITION_ORDER:
        for seed in TRAINING_SEEDS:
            manifest_path = results_dir / "jobs" / condition / f"seed-{seed}" / "manifest.json"
            manifest = load_json_mapping(manifest_path)
            if manifest.get("status") != "success":
                raise ValueError(f"pilot job is not successful: {manifest_path}")
            progress_record = manifest["progress"]
            progress_path = Path(str(progress_record["path"]))
            actual_hash = sha256_file(progress_path)
            if actual_hash != progress_record["sha256"]:
                raise ValueError(f"progress hash mismatch: {progress_path}")
            rows = read_progress(progress_path)
            if len(rows) != 100 or rows[-1]["TotalEnvSteps"] != 1_000_000:
                raise ValueError(f"unexpected progress extent: {progress_path}")
            curves[condition][seed] = rows
            sources[str(progress_path)] = actual_hash
    return curves, sources


def interval_error(
    point: float,
    interval: Mapping[str, Any],
    *,
    scale: float = 1.0,
) -> np.ndarray:
    lower = float(interval["lower"])
    upper = float(interval["upper"])
    return np.asarray([[(point - lower) * scale], [(upper - point) * scale]])


def save_figure(figure: plt.Figure, output_base: Path) -> List[Path]:
    output_base.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_base.with_suffix(".png")
    svg_path = output_base.with_suffix(".svg")
    figure.savefig(
        png_path,
        dpi=200,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Software": f"Matplotlib {matplotlib.__version__}"},
    )
    figure.savefig(
        svg_path,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Date": None, "Creator": f"Matplotlib {matplotlib.__version__}"},
    )
    plt.close(figure)
    return [png_path, svg_path]


def style_axes(axis: plt.Axes) -> None:
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.grid(axis="y", alpha=0.22, linewidth=0.8)


def plot_evaluation_overview(analysis: Mapping[str, Any], output_dir: Path) -> List[Path]:
    panels = (
        ("missed_obligation_rate_per_trigger", "Missed obligations / trigger", 100.0, "%"),
        ("triggers_per_episode", "Warning triggers / episode", 1.0, "events"),
        ("goal_success_rate", "Goal success", 100.0, "%"),
        ("episode_return", "Episode return", 1.0, "return"),
    )
    figure, axes = plt.subplots(2, 2, figsize=(11.5, 8.0))
    for axis, (metric, title, scale, unit) in zip(axes.flat, panels):
        for x, condition in enumerate(CONDITION_ORDER):
            point = float(analysis["pooled_condition_results"][condition][metric])
            interval = analysis["condition_confidence_intervals"][condition][metric]
            axis.errorbar(
                x,
                point * scale,
                yerr=interval_error(point, interval, scale=scale),
                fmt="o",
                color=COLORS[condition],
                markersize=8,
                capsize=5,
                linewidth=2,
            )
            axis.annotate(
                f"{point * scale:.1f}" if scale == 100.0 else f"{point:.2f}",
                (x, point * scale),
                xytext=(0, 9),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )
        axis.set_xticks(range(len(CONDITION_ORDER)), [LABELS[c] for c in CONDITION_ORDER])
        axis.set_title(title, fontweight="bold")
        axis.set_ylabel(unit)
        if metric == "goal_success_rate":
            axis.set_ylim(0.0, 105.0)
        style_axes(axis)
    figure.suptitle(
        "Stage I final-checkpoint evaluation\nPoint estimate and 95% paired hierarchical bootstrap interval",
        fontsize=14,
        fontweight="bold",
    )
    figure.tight_layout()
    return save_figure(figure, output_dir / "evaluation_overview")


def plot_primary_comparison(
    analysis: Mapping[str, Any],
    per_seed_rows: Sequence[Mapping[str, str]],
    bootstrap_rows: Sequence[Mapping[str, str]],
    output_dir: Path,
) -> List[Path]:
    per_seed = {
        (row["condition"], int(row["training_seed"])): float(
            row["missed_obligation_rate_per_trigger"],
        )
        for row in per_seed_rows
    }
    absolute = np.asarray(
        [float(row["absolute_reduction_task_minus_gold"]) * 100.0 for row in bootstrap_rows],
    )
    relative = np.asarray(
        [float(row["relative_reduction"]) * 100.0 for row in bootstrap_rows if row["relative_reduction"]],
    )
    primary = analysis["primary_comparison"]
    intervals = analysis["primary_confidence_intervals"]

    figure, axes = plt.subplots(1, 3, figsize=(15.5, 4.7))
    paired_axis = axes[0]
    for seed in TRAINING_SEEDS:
        values = [
            per_seed[("task_only", seed)] * 100.0,
            per_seed[("gold_stl_cost", seed)] * 100.0,
        ]
        paired_axis.plot([0, 1], values, color="#8A8A8A", alpha=0.65, marker="o")
        paired_axis.annotate(str(seed), (1, values[1]), xytext=(5, 0), textcoords="offset points", fontsize=8)
    paired_axis.set_xticks([0, 1], [LABELS["task_only"], LABELS["gold_stl_cost"]])
    paired_axis.set_ylabel("Missed obligations / trigger (%)")
    paired_axis.set_title("Matched training seeds", fontweight="bold")
    style_axes(paired_axis)

    absolute_axis = axes[1]
    absolute_axis.hist(absolute, bins=45, color="#72B7B2", alpha=0.85, edgecolor="white")
    absolute_point = float(primary["absolute_reduction_task_minus_gold"]) * 100.0
    absolute_ci = intervals["absolute_reduction_task_minus_gold"]
    absolute_axis.axvline(0.0, color="black", linewidth=1.2)
    absolute_axis.axvline(absolute_point, color="#B279A2", linewidth=2.2, label="Point estimate")
    absolute_axis.axvspan(
        float(absolute_ci["lower"]) * 100.0,
        float(absolute_ci["upper"]) * 100.0,
        color="#B279A2",
        alpha=0.18,
        label="95% interval",
    )
    absolute_axis.set_xlabel("Task-only minus Gold STL (percentage points)")
    absolute_axis.set_ylabel("Bootstrap replicates")
    absolute_axis.set_title("Absolute safety reduction", fontweight="bold")
    absolute_axis.legend(frameon=False, fontsize=8)
    style_axes(absolute_axis)

    relative_axis = axes[2]
    relative_axis.hist(relative, bins=45, color="#59A14F", alpha=0.82, edgecolor="white")
    relative_point = float(primary["relative_reduction"]) * 100.0
    relative_ci = intervals["relative_reduction"]
    relative_axis.axvline(0.0, color="black", linewidth=1.2, label="No improvement")
    relative_axis.axvline(30.0, color="#E45756", linestyle="--", linewidth=2.0, label="Pilot target")
    relative_axis.axvline(relative_point, color="#B279A2", linewidth=2.2, label="Point estimate")
    relative_axis.axvspan(
        float(relative_ci["lower"]) * 100.0,
        float(relative_ci["upper"]) * 100.0,
        color="#B279A2",
        alpha=0.18,
        label="95% interval",
    )
    relative_axis.set_xlabel("Relative safety reduction (%)")
    relative_axis.set_ylabel("Bootstrap replicates")
    relative_axis.set_title("Relative safety reduction", fontweight="bold")
    relative_axis.legend(frameon=False, fontsize=8)
    style_axes(relative_axis)

    figure.suptitle(
        "Frozen primary comparison: positive reduction favors Gold STL cost",
        fontsize=14,
        fontweight="bold",
    )
    figure.tight_layout()
    return save_figure(figure, output_dir / "primary_comparison")


def metric_matrix(
    curves: Mapping[str, Mapping[int, Sequence[Mapping[str, float]]]],
    condition: str,
    metric: str,
) -> Tuple[np.ndarray, np.ndarray]:
    values = np.asarray(
        [[float(row[metric]) for row in curves[condition][seed]] for seed in TRAINING_SEEDS],
    )
    steps = np.asarray(
        [float(row["TotalEnvSteps"]) for row in curves[condition][TRAINING_SEEDS[0]]],
    )
    return steps, values


def plot_curve_panel(
    axis: plt.Axes,
    curves: Mapping[str, Mapping[int, Sequence[Mapping[str, float]]]],
    metric: str,
    title: str,
    ylabel: str,
) -> None:
    for condition in CONDITION_ORDER:
        steps, values = metric_matrix(curves, condition, metric)
        x = steps / 1_000_000.0
        for row in values:
            axis.plot(x, row, color=COLORS[condition], alpha=0.10, linewidth=0.8)
        axis.fill_between(
            x,
            values.min(axis=0),
            values.max(axis=0),
            color=COLORS[condition],
            alpha=0.10,
        )
        axis.plot(x, values.mean(axis=0), color=COLORS[condition], linewidth=2.0, label=LABELS[condition])
    axis.set_title(title, fontweight="bold")
    axis.set_xlabel("Training transitions (millions)")
    axis.set_ylabel(ylabel)
    style_axes(axis)


def plot_learning_curves(
    curves: Mapping[str, Mapping[int, Sequence[Mapping[str, float]]]],
    output_dir: Path,
) -> List[Path]:
    figure, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), sharex=True)
    plot_curve_panel(axes[0, 0], curves, "Metrics/EpRet", "Episode return", "return")
    plot_curve_panel(
        axes[0, 1],
        curves,
        "Metrics/STLCost",
        "Gold-STL missed events",
        "events / episode",
    )
    plot_curve_panel(
        axes[1, 0],
        curves,
        "Metrics/NativeCost",
        "Native hazard cost",
        "hazard-cost steps / episode",
    )
    plot_curve_panel(
        axes[1, 1],
        curves,
        "Metrics/LagrangeMultiplier",
        "Lagrange multiplier",
        "multiplier (cost-unit specific)",
    )
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    figure.suptitle(
        "Training diagnostics across five seeds\nBold line: seed mean; shading: seed min–max (descriptive, not a confidence interval)",
        fontsize=14,
        fontweight="bold",
    )
    figure.tight_layout(rect=(0, 0.06, 1, 0.94))
    return save_figure(figure, output_dir / "learning_curves")


def plot_constraint_diagnostics(
    curves: Mapping[str, Mapping[int, Sequence[Mapping[str, float]]]],
    output_dir: Path,
) -> List[Path]:
    specifications = (
        ("native_cost", 25.0, "hazard-cost steps / episode"),
        ("gold_stl_cost", 0.1, "missed events / episode"),
    )
    figure, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    for axis, (condition, limit, unit) in zip(axes, specifications):
        steps, selected = metric_matrix(curves, condition, "Metrics/SelectedAlgorithmCost")
        _, multiplier = metric_matrix(curves, condition, "Metrics/LagrangeMultiplier")
        x = steps / 1_000_000.0
        axis.fill_between(x, selected.min(axis=0), selected.max(axis=0), color=COLORS[condition], alpha=0.14)
        axis.plot(x, selected.mean(axis=0), color=COLORS[condition], linewidth=2.2, label="Selected cost mean")
        axis.axhline(limit, color="#E45756", linestyle="--", linewidth=2.0, label=f"Cost limit = {limit:g}")
        axis.set_xlabel("Training transitions (millions)")
        axis.set_ylabel(unit)
        axis.set_title(LABELS[condition], fontweight="bold")
        style_axes(axis)
        second = axis.twinx()
        second.plot(x, multiplier.mean(axis=0), color="#B279A2", linewidth=1.8, label="Multiplier mean")
        second.set_ylabel("Lagrange multiplier", color="#B279A2")
        second.spines["top"].set_visible(False)
        handles_a, labels_a = axis.get_legend_handles_labels()
        handles_b, labels_b = second.get_legend_handles_labels()
        axis.legend(handles_a + handles_b, labels_a + labels_b, frameon=False, fontsize=8, loc="best")
    figure.suptitle(
        "Constraint diagnostics (cost units differ across panels)",
        fontsize=14,
        fontweight="bold",
    )
    figure.tight_layout()
    return save_figure(figure, output_dir / "constraint_diagnostics")


def write_tail_summary(
    path: Path,
    curves: Mapping[str, Mapping[int, Sequence[Mapping[str, float]]]],
) -> None:
    metrics = (
        "Metrics/EpRet",
        "Metrics/NativeCost",
        "Metrics/STLCost",
        "Metrics/SelectedAlgorithmCost",
        "Metrics/LagrangeMultiplier",
    )
    rows: List[Dict[str, Any]] = []
    for condition in CONDITION_ORDER:
        for seed in TRAINING_SEEDS:
            records = curves[condition][seed]
            row: Dict[str, Any] = {"condition": condition, "training_seed": seed}
            for metric in metrics:
                key = metric.replace("Metrics/", "").lower()
                row[f"{key}_first_20_mean"] = float(np.mean([record[metric] for record in records[:20]]))
                row[f"{key}_last_20_mean"] = float(np.mean([record[metric] for record in records[-20:]]))
            rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_paired_episode_examples(path: Path, episode_rows: Sequence[Mapping[str, str]]) -> None:
    index = {
        (row["condition"], int(row["training_seed"]), int(row["evaluation_seed"])): row
        for row in episode_rows
    }
    candidates: List[Dict[str, Any]] = []
    for seed in TRAINING_SEEDS:
        for evaluation_seed in range(10_000, 10_100):
            task = index[("task_only", seed, evaluation_seed)]
            gold = index[("gold_stl_cost", seed, evaluation_seed)]
            task_missed = int(float(task["deadline_violation_count"])) + int(
                float(task["terminal_unresolved_count"]),
            )
            gold_missed = int(float(gold["deadline_violation_count"])) + int(
                float(gold["terminal_unresolved_count"]),
            )
            candidates.append(
                {
                    "training_seed": seed,
                    "evaluation_seed": evaluation_seed,
                    "gold_minus_task_missed_count": gold_missed - task_missed,
                    "task_trigger_count": int(float(task["trigger_count"])),
                    "task_missed_count": task_missed,
                    "gold_trigger_count": int(float(gold["trigger_count"])),
                    "gold_missed_count": gold_missed,
                    "task_episode_return": float(task["episode_return"]),
                    "gold_episode_return": float(gold["episode_return"]),
                    "task_goal_success": task["goal_success"],
                    "gold_goal_success": gold["goal_success"],
                },
            )
    gold_worse = sorted(
        candidates,
        key=lambda row: (
            -int(row["gold_minus_task_missed_count"]),
            int(row["training_seed"]),
            int(row["evaluation_seed"]),
        ),
    )[:5]
    gold_better = sorted(
        candidates,
        key=lambda row: (
            int(row["gold_minus_task_missed_count"]),
            int(row["training_seed"]),
            int(row["evaluation_seed"]),
        ),
    )[:5]
    rows = [
        {"selection": "largest_gold_minus_task_missed", **row} for row in gold_worse
    ] + [{"selection": "largest_task_minus_gold_missed", **row} for row in gold_better]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    results_dir = args.results_dir.resolve()
    analysis_dir = args.analysis_dir.resolve()
    figures_dir = analysis_dir / "figures"
    analysis_path = analysis_dir / "analysis.json"
    per_seed_path = analysis_dir / "per_training_seed.csv"
    bootstrap_path = analysis_dir / "bootstrap_primary.csv"
    episodes_path = analysis_dir / "episode_records.csv"
    analysis = load_json_mapping(analysis_path)
    per_seed_rows = read_csv(per_seed_path)
    bootstrap_rows = read_csv(bootstrap_path)
    episode_rows = read_csv(episodes_path)
    if len(bootstrap_rows) != 10_000:
        raise ValueError("the frozen primary bootstrap must contain 10,000 replicates")

    curves, progress_sources = load_progress_matrix(results_dir)
    matplotlib.rcParams.update(
        {
            "font.size": 10,
            "axes.titlepad": 9,
            "figure.dpi": 120,
            "svg.hashsalt": "stage1-pilot-v1",
        },
    )
    created: List[Path] = []
    created.extend(plot_evaluation_overview(analysis, figures_dir))
    created.extend(plot_primary_comparison(analysis, per_seed_rows, bootstrap_rows, figures_dir))
    created.extend(plot_learning_curves(curves, figures_dir))
    created.extend(plot_constraint_diagnostics(curves, figures_dir))
    tail_path = analysis_dir / "learning_curve_tail_windows.csv"
    write_tail_summary(tail_path, curves)
    created.append(tail_path)
    examples_path = analysis_dir / "paired_episode_examples.csv"
    write_paired_episode_examples(examples_path, episode_rows)
    created.append(examples_path)

    source_paths = (
        analysis_path,
        per_seed_path,
        bootstrap_path,
        episodes_path,
        Path(__file__).resolve(),
    )
    source_hashes = {str(path): sha256_file(path) for path in source_paths}
    source_hashes.update(progress_sources)
    manifest_path = figures_dir / "figures_manifest.json"
    manifest = {
        "schema_version": 1,
        "description": "Stage I pilot descriptive figures; inferential intervals come from the frozen D31 analysis.",
        "matplotlib_version": matplotlib.__version__,
        "numpy_version": np.__version__,
        "figure_files": {
            str(path): sha256_file(path) for path in created if path.suffix in {".png", ".svg"}
        },
        "analysis_companion_files": {
            str(path): sha256_file(path) for path in (tail_path, examples_path)
        },
        "source_files": source_hashes,
        "interpretation_guards": [
            "learning_curve_seed_ranges_are_descriptive_not_confidence_intervals",
            "cost_units_differ_between_native_and_gold_stl_conditions",
            "plots_do_not_change_the_frozen_statistical_protocol",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "figure_count": 4,
                "rendered_file_count": 8,
                "manifest": str(manifest_path),
                "tail_summary": str(tail_path),
                "paired_examples": str(examples_path),
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
