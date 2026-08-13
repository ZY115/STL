#!/usr/bin/env python3
"""Plot the fixed route request and common Gold evaluation geometry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_ROOT = REPOSITORY_ROOT / "src" / "safety_stl"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from fixed_route import load_fixed_route_scenario  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=REPOSITORY_ROOT / "configs" / "fixed_route_v1" / "scenario.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "results" / "fixed_route_v1" / "scenario_plan.png",
    )
    options = parser.parse_args()
    scenario = load_fixed_route_scenario(options.config)

    figure, axis = plt.subplots(figsize=(7.2, 7.2))
    for index, hazard in enumerate(scenario.hazard_locations):
        axis.add_patch(
            Circle(
                hazard,
                scenario.d_safe,
                fill=False,
                edgecolor="#2ca02c",
                linestyle=":",
                linewidth=1.1,
            ),
        )
        axis.add_patch(
            Circle(
                hazard,
                scenario.d_warn,
                fill=False,
                edgecolor="#d62728",
                linestyle="--",
                linewidth=1.1,
            ),
        )
        axis.add_patch(
            Circle(
                hazard,
                scenario.hazard_radius,
                facecolor="#5b8db8",
                edgecolor="#24577e",
                alpha=0.55,
            ),
        )
        axis.text(hazard[0], hazard[1], f"H{index + 1}", ha="center", va="center", fontsize=7)

    for vase in scenario.vase_locations:
        axis.scatter(*vase, marker="s", s=45, color="#aaaaaa", edgecolor="#555555", zorder=4)
        axis.text(vase[0] + 0.05, vase[1] - 0.08, "Vase", fontsize=8, color="#555555")

    waypoints = (scenario.agent_start, *scenario.goal_sequence)
    for start, end in zip(waypoints, waypoints[1:]):
        axis.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops={
                "arrowstyle": "->",
                "color": "#666666",
                "linestyle": "--",
                "linewidth": 1.4,
            },
        )
    axis.scatter(
        *scenario.agent_start,
        marker="o",
        s=80,
        facecolor="white",
        edgecolor="black",
        zorder=5,
    )
    axis.text(scenario.agent_start[0] + 0.05, scenario.agent_start[1] - 0.08, "Start", fontsize=9)
    for index, goal in enumerate(scenario.goal_sequence):
        axis.scatter(
            *goal,
            marker="*",
            s=120,
            color="#1f8f4d",
            edgecolor="black",
            linewidth=0.4,
            zorder=5,
        )
        axis.text(goal[0] + 0.05, goal[1] + 0.05, f"G{index + 1}", fontsize=9)

    axis.set_xlim(-1.55, 1.55)
    axis.set_ylim(-1.55, 1.55)
    axis.set_aspect("equal")
    axis.set_xlabel("x")
    axis.set_ylabel("y")
    axis.grid(alpha=0.15)
    axis.set_title("Fixed route request; the policy trajectory remains learned")
    figure.text(
        0.5,
        0.015,
        "Blue: physical hazard r=0.20   Red dashed: warning r=0.25   Green dotted: safe r=0.28",
        ha="center",
        fontsize=9,
    )
    figure.tight_layout(rect=(0.0, 0.04, 1.0, 1.0))
    options.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(options.output, dpi=190, bbox_inches="tight")
    plt.close(figure)
    print(options.output)


if __name__ == "__main__":
    main()
