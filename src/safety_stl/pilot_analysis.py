"""Frozen paired hierarchical analysis for the Stage I gold-STL pilot."""

from __future__ import annotations

import csv
import copy
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from safety_stl.pilot_protocol import validate_protocol
from safety_stl.pilot_runner import (
    CONDITION_ORDER,
    load_json_mapping,
    read_progress_rows,
    sha256_file,
)


EPISODE_FLOAT_FIELDS = (
    "episode_return",
    "native_cost_total",
    "gold_stl_cost_total",
    "goal_events",
    "episode_length",
    "minimum_distance",
    "trigger_count",
    "recovery_count",
    "late_recovery_count",
    "deadline_violation_count",
    "terminal_unresolved_count",
    "completed_window_count",
    "rtamt_max_robustness_difference",
)
ANALYSIS_CONDITION_METRICS = (
    "missed_obligation_rate_per_trigger",
    "deadline_violation_rate_per_trigger",
    "terminal_unresolved_rate_per_trigger",
    "triggers_per_episode",
    "triggered_episode_rate",
    "missed_obligations_per_episode",
    "native_cost_per_episode",
    "stl_cost_per_episode",
    "episode_return",
    "goal_success_rate",
    "goal_events_per_episode",
)


@dataclass(frozen=True)
class HierarchicalDraw:
    """One resampled training-seed cluster and its within-seed episode draw."""

    source_training_seed: int
    evaluation_seeds: Tuple[int, ...]


def _optional_divide(numerator: float, denominator: float) -> Optional[float]:
    return numerator / denominator if denominator else None


def _mean(records: Sequence[Mapping[str, Any]], field: str) -> float:
    return float(mean(float(record[field]) for record in records))


def aggregate_condition(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Pool obligation events while retaining episode-level task metrics."""

    if not records:
        raise ValueError("condition aggregation requires episode records")
    episode_count = len(records)
    triggers = sum(int(record["trigger_count"]) for record in records)
    deadline = sum(int(record["deadline_violation_count"]) for record in records)
    unresolved = sum(int(record["terminal_unresolved_count"]) for record in records)
    missed = deadline + unresolved
    return {
        "episode_count": episode_count,
        "trigger_count": triggers,
        "deadline_violation_count": deadline,
        "terminal_unresolved_count": unresolved,
        "missed_obligation_count": missed,
        "missed_obligation_rate_per_trigger": _optional_divide(missed, triggers),
        "deadline_violation_rate_per_trigger": _optional_divide(deadline, triggers),
        "terminal_unresolved_rate_per_trigger": _optional_divide(unresolved, triggers),
        "triggers_per_episode": triggers / episode_count,
        "triggered_episode_rate": sum(int(record["trigger_count"]) > 0 for record in records)
        / episode_count,
        "missed_obligations_per_episode": missed / episode_count,
        "native_cost_per_episode": _mean(records, "native_cost_total"),
        "stl_cost_per_episode": _mean(records, "gold_stl_cost_total"),
        "episode_return": _mean(records, "episode_return"),
        "goal_success_rate": sum(bool(record["goal_success"]) for record in records)
        / episode_count,
        "goal_events_per_episode": _mean(records, "goal_events"),
        "mean_episode_length": _mean(records, "episode_length"),
        "all_online_oracle_agree": all(
            bool(record["online_oracle_agreement"]) for record in records
        ),
        "rtamt_max_robustness_difference": max(
            float(record["rtamt_max_robustness_difference"]) for record in records
        ),
    }


def primary_comparison(
    task: Mapping[str, Any],
    gold: Mapping[str, Any],
    *,
    target_relative_reduction: float = 0.30,
) -> Dict[str, Any]:
    """Apply D31's sign and zero-baseline rules without replacing N/A by zero."""

    task_rate = task["missed_obligation_rate_per_trigger"]
    gold_rate = gold["missed_obligation_rate_per_trigger"]
    absolute = None
    relative = None
    if task_rate is not None and gold_rate is not None:
        absolute = float(task_rate) - float(gold_rate)
        if float(task_rate) > 0.0:
            relative = absolute / float(task_rate)
    baseline_zero = task_rate is not None and math.isclose(float(task_rate), 0.0, abs_tol=0.0)
    return {
        "task_only_rate": task_rate,
        "gold_stl_rate": gold_rate,
        "absolute_reduction_task_minus_gold": absolute,
        "relative_reduction": relative,
        "task_only_baseline_rate_is_zero": baseline_zero,
        "relative_reduction_is_undefined": relative is None,
        "relative_target": target_relative_reduction,
        "relative_target_met": (
            relative >= target_relative_reduction if relative is not None else None
        ),
        "zero_baseline_absolute_direction_improved": (
            absolute > 0.0 if baseline_zero and absolute is not None else None
        ),
    }


def goal_noninferiority(
    task_goal_success: float,
    gold_goal_success: float,
    *,
    margin: float = 0.10,
    confidence_interval: Optional[Mapping[str, Optional[float]]] = None,
) -> Dict[str, Any]:
    """Use gold minus task so non-inferiority requires a value at least -margin."""

    difference = gold_goal_success - task_goal_success
    lower = confidence_interval.get("lower") if confidence_interval else None
    return {
        "difference_gold_minus_task": difference,
        "noninferiority_margin": margin,
        "decision_boundary": -margin,
        "point_estimate_noninferior": difference >= -margin,
        "confidence_interval_supports_noninferiority": (
            lower >= -margin if lower is not None else None
        ),
    }


def draw_hierarchical_sample(
    training_seeds: Sequence[int],
    evaluation_seeds_by_training_seed: Mapping[int, Sequence[int]],
    rng: random.Random,
) -> List[HierarchicalDraw]:
    """Resample matched training clusters, then matched episodes within each cluster."""

    draws: List[HierarchicalDraw] = []
    for _ in training_seeds:
        source_seed = int(rng.choice(list(training_seeds)))
        available = list(evaluation_seeds_by_training_seed[source_seed])
        if not available:
            raise ValueError(f"training seed {source_seed} has no evaluation episodes")
        draws.append(
            HierarchicalDraw(
                source_training_seed=source_seed,
                evaluation_seeds=tuple(int(rng.choice(available)) for _ in available),
            ),
        )
    return draws


def _index_records(
    records: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[int, Dict[int, Mapping[str, Any]]]]:
    index: Dict[str, Dict[int, Dict[int, Mapping[str, Any]]]] = {
        condition: {} for condition in CONDITION_ORDER
    }
    for record in records:
        condition = str(record["condition"])
        seed = int(record["training_seed"])
        evaluation_seed = int(record["evaluation_seed"])
        bucket = index.setdefault(condition, {}).setdefault(seed, {})
        if evaluation_seed in bucket:
            raise ValueError(
                f"duplicate episode for {condition}, training seed {seed}, eval seed {evaluation_seed}",
            )
        bucket[evaluation_seed] = record
    return index


def paired_hierarchical_bootstrap(
    records: Sequence[Mapping[str, Any]],
    *,
    training_seeds: Sequence[int],
    replicates: int,
    rng_seed: int,
) -> Dict[str, Any]:
    """Bootstrap paired conditions at both the training-seed and episode levels."""

    if replicates <= 0:
        raise ValueError("bootstrap replicates must be positive")
    index = _index_records(records)
    evaluation_seeds_by_training_seed: Dict[int, List[int]] = {}
    for seed in training_seeds:
        seed_sets = [set(index[condition][int(seed)]) for condition in CONDITION_ORDER]
        if not all(values == seed_sets[0] for values in seed_sets[1:]):
            raise ValueError(f"evaluation seeds are not paired for training seed {seed}")
        evaluation_seeds_by_training_seed[int(seed)] = sorted(seed_sets[0])

    condition_values = {
        condition: {metric: [] for metric in ANALYSIS_CONDITION_METRICS}
        for condition in CONDITION_ORDER
    }
    primary_values: Dict[str, List[Optional[float]]] = {
        "absolute_reduction_task_minus_gold": [],
        "relative_reduction": [],
        "goal_success_difference_gold_minus_task": [],
    }
    primary_rows: List[Dict[str, Any]] = []
    rng = random.Random(int(rng_seed))
    for replicate in range(replicates):
        draws = draw_hierarchical_sample(training_seeds, evaluation_seeds_by_training_seed, rng)
        sampled: Dict[str, List[Mapping[str, Any]]] = {
            condition: [] for condition in CONDITION_ORDER
        }
        for draw in draws:
            for evaluation_seed in draw.evaluation_seeds:
                for condition in CONDITION_ORDER:
                    sampled[condition].append(
                        index[condition][draw.source_training_seed][evaluation_seed],
                    )
        aggregates = {
            condition: aggregate_condition(values) for condition, values in sampled.items()
        }
        for condition in CONDITION_ORDER:
            for metric in ANALYSIS_CONDITION_METRICS:
                condition_values[condition][metric].append(aggregates[condition][metric])
        primary = primary_comparison(aggregates["task_only"], aggregates["gold_stl_cost"])
        goal_difference = (
            aggregates["gold_stl_cost"]["goal_success_rate"]
            - aggregates["task_only"]["goal_success_rate"]
        )
        primary_values["absolute_reduction_task_minus_gold"].append(
            primary["absolute_reduction_task_minus_gold"],
        )
        primary_values["relative_reduction"].append(primary["relative_reduction"])
        primary_values["goal_success_difference_gold_minus_task"].append(goal_difference)
        primary_rows.append(
            {
                "replicate": replicate,
                "absolute_reduction_task_minus_gold": primary[
                    "absolute_reduction_task_minus_gold"
                ],
                "relative_reduction": primary["relative_reduction"],
                "goal_success_difference_gold_minus_task": goal_difference,
            },
        )
    return {
        "method": "paired_hierarchical_percentile_bootstrap",
        "replicates": replicates,
        "rng_seed": int(rng_seed),
        "condition_values": condition_values,
        "primary_values": primary_values,
        "primary_rows": primary_rows,
    }


def percentile_interval(
    values: Sequence[Optional[float]],
    *,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """Return a linear percentile interval and explicitly count undefined replicates."""

    valid = sorted(float(value) for value in values if value is not None and math.isfinite(value))
    if not valid:
        return {
            "lower": None,
            "upper": None,
            "valid_replicates": 0,
            "undefined_replicates": len(values),
        }

    def quantile(probability: float) -> float:
        position = probability * (len(valid) - 1)
        low = int(math.floor(position))
        high = int(math.ceil(position))
        if low == high:
            return valid[low]
        fraction = position - low
        return valid[low] * (1.0 - fraction) + valid[high] * fraction

    alpha = (1.0 - confidence_level) / 2.0
    return {
        "lower": quantile(alpha),
        "upper": quantile(1.0 - alpha),
        "valid_replicates": len(valid),
        "undefined_replicates": len(values) - len(valid),
    }


def inspect_learning_curve(rows: Sequence[Mapping[str, float]]) -> Dict[str, Any]:
    """Describe tail drift while explicitly avoiding a convergence claim."""

    if not rows:
        raise ValueError("learning-curve inspection requires progress rows")
    steps = [float(row["TotalEnvSteps"]) for row in rows]
    if any(right <= left for left, right in zip(steps, steps[1:])):
        raise ValueError("TotalEnvSteps must be strictly increasing")
    window = max(1, len(rows) // 5)
    if len(rows) < 2 * window:
        window = max(1, len(rows) // 2)
    metrics = (
        "Metrics/EpRet",
        "Metrics/SelectedAlgorithmCost",
        "Metrics/STLTriggers",
        "Metrics/STLDeadlineViolations",
        "Metrics/STLTerminalUnresolved",
        "Metrics/LagrangeMultiplier",
    )
    descriptions: Dict[str, Any] = {}
    flags = []
    for metric in metrics:
        if not all(metric in row for row in rows):
            descriptions[metric] = {"available": False}
            continue
        recent = [float(row[metric]) for row in rows[-window:]]
        previous = [float(row[metric]) for row in rows[-2 * window : -window]]
        previous_mean = float(mean(previous)) if previous else None
        recent_mean = float(mean(recent))
        change = recent_mean - previous_mean if previous_mean is not None else None
        scale = max(
            abs(previous_mean) if previous_mean is not None else 0.0,
            abs(recent_mean),
            1.0,
        )
        normalized_change = change / scale if change is not None else None
        drift = normalized_change is not None and abs(normalized_change) > 0.20
        if drift:
            flags.append(metric)
        descriptions[metric] = {
            "available": True,
            "previous_window_mean": previous_mean,
            "recent_window_mean": recent_mean,
            "recent_minus_previous": change,
            "scale_normalized_change": normalized_change,
            "descriptive_tail_drift_over_0_20": drift,
        }
    return {
        "progress_rows": len(rows),
        "tail_window_rows": window,
        "first_total_env_steps": steps[0],
        "final_total_env_steps": steps[-1],
        "metrics": descriptions,
        "tail_drift_flags": flags,
        "interpretation": "descriptive learning-curve review only; not a convergence test",
        "convergence_claim": False,
    }


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    raise ValueError(f"cannot parse Boolean CSV value: {value}")


def read_episode_csv(path: Path, *, condition: str, training_seed: int) -> List[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        raw = list(csv.DictReader(handle))
    records: List[Dict[str, Any]] = []
    for row in raw:
        record: Dict[str, Any] = dict(row)
        for field in EPISODE_FLOAT_FIELDS:
            if field in record and record[field] not in (None, ""):
                record[field] = float(record[field])
        for field in ("episode_index", "evaluation_seed"):
            record[field] = int(record[field])
        for field in ("goal_success", "online_oracle_agreement"):
            record[field] = _parse_bool(str(record[field]))
        record["condition"] = condition
        record["training_seed"] = int(training_seed)
        records.append(record)
    return records


def load_complete_matrix(
    results_root: Path,
    protocol: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Require all 15 successful final-checkpoint evaluations."""

    validate_protocol(protocol)
    training_seeds = [int(seed) for seed in protocol["matched_design"]["training_seeds"]]
    expected_eval = list(
        range(
            int(protocol["matched_design"]["evaluation_seed_start"]),
            int(protocol["matched_design"]["evaluation_seed_start"])
            + int(protocol["matched_design"]["evaluation_episodes_per_training_seed_and_condition"]),
        ),
    )
    episodes: List[Dict[str, Any]] = []
    manifests: List[Dict[str, Any]] = []
    learning: Dict[str, Dict[str, Any]] = {}
    missing = []
    for condition in CONDITION_ORDER:
        for training_seed in training_seeds:
            path = results_root / "jobs" / condition / f"seed-{training_seed}" / "manifest.json"
            if not path.is_file():
                missing.append(str(path))
                continue
            manifest = load_json_mapping(path)
            if manifest.get("status") != "success":
                missing.append(f"{path} (status={manifest.get('status')})")
                continue
            evaluation = manifest["evaluation"]
            if list(evaluation["evaluation_seeds"]) != expected_eval:
                raise ValueError(f"evaluation seeds differ from the frozen protocol: {path}")
            if not bool(evaluation["deterministic_policy"]):
                raise ValueError(f"primary evaluation is not deterministic: {path}")
            if int(evaluation["episode_count"]) != len(expected_eval):
                raise ValueError(f"evaluation episode count is incomplete: {path}")
            if not bool(evaluation["gold_oracle_agreement"]):
                raise ValueError(f"gold oracle agreement failed: {path}")
            if float(evaluation["rtamt_max_robustness_difference"]) > 1.0e-9:
                raise ValueError(f"RTAMT agreement tolerance failed: {path}")
            for record_name, record in (
                ("progress", manifest["progress"]),
                ("final checkpoint", manifest["final_checkpoint"]),
                ("evaluation summary", evaluation["summary"]),
                ("evaluation episodes", evaluation["episodes"]),
            ):
                artifact = Path(str(record["path"]))
                if not artifact.is_file() or sha256_file(artifact) != record["sha256"]:
                    raise ValueError(f"{record_name} hash mismatch: {path}")
            fixed_epoch = int(manifest["training"]["fixed_final_epoch"])
            checkpoint_name = Path(str(manifest["final_checkpoint"]["path"])).name
            if checkpoint_name != f"epoch-{fixed_epoch}.pt":
                raise ValueError(f"manifest did not select the fixed final checkpoint: {path}")
            records = read_episode_csv(
                Path(str(evaluation["episodes"]["path"])),
                condition=condition,
                training_seed=training_seed,
            )
            if [int(record["evaluation_seed"]) for record in records] != expected_eval:
                raise ValueError(f"episode CSV is not in the frozen paired-seed order: {path}")
            episodes.extend(records)
            manifests.append(manifest)
            learning[f"{condition}__seed-{training_seed}"] = inspect_learning_curve(
                read_progress_rows(Path(str(manifest["progress"]["path"]))),
            )
    if missing:
        raise ValueError(
            f"complete primary analysis requires all 15 jobs; missing {len(missing)}: {missing}",
        )
    return episodes, manifests, learning


def analyze_pilot(
    records: Sequence[Mapping[str, Any]],
    protocol: Mapping[str, Any],
    *,
    analysis_rng_seed: int,
) -> Dict[str, Any]:
    """Calculate the frozen point estimates, intervals, and NI decision."""

    validate_protocol(protocol)
    by_condition = {
        condition: [record for record in records if record["condition"] == condition]
        for condition in CONDITION_ORDER
    }
    pooled = {
        condition: aggregate_condition(values) for condition, values in by_condition.items()
    }
    training_seeds = [int(seed) for seed in protocol["matched_design"]["training_seeds"]]
    per_seed = []
    for condition in CONDITION_ORDER:
        for seed in training_seeds:
            values = [
                record
                for record in by_condition[condition]
                if int(record["training_seed"]) == seed
            ]
            per_seed.append({"condition": condition, "training_seed": seed, **aggregate_condition(values)})

    uncertainty = protocol["matched_design"]["uncertainty"]
    bootstrap = paired_hierarchical_bootstrap(
        records,
        training_seeds=training_seeds,
        replicates=int(uncertainty["replicates"]),
        rng_seed=int(analysis_rng_seed),
    )
    condition_intervals: Dict[str, Dict[str, Any]] = {}
    for condition in CONDITION_ORDER:
        condition_intervals[condition] = {
            metric: percentile_interval(bootstrap["condition_values"][condition][metric])
            for metric in ANALYSIS_CONDITION_METRICS
        }
    primary = primary_comparison(
        pooled["task_only"],
        pooled["gold_stl_cost"],
        target_relative_reduction=float(
            protocol["primary_safety_metric"]["target_relative_reduction"],
        ),
    )
    primary_intervals = {
        name: percentile_interval(values)
        for name, values in bootstrap["primary_values"].items()
    }
    goal = goal_noninferiority(
        pooled["task_only"]["goal_success_rate"],
        pooled["gold_stl_cost"]["goal_success_rate"],
        margin=float(
            protocol["goal_success_noninferiority"]["absolute_margin_percentage_points"],
        )
        / 100.0,
        confidence_interval=primary_intervals["goal_success_difference_gold_minus_task"],
    )
    return {
        "schema_version": 1,
        "protocol_id": protocol["protocol_id"],
        "analysis_rng_seed": int(analysis_rng_seed),
        "episode_record_count": len(records),
        "pooled_condition_results": pooled,
        "per_training_seed_results": per_seed,
        "condition_confidence_intervals": condition_intervals,
        "primary_comparison": primary,
        "primary_confidence_intervals": primary_intervals,
        "goal_success_noninferiority": goal,
        "bootstrap": {
            "method": bootstrap["method"],
            "replicates": bootstrap["replicates"],
            "rng_seed": bootstrap["rng_seed"],
            "primary_rows": bootstrap["primary_rows"],
        },
        "interpretation_guards": [
            "pilot_only_not_final_main_study_standard",
            "no_formal_safety_guarantee",
            "undefined_rates_and_relative_reductions_remain_NA",
        ],
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: List[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _display(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_result_table(analysis: Mapping[str, Any]) -> str:
    lines = [
        "# Stage I pilot result table",
        "",
        "| Condition | Missed/trigger | Deadline/trigger | Terminal unresolved/trigger | Goal success | Return | Native cost/episode | STL cost/episode |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITION_ORDER:
        result = analysis["pooled_condition_results"][condition]
        lines.append(
            "| "
            + " | ".join(
                [
                    condition,
                    _display(result["missed_obligation_rate_per_trigger"]),
                    _display(result["deadline_violation_rate_per_trigger"]),
                    _display(result["terminal_unresolved_rate_per_trigger"]),
                    _display(result["goal_success_rate"]),
                    _display(result["episode_return"]),
                    _display(result["native_cost_per_episode"]),
                    _display(result["stl_cost_per_episode"]),
                ],
            )
            + " |",
        )
    primary = analysis["primary_comparison"]
    goal = analysis["goal_success_noninferiority"]
    lines.extend(
        [
            "",
            "## Frozen primary comparisons",
            "",
            f"- Absolute safety reduction (task - gold): {_display(primary['absolute_reduction_task_minus_gold'])}",
            f"- Relative safety reduction: {_display(primary['relative_reduction'])}",
            f"- Goal-success difference (gold - task): {_display(goal['difference_gold_minus_task'])}",
            f"- Goal-success non-inferiority supported by 95% interval: {_display(goal['confidence_interval_supports_noninferiority'])}",
            "",
            "N/A values are intentionally not replaced by zero. This pilot does not establish a formal safety guarantee.",
        ],
    )
    return "\n".join(lines) + "\n"


def write_analysis_outputs(
    output_dir: Path,
    analysis: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    learning_curves: Mapping[str, Mapping[str, Any]],
) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = output_dir / "analysis.json"
    serializable = copy.deepcopy(dict(analysis))
    bootstrap_rows = list(serializable["bootstrap"].pop("primary_rows"))
    serializable["learning_curve_review"] = dict(learning_curves)
    with analysis_path.open("w", encoding="utf-8") as handle:
        json.dump(serializable, handle, indent=2, sort_keys=True)
        handle.write("\n")
    per_seed_path = output_dir / "per_training_seed.csv"
    episodes_path = output_dir / "episode_records.csv"
    bootstrap_path = output_dir / "bootstrap_primary.csv"
    learning_path = output_dir / "learning_curve_summary.csv"
    markdown_path = output_dir / "result_table.md"
    _write_csv(per_seed_path, analysis["per_training_seed_results"])
    _write_csv(episodes_path, records)
    _write_csv(bootstrap_path, bootstrap_rows)
    learning_rows = [
        {
            "job_id": job_id,
            "progress_rows": value["progress_rows"],
            "final_total_env_steps": value["final_total_env_steps"],
            "tail_drift_flags": ";".join(value["tail_drift_flags"]),
            "convergence_claim": value["convergence_claim"],
            "interpretation": value["interpretation"],
        }
        for job_id, value in learning_curves.items()
    ]
    _write_csv(learning_path, learning_rows)
    markdown_path.write_text(markdown_result_table(analysis), encoding="utf-8")
    return {
        "analysis": str(analysis_path),
        "per_training_seed": str(per_seed_path),
        "episode_records": str(episodes_path),
        "bootstrap_primary": str(bootstrap_path),
        "learning_curve_summary": str(learning_path),
        "markdown_table": str(markdown_path),
    }


__all__ = [
    "HierarchicalDraw",
    "aggregate_condition",
    "analyze_pilot",
    "draw_hierarchical_sample",
    "goal_noninferiority",
    "inspect_learning_curve",
    "load_complete_matrix",
    "paired_hierarchical_bootstrap",
    "percentile_interval",
    "primary_comparison",
    "write_analysis_outputs",
]
