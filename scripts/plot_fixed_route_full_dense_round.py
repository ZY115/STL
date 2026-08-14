#!/usr/bin/env python3
"""Analyze and plot the completed single-seed D47 fixed-route round."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/fixed_route_v1/full_dense_round"
REPORT = ROOT / "docs/fixed_route_v1_full_dense_result_report.md"
CONDITIONS = ["task_only", "native_safety", "stl_dense_safety"]
LABELS = {
    "task_only": "Task-only",
    "native_safety": "Native-safety",
    "stl_dense_safety": "STL-dense-safety",
}
COLORS = {
    "task_only": "#4c78a8",
    "native_safety": "#f58518",
    "stl_dense_safety": "#54a24b",
}


def _json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _rolling(values: Sequence[float], window: int = 5) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if len(array) < window:
        return array
    prefix = np.full(window - 1, np.nan)
    return np.concatenate((prefix, np.convolve(array, np.ones(window) / window, mode="valid")))


def _percentile(values: Sequence[float]) -> List[float]:
    finite = np.asarray([value for value in values if math.isfinite(value)], dtype=float)
    if not len(finite):
        return [float("nan"), float("nan")]
    return [float(value) for value in np.percentile(finite, [2.5, 97.5])]


def _missed(row: Mapping[str, str]) -> int:
    return int(row["deadline_violation_count"]) + int(row["terminal_unresolved_count"])


def _paired_bootstrap(
    task: Sequence[Mapping[str, str]],
    comparison: Sequence[Mapping[str, str]],
    *,
    replicates: int = 10_000,
    seed: int = 8102026,
) -> Dict[str, Any]:
    task_by_seed = {int(row["evaluation_seed"]): row for row in task}
    comparison_by_seed = {int(row["evaluation_seed"]): row for row in comparison}
    seeds = sorted(task_by_seed)
    if seeds != sorted(comparison_by_seed):
        raise ValueError("paired evaluation seed sets differ")
    rng = np.random.default_rng(seed)
    reductions: List[float] = []
    goal_differences: List[float] = []
    return_differences: List[float] = []
    native_differences: List[float] = []
    for _ in range(replicates):
        sampled = rng.choice(seeds, size=len(seeds), replace=True)
        task_rows = [task_by_seed[int(value)] for value in sampled]
        comparison_rows = [comparison_by_seed[int(value)] for value in sampled]
        task_triggers = sum(int(row["trigger_count"]) for row in task_rows)
        comparison_triggers = sum(int(row["trigger_count"]) for row in comparison_rows)
        task_rate = (
            float("nan") if not task_triggers
            else sum(_missed(row) for row in task_rows) / task_triggers
        )
        comparison_rate = (
            float("nan") if not comparison_triggers
            else sum(_missed(row) for row in comparison_rows) / comparison_triggers
        )
        reductions.append(task_rate - comparison_rate)
        goal_differences.append(
            float(np.mean([str(row["goal_success"]).lower() == "true" for row in comparison_rows]))
            - float(np.mean([str(row["goal_success"]).lower() == "true" for row in task_rows])),
        )
        return_differences.append(
            float(np.mean([float(row["episode_return"]) for row in comparison_rows]))
            - float(np.mean([float(row["episode_return"]) for row in task_rows])),
        )
        native_differences.append(
            float(np.mean([float(row["native_cost_total"]) for row in comparison_rows]))
            - float(np.mean([float(row["native_cost_total"]) for row in task_rows])),
        )
    return {
        "replicates": replicates,
        "paired_seed": seed,
        "missed_rate_absolute_reduction_ci95": _percentile(reductions),
        "goal_success_difference_ci95": _percentile(goal_differences),
        "return_difference_ci95": _percentile(return_differences),
        "native_cost_difference_ci95": _percentile(native_differences),
    }


def _aggregate(rows: Sequence[Mapping[str, str]]) -> Dict[str, float]:
    triggers = sum(int(row["trigger_count"]) for row in rows)
    missed = sum(_missed(row) for row in rows)
    return {
        "episodes": float(len(rows)),
        "return_mean": float(np.mean([float(row["episode_return"]) for row in rows])),
        "goal_events_mean": float(np.mean([float(row["goal_events"]) for row in rows])),
        "goal_success_rate": float(np.mean([str(row["goal_success"]).lower() == "true" for row in rows])),
        "native_cost_mean": float(np.mean([float(row["native_cost_total"]) for row in rows])),
        "minimum_distance_mean": float(np.mean([float(row["minimum_distance"]) for row in rows])),
        "triggers": float(triggers),
        "missed": float(missed),
        "missed_rate": float("nan") if not triggers else missed / triggers,
    }


def _tail_diagnostics(rows: Sequence[Mapping[str, str]]) -> Dict[str, float]:
    def mean_slice(field: str, start: int, stop: int) -> float:
        return float(np.mean([float(row[field]) for row in rows[start:stop]]))
    return {
        "return_previous_20_mean": mean_slice("Metrics/EpRet", -40, -20),
        "return_last_20_mean": mean_slice("Metrics/EpRet", -20, len(rows)),
        "selected_cost_previous_20_mean": mean_slice("Metrics/SelectedAlgorithmCost", -40, -20),
        "selected_cost_last_20_mean": mean_slice("Metrics/SelectedAlgorithmCost", -20, len(rows)),
        "lagrange_last": float(rows[-1]["Metrics/LagrangeMultiplier"]),
        "lagrange_last_20_mean": mean_slice("Metrics/LagrangeMultiplier", -20, len(rows)),
        "positive_cost_fraction_last_20_mean": mean_slice("Diagnostics/PositiveCostStepFraction", -20, len(rows)),
    }


def _write_combined_csv(path: Path, groups: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    rows = [{"condition": condition, **row} for condition, values in groups.items() for row in values]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    options = parser.parse_args()
    root, report = options.output_root.resolve(), options.report.resolve()
    validation = _json(root / "validated_training_completion.json")
    budgets = _json(root / "task_control_budgets.json")
    cell_by_condition = {cell["condition_id"]: cell for cell in validation["cells"]}
    progress = {condition: _csv(Path(cell_by_condition[condition]["progress"])) for condition in CONDITIONS}
    episodes = {
        condition: _csv(root / "evaluation" / condition / "stochastic" / "episodes.csv")
        for condition in CONDITIONS
    }
    evaluation_summaries = {
        condition: _json(root / "evaluation" / condition / "stochastic" / "summary.json")
        for condition in CONDITIONS
    }
    trajectory_rows: Dict[str, List[Dict[str, Any]]] = {}
    for condition in CONDITIONS:
        path = root / "evaluation" / condition / "deterministic" / "trajectories.jsonl"
        with path.open("r", encoding="utf-8") as handle:
            trajectory_rows[condition] = [json.loads(line) for line in handle]
    _write_combined_csv(root / "evaluation_episodes.csv", episodes)
    _write_combined_csv(root / "deterministic_trajectories.csv", trajectory_rows)

    aggregates = {condition: _aggregate(episodes[condition]) for condition in CONDITIONS}
    tail = {condition: _tail_diagnostics(progress[condition]) for condition in CONDITIONS}
    comparisons = {
        condition: _paired_bootstrap(episodes["task_only"], episodes[condition])
        for condition in ("native_safety", "stl_dense_safety")
    }
    task_rate = aggregates["task_only"]["missed_rate"]
    for condition, result in comparisons.items():
        comparison_rate = aggregates[condition]["missed_rate"]
        result["missed_rate_absolute_reduction"] = task_rate - comparison_rate
        result["missed_rate_relative_reduction"] = (
            None if task_rate == 0 else (task_rate - comparison_rate) / task_rate
        )
        result["baseline_zero_absolute_difference_rule_used"] = task_rate == 0
        result["goal_success_difference"] = (
            aggregates[condition]["goal_success_rate"]
            - aggregates["task_only"]["goal_success_rate"]
        )
        result["goal_success_noninferiority_margin"] = -0.10
        result["descriptive_noninferiority_pass"] = (
            result["goal_success_difference_ci95"][0] >= -0.10
        )

    analysis = {
        "schema_version": 1,
        "status": "single_seed_exploratory_analysis_complete",
        "training_seed": 12647,
        "evaluation_episode_count_per_condition": 100,
        "aggregates": aggregates,
        "paired_bootstrap": comparisons,
        "learning_curve_tail": tail,
        "agreement": {
            condition: {
                "all_online_oracle_agree": evaluation_summaries[condition]["aggregate"]["all_online_oracle_agree"],
                "rtamt_max_robustness_difference": evaluation_summaries[condition]["aggregate"]["rtamt_max_robustness_difference"],
            }
            for condition in CONDITIONS
        },
        "interpretation_guard": "one matched training seed; not confirmatory or a safety guarantee",
    }
    (root / "analysis_summary.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Figure 1: common-unit learning curves.
    figure, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True)
    fields = [
        ("Metrics/EpRet", "Episode return"),
        ("Metrics/STLCost", "Raw Gold missed-event cost / episode"),
        ("Metrics/NativeCost", "Native hazard cost / episode"),
        ("Metrics/STLDenseCost", "C1 dense surrogate mass / episode"),
    ]
    for axis, (field, title) in zip(axes.flat, fields):
        for condition in CONDITIONS:
            rows = progress[condition]
            axis.plot(
                [float(row["TotalEnvSteps"]) for row in rows],
                _rolling([float(row[field]) for row in rows]),
                label=LABELS[condition],
                color=COLORS[condition],
                linewidth=1.7,
            )
        axis.set_title(f"{title} (5-epoch moving mean)")
        axis.grid(alpha=0.2)
    for axis in axes[1]:
        axis.set_xlabel("Environment transitions")
    for axis in axes.flat:
        axis.legend(fontsize=8)
    figure.suptitle("Fixed-route v1: 1M-transition learning curves")
    figure.tight_layout()
    figure.savefig(root / "full_dense_learning_curves.png", dpi=190)
    plt.close(figure)

    # Figure 2: condition-specific constraint diagnostics (units kept separate).
    figure, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True)
    for condition, axis, budget_key, title in (
        ("native_safety", axes[0, 0], "native_cost_per_episode", "Native selected cost"),
        ("stl_dense_safety", axes[0, 1], "c1_surrogate_mass_per_episode", "STL-dense selected cost"),
    ):
        rows = progress[condition]
        axis.plot(
            [float(row["TotalEnvSteps"]) for row in rows],
            _rolling([float(row["Metrics/SelectedAlgorithmCost"]) for row in rows]),
            color=COLORS[condition],
        )
        limit = float(budgets["cost_limit"][budget_key])
        axis.axhline(limit, color="black", linestyle="--", linewidth=1, label=f"limit={limit:.3f}")
        axis.set_title(f"{title} (own units)")
        axis.legend(fontsize=8)
    for condition in ("native_safety", "stl_dense_safety"):
        rows = progress[condition]
        x = [float(row["TotalEnvSteps"]) for row in rows]
        axes[1, 0].plot(x, [float(row["Metrics/LagrangeMultiplier"]) for row in rows], label=LABELS[condition], color=COLORS[condition])
        axes[1, 1].plot(x, _rolling([float(row["Diagnostics/PositiveCostStepFraction"]) for row in rows]), label=LABELS[condition], color=COLORS[condition])
    axes[1, 0].set_title("Lagrange multiplier")
    axes[1, 1].set_title("Positive learner-cost step fraction (5-epoch mean)")
    for axis in axes.flat:
        axis.grid(alpha=0.2)
        axis.set_xlabel("Environment transitions")
        axis.legend(fontsize=8)
    figure.suptitle("Constraint learning diagnostics; Native and C1 units are not comparable")
    figure.tight_layout()
    figure.savefig(root / "full_dense_constraint_diagnostics.png", dpi=190)
    plt.close(figure)

    # Figure 3: fixed final-checkpoint outcomes.
    labels = [LABELS[condition] for condition in CONDITIONS]
    colors = [COLORS[condition] for condition in CONDITIONS]
    figure, axes = plt.subplots(2, 2, figsize=(12.5, 8.5))
    panels: List[Tuple[str, str, List[float]]] = [
        ("Gold missed recovery obligations", "missed / triggered", [aggregates[c]["missed_rate"] for c in CONDITIONS]),
        ("Goal success", "episode proportion", [aggregates[c]["goal_success_rate"] for c in CONDITIONS]),
        ("Task performance", "mean episode return", [aggregates[c]["return_mean"] for c in CONDITIONS]),
        ("Physical hazard contact", "mean native cost / episode", [aggregates[c]["native_cost_mean"] for c in CONDITIONS]),
    ]
    for panel_index, (axis, (title, ylabel, values)) in enumerate(zip(axes.flat, panels)):
        bars = axis.bar(labels, values, color=colors)
        axis.set(title=title, ylabel=ylabel)
        axis.grid(axis="y", alpha=0.2)
        axis.tick_params(axis="x", labelrotation=12)
        upper = max(values) if values else 1.0
        pad = max(0.02, 0.04 * max(upper, 1.0))
        for condition, bar, value in zip(CONDITIONS, bars, values):
            label = f"{value:.3f}"
            if panel_index == 0:
                label += f"\n({int(aggregates[condition]['missed'])}/{int(aggregates[condition]['triggers'])})"
            axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + pad, label, ha="center", fontsize=8)
    axes[0, 0].set_ylim(0, 1.05)
    axes[0, 1].set_ylim(0, 1.08)
    figure.suptitle("Fixed final checkpoints: 100 paired stochastic episodes")
    figure.tight_layout()
    figure.savefig(root / "full_dense_final_outcomes.png", dpi=190)
    plt.close(figure)

    # Figure 4: one deterministic trajectory per condition.
    figure, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
    for axis, condition in zip(axes, CONDITIONS):
        rows = trajectory_rows[condition]
        first = rows[0]
        for index in range(8):
            center = (float(first[f"hazard_{index}_x"]), float(first[f"hazard_{index}_y"]))
            axis.add_patch(Circle(center, 0.20, color="#4c78a8", alpha=0.35))
            axis.add_patch(Circle(center, 0.25, fill=False, color="#d62728", linestyle="--", linewidth=0.8))
            axis.add_patch(Circle(center, 0.28, fill=False, color="#2ca02c", linestyle=":", linewidth=0.8))
        goals: List[Tuple[float, float]] = []
        for row in rows:
            goal = (float(row["goal_x"]), float(row["goal_y"]))
            if goal not in goals:
                goals.append(goal)
        axis.scatter([goal[0] for goal in goals], [goal[1] for goal in goals], marker="*", s=65, color="#eeca3b", edgecolor="black", linewidth=0.4, zorder=4)
        axis.plot([float(row["agent_x"]) for row in rows], [float(row["agent_y"]) for row in rows], color="#222222", linewidth=1.1)
        for field, marker, color in (
            ("warning_trigger", "v", "#9467bd"),
            ("recovery", "o", "#2ca02c"),
            ("deadline_violation", "X", "#d62728"),
            ("terminal_unresolved", "P", "black"),
        ):
            selected = [row for row in rows if bool(row[field])]
            if selected:
                axis.scatter([float(row["agent_x"]) for row in selected], [float(row["agent_y"]) for row in selected], marker=marker, color=color, s=28, zorder=5)
        axis.set(xlim=(-1.55, 1.55), ylim=(-1.55, 1.55), aspect="equal", title=LABELS[condition], xlabel="x")
        axis.grid(alpha=0.15)
    axes[0].set_ylabel("y")
    figure.suptitle("Deterministic seed 59301: common Gold-STL geometry and event overlay")
    figure.tight_layout()
    figure.savefig(root / "full_dense_deterministic_trajectories.png", dpi=190)
    plt.close(figure)

    stl = aggregates["stl_dense_safety"]
    native = aggregates["native_safety"]
    stl_cmp = comparisons["stl_dense_safety"]
    native_cmp = comparisons["native_safety"]
    lines = [
        "# Fixed-route v1 full C1-dense round result",
        "",
        "## Scope and validity",
        "",
        "This report analyzes one matched training seed (`12647`), three fixed final 1M-transition checkpoints and 100 paired stochastic evaluation episodes per condition. It is exploratory: it is not the frozen five-seed confirmatory study and does not establish a formal safety guarantee.",
        "",
        "The original runner stopped after training because one of 100 STL CSV rows differed between selected and dense logger aggregates by `3.8147e-6` at scale `42.2763` (about `9.0e-8` relative). All three checkpoints were complete and finite. A scale-aware validation accepted the existing checkpoint; the original failed manifest remains unchanged.",
        "",
        "## Fixed-checkpoint result",
        "",
        "| Condition | Return mean | Goals/episode | Goal success | Gold missed / trigger | Native cost mean | Mean minimum distance |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        value = aggregates[condition]
        lines.append(
            f"| {LABELS[condition]} | {value['return_mean']:.3f} | {value['goal_events_mean']:.2f} | {value['goal_success_rate']:.1%} | {int(value['missed'])}/{int(value['triggers'])} = {value['missed_rate']:.3f} | {value['native_cost_mean']:.3f} | {value['minimum_distance_mean']:.3f} |",
        )
    lines.extend(
        [
            "",
            "Task-only and Native-safety had zero missed recovery obligations, whereas STL-dense had `31/139 = 0.223`. Because the Task-only baseline rate is zero, the frozen protocol uses absolute difference: the Task-minus-STL reduction is `-0.223` (95% paired episode-bootstrap interval `-0.313` to `-0.139`), and Task-minus-Native is `0.000`. Relative reduction is undefined. STL-dense therefore does not meet the intended safety direction in this run.",
            "",
            f"STL-dense retained 100% goal success but its mean return was `{stl['return_mean']:.3f}` versus Task-only `{aggregates['task_only']['return_mean']:.3f}`. Its physical native cost mean was `{stl['native_cost_mean']:.3f}` versus `{aggregates['task_only']['native_cost_mean']:.3f}`.",
            f"Native-safety reduced physical native cost from `{aggregates['task_only']['native_cost_mean']:.3f}` to `{native['native_cost_mean']:.3f}`, while mean return changed from `{aggregates['task_only']['return_mean']:.3f}` to `{native['return_mean']:.3f}`.",
            "",
            "Paired episode-bootstrap intervals are descriptive only because policies come from one training seed:",
            "",
            f"- STL minus Task return difference 95% interval: `{stl_cmp['return_difference_ci95'][0]:.3f}` to `{stl_cmp['return_difference_ci95'][1]:.3f}`.",
            f"- Native minus Task return difference 95% interval: `{native_cmp['return_difference_ci95'][0]:.3f}` to `{native_cmp['return_difference_ci95'][1]:.3f}`.",
            f"- STL minus Task native-cost difference 95% interval: `{stl_cmp['native_cost_difference_ci95'][0]:.3f}` to `{stl_cmp['native_cost_difference_ci95'][1]:.3f}`.",
            f"- Native minus Task native-cost difference 95% interval: `{native_cmp['native_cost_difference_ci95'][0]:.3f}` to `{native_cmp['native_cost_difference_ci95'][1]:.3f}`.",
            "",
            "Online monitor and independent oracle agreed in every evaluated episode for all three conditions; RTAMT completed-window maximum robustness difference was zero.",
            "",
            "## Interpretation",
            "",
            "The dense interface definitely supplied non-sparse training feedback, but it did not produce a safer final policy. Over the last 20 training epochs, STL selected cost averaged `16.535`, above its frozen `10.995` limit, while its Lagrange multiplier averaged `1.444` and ended at `1.490`. The STL return was still improving but remained far below Task-only. These traces do not support a convergence claim.",
            "",
            "The outcome pattern is mechanistically important: STL-dense reduced the number of warning triggers (`139` versus Task-only `268`) but missed `31` of the obligations it did trigger, reduced goal throughput, and increased physical contact. A plausible interpretation is that the accumulated pending-obligation surrogate and tight episode-level budget encouraged avoiding triggers without learning reliable recovery after entry; this is an inference, not yet a causal conclusion. Native cost, by contrast, nearly eliminated physical hazard contact (`0.020` versus `2.420`) while preserving zero Gold misses, though at a smaller task-return penalty.",
            "",
            "The next step should be mechanism diagnosis before another long run: inspect C1 cost/value/advantage scale around trigger and recovery windows, test whether accumulated surrogate mass overwhelms the event objective, and evaluate these fixed checkpoints on prospectively defined held-out routes/layouts. Any cost normalization or scenario/rule change must be frozen before seeing new training outcomes.",
            "",
            "Learning-curve tail values remain in `analysis_summary.json`; visual inspection is still required before calling any condition converged.",
            "",
            "## Figures",
            "",
            "- `results/fixed_route_v1/full_dense_round/full_dense_learning_curves.png`",
            "- `results/fixed_route_v1/full_dense_round/full_dense_constraint_diagnostics.png`",
            "- `results/fixed_route_v1/full_dense_round/full_dense_final_outcomes.png`",
            "- `results/fixed_route_v1/full_dense_round/full_dense_deterministic_trajectories.png`",
        ],
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    figure_names = (
        "full_dense_learning_curves.png",
        "full_dense_constraint_diagnostics.png",
        "full_dense_final_outcomes.png",
        "full_dense_deterministic_trajectories.png",
    )
    figure_manifest = {
        "schema_version": 1,
        "figures": {
            name: {"bytes": (root / name).stat().st_size, "sha256": _sha256(root / name)}
            for name in figure_names
        },
    }
    (root / "figure_manifest.json").write_text(
        json.dumps(figure_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"analysis": str(root / "analysis_summary.json"), "report": str(report), "figure_manifest": str(root / "figure_manifest.json"), "figures": [str(root / name) for name in figure_names]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
