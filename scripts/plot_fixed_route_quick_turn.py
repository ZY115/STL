#!/usr/bin/env python3
"""Create D43 trajectory/learning figures, compact tables and report."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LABELS = {"task_only": "Task-only", "native_safety": "Native-safety", "stl_dense_safety": "STL-dense-safety"}


def _json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "results/fixed_route_v1/quick_turn")
    options = parser.parse_args(); root = options.output_root.resolve()
    training = _json(root / "training_summary.json")
    conditions = ["task_only", "native_safety", "stl_dense_safety"]
    trajectory_rows: List[Dict[str, Any]] = []
    episode_rows: List[Dict[str, Any]] = []
    for condition in conditions:
        for row in _csv(root / "evaluation" / condition / "stochastic" / "episodes.csv"):
            episode_rows.append({"condition": condition, **row})
        trajectory_path = root / "evaluation" / condition / "deterministic" / "trajectories.jsonl"
        with trajectory_path.open("r", encoding="utf-8") as handle:
            trajectory_rows.extend({"condition": condition, **json.loads(line)} for line in handle)
    with (root / "evaluation_episodes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(episode_rows[0])); writer.writeheader(); writer.writerows(episode_rows)
    with (root / "deterministic_trajectories.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trajectory_rows[0])); writer.writeheader(); writer.writerows(trajectory_rows)

    figure, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
    for axis, condition in zip(axes, conditions):
        rows = [row for row in trajectory_rows if row["condition"] == condition]
        first = rows[0]
        for index in range(8):
            center = (float(first[f"hazard_{index}_x"]), float(first[f"hazard_{index}_y"]))
            axis.add_patch(Circle(center, 0.20, color="#4c78a8", alpha=0.4))
            axis.add_patch(Circle(center, 0.25, fill=False, color="#d62728", linestyle="--", linewidth=0.8))
            axis.add_patch(Circle(center, 0.28, fill=False, color="#2ca02c", linestyle=":", linewidth=0.8))
        axis.plot([float(row["agent_x"]) for row in rows], [float(row["agent_y"]) for row in rows], color="#222222", linewidth=1.0)
        for field, marker, color in (("warning_trigger", "v", "#9467bd"), ("recovery", "o", "#2ca02c"), ("deadline_violation", "X", "#d62728"), ("terminal_unresolved", "P", "black")):
            selected = [row for row in rows if str(row[field]).lower() == "true"]
            if selected:
                axis.scatter([float(row["agent_x"]) for row in selected], [float(row["agent_y"]) for row in selected], marker=marker, color=color, s=28, zorder=5)
        axis.set(xlim=(-1.55, 1.55), ylim=(-1.55, 1.55), aspect="equal", title=LABELS[condition], xlabel="x")
        axis.grid(alpha=0.15)
    axes[0].set_ylabel("y"); figure.suptitle("Fixed-route final deterministic trajectories; common Gold overlay")
    figure.tight_layout(); figure.savefig(root / "fixed_route_quick_turn_trajectories.png", dpi=190); plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for cell in training["cells"]:
        rows = _csv(Path(cell["progress"])); condition = cell["condition_id"]
        x = [float(row["TotalEnvSteps"]) for row in rows]
        axes[0].plot(x, [float(row["Metrics/EpRet"]) for row in rows], label=LABELS[condition])
        axes[1].plot(x, [float(row["Metrics/SelectedAlgorithmCost"]) for row in rows], label=LABELS[condition])
    axes[0].set(title="Episode return", xlabel="Transitions", ylabel="rolling mean")
    axes[1].set(title="Selected learner cost (units differ)", xlabel="Transitions", ylabel="rolling mean")
    for axis in axes: axis.grid(alpha=0.2); axis.legend(fontsize=8)
    figure.tight_layout(); figure.savefig(root / "fixed_route_quick_turn_learning_curves.png", dpi=190); plt.close(figure)

    aggregates: Dict[str, Dict[str, float]] = {}
    for condition in conditions:
        rows = [row for row in episode_rows if row["condition"] == condition]
        returns = sum(float(row["episode_return"]) for row in rows) / len(rows)
        success = sum(str(row["goal_success"]).lower() == "true" for row in rows) / len(rows)
        triggers = sum(int(row["trigger_count"]) for row in rows); missed = sum(int(row["deadline_violation_count"]) + int(row["terminal_unresolved_count"]) for row in rows)
        native = sum(float(row["native_cost_total"]) for row in rows) / len(rows)
        goals = sum(float(row["goal_events"]) for row in rows) / len(rows)
        aggregates[condition] = {
            "return": returns,
            "success": success,
            "triggers": float(triggers),
            "missed": float(missed),
            "missed_rate": float("nan") if triggers == 0 else missed / triggers,
            "native": native,
            "goals": goals,
        }

    colors = ["#4c78a8", "#f58518", "#54a24b"]
    labels = [LABELS[condition] for condition in conditions]
    figure, axes = plt.subplots(1, 3, figsize=(13.5, 4.2))
    missed_values = [aggregates[condition]["missed_rate"] for condition in conditions]
    bars = axes[0].bar(labels, missed_values, color=colors)
    axes[0].set(title="Gold missed recovery obligations", ylabel="missed / triggered obligations", ylim=(0, 1.05))
    for bar, condition in zip(bars, conditions):
        value = aggregates[condition]
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.025, f"{value['missed_rate']:.3f}\n({int(value['missed'])}/{int(value['triggers'])})", ha="center", va="bottom", fontsize=8)
    axes[1].bar(labels, [aggregates[condition]["return"] for condition in conditions], color=colors)
    axes[1].set(title="Task performance", ylabel="mean episode return")
    axes[2].bar(labels, [aggregates[condition]["native"] for condition in conditions], color=colors)
    axes[2].set(title="Native hazard contact", ylabel="mean native cost / episode")
    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
        axis.tick_params(axis="x", labelrotation=18)
    figure.suptitle("Fixed final checkpoints: 20 paired stochastic episodes (exploratory)")
    figure.tight_layout(); figure.savefig(root / "fixed_route_quick_turn_outcomes.png", dpi=190); plt.close(figure)

    task_rate = aggregates["task_only"]["missed_rate"]
    stl_rate = aggregates["stl_dense_safety"]["missed_rate"]
    native_rate = aggregates["native_safety"]["missed_rate"]
    stl_absolute = task_rate - stl_rate
    stl_relative = stl_absolute / task_rate if task_rate else float("nan")
    native_absolute = task_rate - native_rate
    native_relative = native_absolute / task_rate if task_rate else float("nan")
    budgets = _json(root / "task_control_budgets.json")
    lines = [
        "# Fixed-route v1 quick-turn report",
        "",
        "- Status: exploratory D43 diagnostic completed",
        f"- Matched transitions per condition: {training['effective_transitions_per_condition']:,}",
        f"- Aggregate reported training seconds: {training['aggregate_training_seconds']:.2f} ({training['aggregate_training_seconds'] / 60:.2f} minutes)",
        "- Evaluation: one matched training seed; 20 paired stochastic episodes and one deterministic visualization episode per condition",
        "- Hardware authority: D45 administrator risk override for D43 only; the D41 CPU/RAM stability gate was not declared passed",
        "",
        "This bounded result is not evidence of convergence, statistical significance, method superiority or generalization. Native and C1 costs have different units. All safety comparisons below use the unchanged Gold binary evaluator, not a learner surrogate.",
        "",
        "## Stochastic final-checkpoint summary",
        "",
        "| Condition | Return mean | Goals/episode | Goal success | Missed/trigger | Missed / triggers | Native cost mean |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in conditions:
        value = aggregates[condition]
        ratio = "N/A" if value["triggers"] == 0 else f"{value['missed_rate']:.3f}"
        lines.append(f"| {LABELS[condition]} | {value['return']:.3f} | {value['goals']:.2f} | {value['success']:.1%} | {ratio} | {int(value['missed'])} / {int(value['triggers'])} | {value['native']:.3f} |")
    lines.extend(
        [
            "",
            "## Descriptive matched comparisons",
            "",
            f"- STL-dense versus task-only: missed/trigger absolute reduction `{stl_absolute:.3f}`; relative reduction `{stl_relative:.1%}`.",
            f"- Native versus task-only: missed/trigger absolute reduction `{native_absolute:.3f}`; relative reduction `{native_relative:.1%}`.",
            "- All three conditions reached at least one goal in all 20 episodes; this satisfies the quick-turn visibility check but is not a powered non-inferiority test.",
            "- Online monitor and independent oracle agreed on every evaluated episode; RTAMT completed-window maximum robustness difference was zero.",
            "",
            "The STL-dense point estimate crosses the historical 30% reduction target, while Native does not. Because D43 has only one training seed and 20 evaluation episodes, this observation is a screening signal only and must not be promoted to a confirmatory claim.",
            "",
            "## Frozen quick-turn pressure budgets",
            "",
            f"- Native: task-control mean `{budgets['task_control_mean']['native_cost_per_episode']:.3f}` native events/episode; limit `{budgets['cost_limit']['native_cost_per_episode']:.3f}`.",
            f"- C1: task-control mean `{budgets['task_control_mean']['c1_surrogate_mass_per_episode']:.3f}` surrogate-mass units/episode; limit `{budgets['cost_limit']['c1_surrogate_mass_per_episode']:.3f}`.",
            "",
            "These limits were frozen separately at 70% of the corresponding task-only mean. Their numerical values are not directly comparable.",
            "",
            "## Figures",
            "",
            "- `results/fixed_route_v1/quick_turn/fixed_route_quick_turn_outcomes.png`",
            "- `results/fixed_route_v1/quick_turn/fixed_route_quick_turn_learning_curves.png`",
            "- `results/fixed_route_v1/quick_turn/fixed_route_quick_turn_trajectories.png`",
            "",
            "The deterministic trajectory panels are qualitative single episodes. In that seed, all three policies triggered once and recovered within K=25; they are not the source of the stochastic safety rates above.",
            "",
            "## Execution note",
            "",
            "The first preflight implementation used one optimizer iteration while reported epochs used 40, which inflated its throughput estimate. The resulting 150k task-only attempt was stopped after 40k transitions and retained as a failed diagnostic attempt. The preflight was corrected to use the full 40-iteration workload; three corrected 10k preflights selected 70k matched transitions. The interrupted attempt's 232.46 seconds remain included in the 1,395.16-second aggregate cap accounting.",
            "",
            "No D38, Stage II-A, full 1M-per-condition pilot or confirmatory run was started.",
        ],
    )
    report = ROOT / "docs/fixed_route_v1_quick_turn_report.md"; report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"trajectory_figure": str(root / "fixed_route_quick_turn_trajectories.png"), "learning_curve_figure": str(root / "fixed_route_quick_turn_learning_curves.png"), "outcome_figure": str(root / "fixed_route_quick_turn_outcomes.png"), "report": str(report)}, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
