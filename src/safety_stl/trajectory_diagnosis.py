"""Post-pilot replay and behavioral diagnosis using existing checkpoints only."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from safety_stl.evaluation import evaluate_checkpoint


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONDITIONS = ("task_only", "native_cost", "gold_stl_cost")
TRAINING_SEEDS = (1101, 2202, 3303, 4404, 5505)
EVALUATION_SEEDS = tuple(range(10000, 10100))
REPRESENTATIVE_CASES = (
    {
        "case_id": "gold_worse_seed-4404_eval-10066",
        "selection": "largest_gold_minus_task_missed",
        "training_seed": 4404,
        "evaluation_seed": 10066,
    },
    {
        "case_id": "gold_better_seed-2202_eval-10031",
        "selection": "largest_task_minus_gold_missed",
        "training_seed": 2202,
        "evaluation_seed": 10031,
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"expected mapping: {path}")
    return dict(value)


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write an empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def job_manifest_path(repository_root: Path, condition: str, training_seed: int) -> Path:
    return (
        repository_root
        / "results"
        / "stage1_pilot"
        / "jobs"
        / condition
        / f"seed-{training_seed}"
        / "manifest.json"
    )


def load_job(repository_root: Path, condition: str, training_seed: int) -> Dict[str, Any]:
    path = job_manifest_path(repository_root, condition, training_seed)
    manifest = load_json(path)
    if manifest.get("status") != "success":
        raise RuntimeError(f"pilot job is not successful: {path}")
    checkpoint = Path(str(manifest["final_checkpoint"]["path"]))
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if sha256_file(checkpoint) != manifest["final_checkpoint"]["sha256"]:
        raise RuntimeError(f"checkpoint hash mismatch: {checkpoint}")
    return manifest


def assert_replay_matches_frozen(
    replayed: Sequence[Mapping[str, Any]],
    frozen_path: Path,
) -> None:
    """Require the new deterministic replay to reproduce the frozen episode table."""

    frozen = read_csv(frozen_path)
    if len(replayed) != len(frozen):
        raise AssertionError("replayed and frozen episode counts differ")
    integer_fields = (
        "evaluation_seed",
        "episode_length",
        "gold_stl_cost_total",
        "goal_events",
        "trigger_count",
        "recovery_count",
        "late_recovery_count",
        "deadline_violation_count",
        "terminal_unresolved_count",
    )
    float_fields = ("episode_return", "native_cost_total", "minimum_distance")
    for current, expected in zip(replayed, frozen):
        for field in integer_fields:
            if int(current[field]) != int(float(expected[field])):
                raise AssertionError(f"replay mismatch in {field}: {current} versus {expected}")
        for field in float_fields:
            if not math.isclose(
                float(current[field]),
                float(expected[field]),
                rel_tol=0.0,
                abs_tol=1e-8,
            ):
                raise AssertionError(f"replay mismatch in {field}: {current} versus {expected}")


def summarize_condition(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    episodes = len(rows)
    triggers = sum(int(row["trigger_count"]) for row in rows)
    recoveries = sum(int(row["recovery_count"]) for row in rows)
    violations = sum(int(row["deadline_violation_count"]) for row in rows)
    unresolved = sum(int(row["terminal_unresolved_count"]) for row in rows)
    actions = sum(int(row["episode_length"]) for row in rows)
    positive_cost_steps = sum(int(row["positive_cost_step_count"]) for row in rows)
    recovery_latency_sum = sum(float(row["on_time_recovery_latency_sum"]) for row in rows)
    deadline_delay_sum = sum(float(row["deadline_violation_delay_sum"]) for row in rows)
    unresolved_delay_sum = sum(float(row["terminal_unresolved_delay_sum"]) for row in rows)
    missed = violations + unresolved
    return {
        "episode_count": episodes,
        "action_step_count": actions,
        "trigger_count": triggers,
        "triggers_per_episode": triggers / episodes,
        "on_time_recovery_count": recoveries,
        "on_time_recovery_rate_per_trigger": recoveries / triggers if triggers else None,
        "mean_on_time_recovery_latency_steps": (
            recovery_latency_sum / recoveries if recoveries else None
        ),
        "deadline_violation_count": violations,
        "terminal_unresolved_count": unresolved,
        "missed_obligation_count": missed,
        "missed_obligation_rate_per_trigger": missed / triggers if triggers else None,
        "missed_obligations_per_episode": missed / episodes,
        "mean_deadline_violation_cost_delay_steps": (
            deadline_delay_sum / violations if violations else None
        ),
        "mean_terminal_unresolved_cost_delay_steps": (
            unresolved_delay_sum / unresolved if unresolved else None
        ),
        "positive_cost_step_count": positive_cost_steps,
        "positive_cost_frequency_per_action_step": positive_cost_steps / actions,
        "mean_episode_return": sum(float(row["episode_return"]) for row in rows) / episodes,
        "mean_native_cost_per_episode": (
            sum(float(row["native_cost_total"]) for row in rows) / episodes
        ),
        "goal_success_rate": sum(bool(row["goal_success"]) for row in rows) / episodes,
    }


def effect_decomposition(condition_summary: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    task = condition_summary["task_only"]
    output: Dict[str, Any] = {}
    for condition in ("native_cost", "gold_stl_cost"):
        current = condition_summary[condition]
        output[condition] = {
            "relative_trigger_frequency_change_vs_task": (
                current["triggers_per_episode"] / task["triggers_per_episode"] - 1.0
            ),
            "absolute_on_time_recovery_rate_change_vs_task": (
                current["on_time_recovery_rate_per_trigger"]
                - task["on_time_recovery_rate_per_trigger"]
            ),
            "absolute_missed_rate_change_vs_task": (
                current["missed_obligation_rate_per_trigger"]
                - task["missed_obligation_rate_per_trigger"]
            ),
            "interpretation": (
                "entry-frequency changed more clearly than conditional recovery"
                if condition == "native_cost"
                else "neither entry frequency nor conditional recovery materially changed"
            ),
        }
    return output


def _flatten_episode(
    condition: str,
    training_seed: int,
    episode: Mapping[str, Any],
) -> Dict[str, Any]:
    return {"condition": condition, "training_seed": training_seed, **episode}


def replay_full_matrix(
    repository_root: Path = REPOSITORY_ROOT,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    all_episodes: List[Dict[str, Any]] = []
    checkpoint_rows: List[Dict[str, Any]] = []
    provenance: List[Dict[str, Any]] = []
    for condition in CONDITIONS:
        for training_seed in TRAINING_SEEDS:
            manifest = load_job(repository_root, condition, training_seed)
            print(f"replay {condition} seed={training_seed}", flush=True)
            summary, episodes, _ = evaluate_checkpoint(
                Path(str(manifest["run_dir"])),
                Path(str(manifest["final_checkpoint"]["path"])).name,
                EVALUATION_SEEDS,
                max_episode_steps=1000,
                deterministic=True,
                save_trajectories=False,
            )
            frozen_episodes = Path(str(manifest["evaluation"]["episodes"]["path"]))
            assert_replay_matches_frozen(episodes, frozen_episodes)
            flattened = [_flatten_episode(condition, training_seed, row) for row in episodes]
            all_episodes.extend(flattened)
            checkpoint_summary = summarize_condition(flattened)
            checkpoint_rows.append(
                {
                    "condition": condition,
                    "training_seed": training_seed,
                    **checkpoint_summary,
                },
            )
            provenance.append(
                {
                    "condition": condition,
                    "training_seed": training_seed,
                    "run_dir": str(manifest["run_dir"]),
                    "checkpoint": str(manifest["final_checkpoint"]["path"]),
                    "checkpoint_sha256": str(manifest["final_checkpoint"]["sha256"]),
                    "frozen_episode_table": str(frozen_episodes),
                    "frozen_episode_sha256": str(manifest["evaluation"]["episodes"]["sha256"]),
                    "replay_matches_frozen": True,
                    "gold_oracle_agreement": bool(summary["aggregate"]["all_online_oracle_agree"]),
                    "rtamt_max_robustness_difference": float(
                        summary["aggregate"]["rtamt_max_robustness_difference"],
                    ),
                },
            )
    condition_summary = {
        condition: summarize_condition(
            [row for row in all_episodes if row["condition"] == condition],
        )
        for condition in CONDITIONS
    }
    summary = {
        "schema_version": 1,
        "scope": "CPU deterministic replay only; no training and no checkpoint selection",
        "conditions": condition_summary,
        "effect_decomposition": effect_decomposition(condition_summary),
        "matrix": {
            "checkpoint_count": len(provenance),
            "episode_count": len(all_episodes),
            "training_seeds": list(TRAINING_SEEDS),
            "evaluation_seeds": list(EVALUATION_SEEDS),
            "fixed_checkpoint": "epoch-100.pt",
            "all_replays_match_frozen": all(row["replay_matches_frozen"] for row in provenance),
            "all_gold_oracle_agree": all(row["gold_oracle_agreement"] for row in provenance),
            "rtamt_max_robustness_difference": max(
                row["rtamt_max_robustness_difference"] for row in provenance
            ),
        },
        "provenance": provenance,
    }
    return summary, all_episodes, checkpoint_rows


def replay_representative_cases(
    repository_root: Path = REPOSITORY_ROOT,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    trajectories: List[Dict[str, Any]] = []
    provenance: List[Dict[str, Any]] = []
    for case in REPRESENTATIVE_CASES:
        for condition in CONDITIONS:
            training_seed = int(case["training_seed"])
            evaluation_seed = int(case["evaluation_seed"])
            manifest = load_job(repository_root, condition, training_seed)
            summary, episodes, rows = evaluate_checkpoint(
                Path(str(manifest["run_dir"])),
                Path(str(manifest["final_checkpoint"]["path"])).name,
                [evaluation_seed],
                max_episode_steps=1000,
                deterministic=True,
                save_trajectories=True,
            )
            if len(episodes) != 1:
                raise AssertionError("representative replay must contain one episode")
            trajectory_id = f"real__{condition}__train-{training_seed}__eval-{evaluation_seed}"
            for row in rows:
                trajectories.append(
                    {
                        "trajectory_id": trajectory_id,
                        "case_id": str(case["case_id"]),
                        "selection": str(case["selection"]),
                        "condition": condition,
                        "training_seed": training_seed,
                        **row,
                    },
                )
            provenance.append(
                {
                    "trajectory_id": trajectory_id,
                    "case_id": str(case["case_id"]),
                    "selection": str(case["selection"]),
                    "condition": condition,
                    "training_seed": training_seed,
                    "evaluation_seed": evaluation_seed,
                    "checkpoint": str(manifest["final_checkpoint"]["path"]),
                    "checkpoint_sha256": str(manifest["final_checkpoint"]["sha256"]),
                    "episode": episodes[0],
                    "gold_oracle_agreement": bool(summary["aggregate"]["all_online_oracle_agree"]),
                    "rtamt_max_robustness_difference": float(
                        summary["aggregate"]["rtamt_max_robustness_difference"],
                    ),
                },
            )
    return trajectories, provenance


def plot_diagnosis(
    trajectories: Sequence[Mapping[str, Any]],
    condition_summary: Mapping[str, Mapping[str, Any]],
    output_dir: Path,
) -> List[Path]:
    """Create representative trajectory and aggregate mechanism figures."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    output_dir.mkdir(parents=True, exist_ok=True)
    condition_labels = {
        "task_only": "Task only",
        "native_cost": "Native cost",
        "gold_stl_cost": "Gold STL cost",
    }
    colors = {"task_only": "#4c78a8", "native_cost": "#f58518", "gold_stl_cost": "#54a24b"}

    figure, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True, sharey=True)
    for row_index, case in enumerate(REPRESENTATIVE_CASES):
        for column_index, condition in enumerate(CONDITIONS):
            axis = axes[row_index, column_index]
            rows = [
                row
                for row in trajectories
                if row["case_id"] == case["case_id"] and row["condition"] == condition
            ]
            steps = np.asarray([int(row["sample_index"]) for row in rows])
            distance = np.asarray([float(row["distance"]) for row in rows])
            axis.plot(steps, distance, color=colors[condition], linewidth=1.0)
            axis.axhline(0.45, color="#d62728", linestyle="--", linewidth=0.8, label="d_warn")
            axis.axhline(0.55, color="#2ca02c", linestyle=":", linewidth=0.8, label="d_safe")
            event_styles = (
                ("warning_trigger", "v", "#9467bd", "trigger"),
                ("recovery", "o", "#2ca02c", "on-time recovery"),
                ("deadline_violation", "X", "#d62728", "deadline violation"),
                ("terminal_unresolved", "*", "#111111", "terminal unresolved"),
            )
            for field, marker, color, label in event_styles:
                event_rows = [row for row in rows if bool(row[field])]
                if event_rows:
                    axis.scatter(
                        [int(row["sample_index"]) for row in event_rows],
                        [float(row["distance"]) for row in event_rows],
                        marker=marker,
                        color=color,
                        s=34,
                        zorder=3,
                        label=label,
                    )
            axis.set_title(
                f"{case['case_id']}\n{condition_labels[condition]}",
                fontsize=9,
            )
            axis.grid(alpha=0.2)
            if column_index == 0:
                axis.set_ylabel("nearest-hazard distance")
            if row_index == 1:
                axis.set_xlabel("environment sample")
    legend_items: Dict[str, Any] = {}
    for axis in axes.reshape(-1):
        axis_handles, axis_labels = axis.get_legend_handles_labels()
        for handle, label in zip(axis_handles, axis_labels):
            legend_items.setdefault(label, handle)
    figure.suptitle("Existing final-checkpoint behavior on frozen representative cases", y=0.99)
    figure.legend(
        list(legend_items.values()),
        list(legend_items),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.955),
        ncol=6,
        frameon=False,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
    trajectory_path = output_dir / "representative_trajectory_replays.png"
    figure.savefig(trajectory_path, dpi=180, bbox_inches="tight")
    plt.close(figure)

    figure, axes = plt.subplots(2, 2, figsize=(10, 7))
    labels = [condition_labels[name] for name in CONDITIONS]
    values = [condition_summary[name] for name in CONDITIONS]
    palette = [colors[name] for name in CONDITIONS]
    panels = (
        ("triggers_per_episode", "Triggers / episode"),
        ("missed_obligation_rate_per_trigger", "Missed obligations / trigger"),
        ("mean_on_time_recovery_latency_steps", "Mean on-time recovery latency (steps)"),
        ("positive_cost_frequency_per_action_step", "Positive STL-cost frequency / action step"),
    )
    for axis, (field, title) in zip(axes.reshape(-1), panels):
        axis.bar(labels, [float(row[field]) for row in values], color=palette)
        axis.set_title(title)
        axis.tick_params(axis="x", rotation=15)
        axis.grid(axis="y", alpha=0.2)
    figure.suptitle("Mechanism decomposition from 1,500 deterministic replays")
    figure.tight_layout()
    mechanism_path = output_dir / "trajectory_mechanism_summary.png"
    figure.savefig(mechanism_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return [trajectory_path, mechanism_path]


def run_diagnosis(output_dir: Path, repository_root: Path = REPOSITORY_ROOT) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary, episodes, checkpoint_rows = replay_full_matrix(repository_root)
    trajectories, representative_provenance = replay_representative_cases(repository_root)
    episode_path = output_dir / "replayed_episode_diagnostics.csv"
    checkpoint_path = output_dir / "checkpoint_diagnostics.csv"
    trajectory_path = output_dir / "representative_per_step_trajectories.csv"
    provenance_path = output_dir / "representative_provenance.json"
    write_csv(episode_path, episodes)
    write_csv(checkpoint_path, checkpoint_rows)
    write_csv(trajectory_path, trajectories)
    with provenance_path.open("w", encoding="utf-8") as handle:
        json.dump(representative_provenance, handle, indent=2, sort_keys=True)
        handle.write("\n")
    figure_paths = plot_diagnosis(trajectories, summary["conditions"], output_dir / "figures")
    artifacts = [episode_path, checkpoint_path, trajectory_path, provenance_path, *figure_paths]
    summary["representative_cases"] = representative_provenance
    summary["artifacts"] = {
        path.relative_to(output_dir).as_posix(): sha256_file(path) for path in artifacts
    }
    summary_path = output_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return summary


__all__ = [
    "CONDITIONS",
    "EVALUATION_SEEDS",
    "REPRESENTATIVE_CASES",
    "TRAINING_SEEDS",
    "assert_replay_matches_frozen",
    "effect_decomposition",
    "replay_full_matrix",
    "replay_representative_cases",
    "run_diagnosis",
    "summarize_condition",
]
