"""Prospective budget derivation from matched D38 task-control evaluations."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple


D_WARN = 0.45
D_SAFE = 0.55
DEADLINE_STEPS = 79
BUDGET_FRACTION = 0.70


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _true(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"1", "true"}
    return bool(value)


def dense_cost_from_evaluation_row(row: Mapping[str, Any]) -> float:
    """Recompute C1 from one public, causal checkpoint-evaluation sample."""

    if _true(row["deadline_violation"]) or _true(row["terminal_unresolved"]):
        return 1.0
    if row["monitor_state"] == "inactive":
        return 0.0
    remaining_raw = row.get("remaining_steps")
    remaining = 0.0 if remaining_raw in (None, "") else float(remaining_raw)
    distance = float(row.get("distance", row.get("public_lidar_distance")))
    q_distance = min(max((D_SAFE - distance) / (D_SAFE - D_WARN), 0.0), 1.0)
    q_urgency = min(max(1.0 - remaining / DEADLINE_STEPS, 0.0), 1.0)
    return min(max(0.5 * q_distance + 0.5 * q_urgency, 0.0), 1.0)


def derive_task_control_budgets(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Derive C0/C1 limits from 3x50 pre-cost-training task controls."""

    episode_costs: Dict[Tuple[int, int], Dict[str, float]] = defaultdict(
        lambda: {"c0": 0.0, "c1": 0.0, "actions": 0.0},
    )
    for row in rows:
        if int(row["action_index"]) < 0:
            continue
        key = (int(row["training_seed"]), int(row["evaluation_seed"]))
        episode_costs[key]["c0"] += float(row["stl_cost"])
        episode_costs[key]["c1"] += dense_cost_from_evaluation_row(row)
        episode_costs[key]["actions"] += 1.0
    if len(episode_costs) != 150:
        raise ValueError(f"budget derivation requires 3x50 task-control episodes, got {len(episode_costs)}")
    if any(value["actions"] != 1000 for value in episode_costs.values()):
        raise ValueError("every task-control budget episode must contain exactly 1,000 actions")
    training_seeds = sorted({key[0] for key in episode_costs})
    if len(training_seeds) != 3:
        raise ValueError("budget derivation requires exactly three task-control training seeds")
    evaluation_seed_sets = {
        seed: {evaluation_seed for train_seed, evaluation_seed in episode_costs if train_seed == seed}
        for seed in training_seeds
    }
    if any(len(values) != 50 for values in evaluation_seed_sets.values()):
        raise ValueError("budget derivation requires exactly 50 episodes per training seed")
    if len({frozenset(values) for values in evaluation_seed_sets.values()}) != 1:
        raise ValueError("task-control budget evaluations must use the same paired seeds")
    mean_c0 = sum(value["c0"] for value in episode_costs.values()) / len(episode_costs)
    mean_c1 = sum(value["c1"] for value in episode_costs.values()) / len(episode_costs)
    per_seed: Dict[str, Dict[str, float]] = {}
    for seed in training_seeds:
        values = [value for key, value in episode_costs.items() if key[0] == seed]
        per_seed[str(seed)] = {
            "episode_count": len(values),
            "mean_c0_events_per_episode": sum(value["c0"] for value in values) / len(values),
            "mean_c1_surrogate_mass_per_episode": sum(value["c1"] for value in values) / len(values),
        }
    return {
        "task_control_episode_count": len(episode_costs),
        "training_seeds": training_seeds,
        "actions_per_episode": 1000,
        "paired_evaluation_seeds": sorted(evaluation_seed_sets[training_seeds[0]]),
        "budget_fraction": BUDGET_FRACTION,
        "task_control_mean": {
            "c0_events_per_episode": mean_c0,
            "c1_surrogate_mass_per_episode": mean_c1,
        },
        "diagnostic_cost_limit": {
            "c0_events_per_episode": BUDGET_FRACTION * mean_c0,
            "c1_surrogate_mass_per_episode": BUDGET_FRACTION * mean_c1,
        },
        "per_training_seed": per_seed,
        "unit_guard": "C0 and C1 limits have different units and are never copied",
    }


__all__ = [
    "derive_task_control_budgets",
    "dense_cost_from_evaluation_row",
    "sha256_file",
]
