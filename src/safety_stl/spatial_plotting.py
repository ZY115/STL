"""Deterministic figures for the Stage I spatial replay package."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np

from safety_stl.spatial_diagnosis import (
    CONDITIONS,
    EVENT_DENSITIES,
    HAZARD_RADIUS,
    MAP_HIGH,
    MAP_LOW,
    SAFE_RADIUS,
    WARNING_RADIUS,
    verify_replay_artifacts,
)


CONDITION_LABELS = {
    "task_only": "Task only",
    "native_cost": "Native cost",
    "gold_stl_cost": "Gold STL cost",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"expected JSON mapping: {path}")
    return dict(value)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _float(row: Mapping[str, str], field: str) -> float:
    return float(row[field])


def _true(row: Mapping[str, str], field: str) -> bool:
    return str(row[field]).lower() == "true"


def _goal_context_metrics(path: Path, window_steps: int = 20) -> Dict[str, Any]:
    """Compare missed-event proximity to goal changes against time exposure."""

    totals: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {
            "action_steps": 0,
            "action_steps_near_goal": 0,
            "deadline_violations": 0,
            "deadline_violations_near_goal": 0,
            "terminal_unresolved": 0,
            "terminal_unresolved_near_goal": 0,
        },
    )

    def add_episode(rows: Sequence[Mapping[str, str]]) -> None:
        if not rows:
            return
        condition = str(rows[0]["condition"])
        goal_steps = [int(row["sample_index"]) for row in rows if _true(row, "goal_met")]

        def near_goal(step: int) -> bool:
            return bool(goal_steps) and min(abs(step - goal) for goal in goal_steps) <= window_steps

        action_rows = [row for row in rows if int(row["action_index"]) >= 0]
        totals[condition]["action_steps"] += len(action_rows)
        totals[condition]["action_steps_near_goal"] += sum(
            near_goal(int(row["sample_index"])) for row in action_rows
        )
        for field, target in (
            ("deadline_violation", "deadline_violations"),
            ("terminal_unresolved", "terminal_unresolved"),
        ):
            event_rows = [row for row in action_rows if _true(row, field)]
            totals[condition][target] += len(event_rows)
            totals[condition][f"{target}_near_goal"] += sum(
                near_goal(int(row["sample_index"])) for row in event_rows
            )

    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        previous_key = None
        episode_rows: List[Mapping[str, str]] = []
        for row in reader:
            key = (row["condition"], row["training_seed"], row["evaluation_seed"])
            if previous_key is not None and key != previous_key:
                add_episode(episode_rows)
                episode_rows = []
            episode_rows.append(row)
            previous_key = key
        add_episode(episode_rows)

    output: Dict[str, Any] = {}
    for condition in CONDITIONS:
        values = dict(totals[condition])
        missed = values["deadline_violations"] + values["terminal_unresolved"]
        missed_near = (
            values["deadline_violations_near_goal"]
            + values["terminal_unresolved_near_goal"]
        )
        exposure = values["action_steps_near_goal"] / values["action_steps"]
        missed_fraction = missed_near / missed
        values.update(
            {
                "goal_context_window_steps": window_steps,
                "action_step_near_goal_fraction": exposure,
                "missed_obligation_near_goal_fraction": missed_fraction,
                "missed_event_to_exposure_ratio": (
                    missed_fraction / exposure if exposure else None
                ),
            },
        )
        output[condition] = values
    return output


def _hazards(rows: Sequence[Mapping[str, str]]) -> np.ndarray:
    first = rows[0]
    return np.asarray(
        [[_float(first, f"hazard_{index}_x"), _float(first, f"hazard_{index}_y")] for index in range(8)],
        dtype=np.float64,
    )


def plot_top_down(
    rows: Sequence[Mapping[str, str]],
    cases: Sequence[Mapping[str, Any]],
    path: Path,
) -> None:
    """Create the required three-case by three-condition top-down panel."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.colors import Normalize
    from matplotlib.patches import Circle, Rectangle

    figure, axes = plt.subplots(3, 3, figsize=(14, 14), sharex=True, sharey=True)
    for row_index, case in enumerate(cases):
        for column_index, condition in enumerate(CONDITIONS):
            axis = axes[row_index, column_index]
            selected = [
                row
                for row in rows
                if row["case_id"] == str(case["case_id"]) and row["condition"] == condition
            ]
            if not selected:
                raise ValueError(f"missing representative geometry: {case['case_id']} / {condition}")
            hazards = _hazards(selected)
            axis.add_patch(
                Rectangle(
                    (MAP_LOW, MAP_LOW),
                    MAP_HIGH - MAP_LOW,
                    MAP_HIGH - MAP_LOW,
                    fill=False,
                    edgecolor="#333333",
                    linewidth=1.0,
                ),
            )
            for hazard_x, hazard_y in hazards:
                axis.add_patch(
                    Circle(
                        (hazard_x, hazard_y),
                        SAFE_RADIUS,
                        fill=False,
                        edgecolor="#2ca02c",
                        linestyle=":",
                        linewidth=0.65,
                        alpha=0.48,
                    ),
                )
                axis.add_patch(
                    Circle(
                        (hazard_x, hazard_y),
                        WARNING_RADIUS,
                        fill=False,
                        edgecolor="#d62728",
                        linestyle="--",
                        linewidth=0.65,
                        alpha=0.58,
                    ),
                )
                axis.add_patch(
                    Circle(
                        (hazard_x, hazard_y),
                        HAZARD_RADIUS,
                        facecolor="#4c78a8",
                        edgecolor="#214761",
                        linewidth=0.6,
                        alpha=0.25,
                    ),
                )
            sample_indices = np.asarray([int(row["sample_index"]) for row in selected])
            normalization = Normalize(vmin=float(sample_indices.min()), vmax=float(sample_indices.max()))
            for goal_id in sorted({int(row["goal_id"]) for row in selected}):
                goal_rows = [row for row in selected if int(row["goal_id"]) == goal_id]
                coordinates = np.asarray(
                    [[_float(row, "agent_x"), _float(row, "agent_y")] for row in goal_rows],
                    dtype=np.float64,
                )
                if len(coordinates) >= 2:
                    segments = np.stack([coordinates[:-1], coordinates[1:]], axis=1)
                    line = LineCollection(
                        segments,
                        cmap="viridis",
                        norm=normalization,
                        linewidth=1.25,
                        alpha=0.9,
                    )
                    line.set_array(np.asarray([int(row["sample_index"]) for row in goal_rows[:-1]]))
                    axis.add_collection(line)
                goal_x = _float(goal_rows[0], "goal_x")
                goal_y = _float(goal_rows[0], "goal_y")
                axis.scatter(goal_x, goal_y, marker="*", s=30, color="#2ca02c", alpha=0.7)
            axis.scatter(
                _float(selected[0], "agent_x"),
                _float(selected[0], "agent_y"),
                marker="o",
                s=35,
                facecolor="white",
                edgecolor="black",
                linewidth=1.0,
                zorder=5,
            )
            event_styles: Tuple[Tuple[str, str, str, int], ...] = (
                ("warning_trigger", "v", "#9467bd", 26),
                ("recovery", "o", "#2ca02c", 25),
                ("deadline_violation", "X", "#d62728", 34),
                ("terminal_unresolved", "P", "#111111", 34),
            )
            for field, marker, color, size in event_styles:
                event_rows = [row for row in selected if _true(row, field)]
                if event_rows:
                    axis.scatter(
                        [_float(row, "agent_x") for row in event_rows],
                        [_float(row, "agent_y") for row in event_rows],
                        marker=marker,
                        s=size,
                        color=color,
                        linewidth=0.5,
                        zorder=6,
                    )
            terminal_rows = [row for row in selected if _true(row, "terminated") or _true(row, "truncated")]
            axis.scatter(
                [_float(row, "agent_x") for row in terminal_rows],
                [_float(row, "agent_y") for row in terminal_rows],
                marker="s",
                s=30,
                facecolor="none",
                edgecolor="black",
                linewidth=0.9,
                zorder=7,
            )
            axis.set_xlim(MAP_LOW - 0.05, MAP_HIGH + 0.05)
            axis.set_ylim(MAP_LOW - 0.05, MAP_HIGH + 0.05)
            axis.set_aspect("equal")
            axis.grid(alpha=0.12)
            title = CONDITION_LABELS[condition]
            if row_index == 0:
                axis.set_title(title)
            if column_index == 0:
                axis.set_ylabel(f"{case['case_id']}\ny")
            if row_index == len(cases) - 1:
                axis.set_xlabel("x")
    figure.suptitle(
        "Frozen Stage I policies: true top-down trajectories\n"
        "blue disks=physical hazards; dashed/dotted circles=common Gold evaluation overlay",
        y=0.995,
    )
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.965))
    figure.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(figure)


def plot_event_density(density_path: Path, output_path: Path) -> None:
    """Plot condition-wise occupancy and event densities from compact counts."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    package = np.load(density_path, allow_pickle=False)
    counts = package["counts"]
    conditions = [str(value) for value in package["conditions"]]
    event_types = [str(value) for value in package["event_types"]]
    if conditions != list(CONDITIONS) or event_types != list(EVENT_DENSITIES):
        raise ValueError("density axes do not match the frozen replay contract")
    figure, axes = plt.subplots(3, 4, figsize=(15, 10), sharex=True, sharey=True)
    for condition_index, condition in enumerate(CONDITIONS):
        for event_index, event_type in enumerate(EVENT_DENSITIES):
            axis = axes[condition_index, event_index]
            transformed = np.log1p(counts[condition_index, event_index])
            image = axis.imshow(
                transformed,
                origin="lower",
                extent=(MAP_LOW, MAP_HIGH, MAP_LOW, MAP_HIGH),
                cmap="magma",
                interpolation="nearest",
                aspect="equal",
            )
            axis.set_xlim(MAP_LOW, MAP_HIGH)
            axis.set_ylim(MAP_LOW, MAP_HIGH)
            if condition_index == 0:
                axis.set_title(event_type.replace("_", " ").title())
            if event_index == 0:
                axis.set_ylabel(f"{CONDITION_LABELS[condition]}\ny")
            if condition_index == len(CONDITIONS) - 1:
                axis.set_xlabel("x")
            figure.colorbar(image, ax=axis, fraction=0.046, pad=0.03, label="log(1 + count)")
    figure.suptitle("Aggregate spatial occupancy and Gold-event density (15 checkpoints, 1,500 episodes)")
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    figure.savefig(output_path, dpi=190, bbox_inches="tight")
    plt.close(figure)


def plot_layout_feasibility(layout_rows: Sequence[Mapping[str, str]], path: Path) -> None:
    """Plot the per-layout navigable fraction for the three declared radii."""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fields = (
        "outside_physical_radius_fraction",
        "outside_warning_radius_fraction",
        "outside_safe_radius_fraction",
    )
    labels = ("Outside physical 0.20", "Outside warning 0.45", "Outside safe 0.55")
    values = [np.asarray([_float(row, field) for row in layout_rows]) * 100.0 for field in fields]
    figure, axis = plt.subplots(figsize=(9, 5.5))
    box = axis.boxplot(values, labels=labels, patch_artist=True, showmeans=True)
    colors = ("#4c78a8", "#d62728", "#2ca02c")
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
    for index, data in enumerate(values, start=1):
        x_positions = np.linspace(index - 0.16, index + 0.16, len(data))
        axis.scatter(x_positions, np.sort(data), s=7, color=colors[index - 1], alpha=0.35)
        axis.text(index, float(np.mean(data)) + 1.1, f"mean {np.mean(data):.1f}%", ha="center")
    axis.set_ylabel("Sampled map outside every hazard-centered disk (%)")
    axis.set_ylim(0, 102)
    axis.grid(axis="y", alpha=0.25)
    axis.set_title("Layout feasibility across the 100 fixed evaluation layouts")
    figure.tight_layout()
    figure.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(figure)


def build_spatial_figures(output_root: Path) -> Dict[str, Any]:
    """Verify replay hashes, generate all required figures and record hashes."""

    replay_manifest = verify_replay_artifacts(output_root)
    summary = _load_json(output_root / "summary.json")
    representative_path = output_root / "representative_geometry.csv"
    density_path = output_root / "spatial_density_counts.npz"
    layout_path = output_root / "layout_feasibility.csv"
    rows = _read_csv(representative_path)
    layout_rows = _read_csv(layout_path)
    context_path = output_root / "goal_context_metrics.json"
    _write_json(
        context_path,
        {
            "schema_version": 1,
            "scope": "descriptive proximity diagnostic; not a causal estimate",
            "conditions": _goal_context_metrics(output_root / "full_geometry.csv.gz"),
        },
    )
    figures = {
        "paired_top_down_trajectories.png": output_root / "paired_top_down_trajectories.png",
        "event_spatial_density.png": output_root / "event_spatial_density.png",
        "layout_feasibility.png": output_root / "layout_feasibility.png",
    }
    plot_top_down(rows, summary["cases"], figures["paired_top_down_trajectories.png"])
    plot_event_density(density_path, figures["event_spatial_density.png"])
    plot_layout_feasibility(layout_rows, figures["layout_feasibility.png"])
    figure_manifest = {
        "schema_version": 1,
        "replay_manifest_sha256": _sha256(output_root / "replay_manifest.json"),
        "verified_compact_input_count": len(replay_manifest["compact_artifacts"]),
        "figures": {
            name: {"path": str(path), "sha256": _sha256(path), "bytes": path.stat().st_size}
            for name, path in figures.items()
        },
        "derived_metrics": {
            context_path.name: {
                "path": str(context_path),
                "sha256": _sha256(context_path),
                "bytes": context_path.stat().st_size,
            },
        },
    }
    _write_json(output_root / "figures_manifest.json", figure_manifest)
    return figure_manifest


__all__ = [
    "build_spatial_figures",
    "plot_event_density",
    "plot_layout_feasibility",
    "plot_top_down",
]
