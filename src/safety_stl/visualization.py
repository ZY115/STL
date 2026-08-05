"""Runnable visualization and artifact logging for the Stage I monitor.

This module is deliberately an evaluation/demo surface.  Its scripted controller
uses privileged simulator geometry to make a warning episode easy to observe; it
is not an RL policy and its rollouts are not experimental safety results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import imageio.v2 as imageio
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

from safety_stl.monitor import BoundedRecoveryMonitor, MonitorOutput
from safety_stl.signals import distance_from_observation


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "stage1_rule.yaml"
DEFAULT_RESULTS_ROOT = Path(__file__).resolve().parents[2] / "results" / "visualization"
MONITOR_FIELDS = tuple(MonitorOutput.__dataclass_fields__)
LOG_FIELDS = (
    "action_index",
    "seed",
    "policy",
    "controller_phase",
    "action_forward",
    "action_turn",
    "reward",
    "native_cost",
    "cost_hazards_info",
    "goal_met",
    "cumulative_reward",
    "cumulative_native_cost",
    "cumulative_stl_cost",
) + MONITOR_FIELDS


@dataclass(frozen=True)
class DemoOptions:
    """Validated runtime choices for one visualization rollout."""

    config_path: Path
    output_dir: Path
    render: str
    policy: str
    seed: int
    max_steps: int
    width: int
    height: int
    fps: int
    camera_name: str
    status_interval: int


@dataclass
class RunTotals:
    """Cumulative quantities kept separate throughout one rollout."""

    reward: float = 0.0
    native_cost: float = 0.0
    stl_cost: int = 0
    minimum_distance: float = math.inf
    goal_events: int = 0


class ScriptedApproachEscapeController:
    """Deterministic visual-demo controller copied from the calibration protocol.

    Hazard positions are privileged and are used only to produce a legible
    approach/recovery sequence.  They never enter the Stage I distance signal or
    monitor.
    """

    def __init__(self, task: Any) -> None:
        agent_xy = np.asarray(task.agent.pos, dtype=np.float64)[:2]
        hazards_xy = np.asarray(task.hazards.pos, dtype=np.float64)[:, :2]
        self.target_hazard_index = int(
            np.argmin(np.linalg.norm(hazards_xy - agent_xy, axis=1)),
        )
        self.target_position = hazards_xy[self.target_hazard_index].copy()
        self.phase = "approach"
        self.reached_approach_target = False

    @staticmethod
    def _steering_action(
        task: Any,
        target_xy: np.ndarray,
        *,
        forward_action: float,
    ) -> np.ndarray:
        agent_xy = np.asarray(task.agent.pos, dtype=np.float64)[:2]
        vector_world = np.asarray(target_xy, dtype=np.float64)[:2] - agent_xy
        vector_ego = np.asarray([vector_world[0], vector_world[1], 0.0]) @ np.asarray(
            task.agent.mat,
            dtype=np.float64,
        )
        heading_error = math.atan2(float(vector_ego[1]), float(vector_ego[0]))
        turn = float(np.clip(2.5 * heading_error, -1.0, 1.0))
        forward = forward_action if abs(heading_error) < 0.10 else 0.0
        return np.asarray([forward, turn], dtype=np.float64)

    def action(self, task: Any) -> np.ndarray:
        """Advance the controller state and return one environment action."""

        agent_xy = np.asarray(task.agent.pos, dtype=np.float64)[:2]
        target_distance = float(np.linalg.norm(agent_xy - self.target_position))
        velocity_world = np.asarray(task.agent.vel, dtype=np.float64)
        velocity_ego = velocity_world @ np.asarray(task.agent.mat, dtype=np.float64)

        if self.phase == "approach" and target_distance <= 0.45:
            self.phase = "decelerate"
        if self.phase == "decelerate" and float(velocity_ego[0]) <= 0.01:
            self.phase = "final_approach"
        if self.phase == "final_approach" and target_distance <= 0.28:
            self.phase = "escape"
            self.reached_approach_target = True

        if self.phase == "approach":
            forward = 0.20 if target_distance > 0.80 else 0.15
            return self._steering_action(task, self.target_position, forward_action=forward)
        if self.phase == "decelerate":
            return np.asarray([-1.0, 0.0], dtype=np.float64)
        if self.phase == "final_approach":
            return self._steering_action(task, self.target_position, forward_action=0.05)
        return np.asarray([-1.0, 0.0], dtype=np.float64)

    def should_stop(self, public_distance: float, monitor_output: MonitorOutput) -> bool:
        """Stop after the visible warning episode has safely closed."""

        return (
            self.phase == "escape"
            and self.reached_approach_target
            and public_distance > 0.9
            and monitor_output.stl_status == "inactive"
        )


def installed_version(distribution: str) -> str:
    """Return an installed distribution version for the run summary."""

    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "not-installed"


def sha256_file(path: Path) -> str:
    """Hash one generated artifact for the durable run summary."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_rule_config(path: Path) -> Dict[str, Any]:
    """Load the fixed Stage I rule and validate its monitor parameters."""

    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, Mapping):
        raise ValueError("rule configuration must be a mapping")
    required = {"environment_id", "lidar_range", "d_warn", "d_safe", "deadline_steps"}
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"rule configuration is missing: {', '.join(missing)}")
    BoundedRecoveryMonitor(
        float(config["d_warn"]),
        float(config["d_safe"]),
        int(config["deadline_steps"]),
    )
    return dict(config)


def event_label(output: MonitorOutput) -> str:
    """Return the most important event at a monitor sample."""

    if output.stl_terminal_unresolved:
        return "TERMINAL UNRESOLVED"
    if output.stl_deadline_violation:
        return "DEADLINE VIOLATION"
    if output.stl_late_recovery:
        return "LATE RECOVERY"
    if output.stl_recovery:
        return "RECOVERY"
    if output.stl_warning_trigger:
        return "WARNING TRIGGER"
    return "-"


def overlay_rows(
    output: MonitorOutput,
    totals: RunTotals,
    *,
    policy: str,
    phase: str,
) -> List[Tuple[str, str]]:
    """Build the shared native-viewer and video-overlay text."""

    remaining = "-" if output.stl_remaining_steps is None else str(output.stl_remaining_steps)
    return [
        ("Policy", policy),
        ("Phase", phase),
        ("Step", str(output.sample_index)),
        ("Distance d_t", f"{output.stl_distance:.3f}"),
        ("Monitor", output.stl_status.upper()),
        ("Remaining", remaining),
        ("Event", event_label(output)),
        ("Reward total", f"{totals.reward:.3f}"),
        ("Native cost", f"{totals.native_cost:.0f}"),
        ("STL cost", str(totals.stl_cost)),
    ]


def annotate_frame(
    frame: np.ndarray,
    output: MonitorOutput,
    totals: RunTotals,
    *,
    policy: str,
    phase: str,
    d_warn: float,
    d_safe: float,
) -> np.ndarray:
    """Append a compact, deterministic monitor panel to one RGB frame."""

    pixels = np.asarray(frame, dtype=np.uint8)
    if pixels.ndim != 3 or pixels.shape[2] != 3:
        raise ValueError("rendered frame must have shape (height, width, 3)")
    source = Image.fromarray(pixels, mode="RGB")
    panel_width = 340
    canvas_height = max(source.height, 390)
    canvas = Image.new("RGB", (source.width + panel_width, canvas_height), (20, 24, 31))
    canvas.paste(source, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    x = source.width + 18
    y = 16
    draw.text((x, y), "STAGE I  |  BOUNDED RECOVERY", fill=(235, 240, 248), font=font)
    y += 28
    for label, value in overlay_rows(output, totals, policy=policy, phase=phase):
        color = (220, 225, 232)
        if label == "Monitor":
            color = {
                "inactive": (105, 210, 145),
                "pending": (250, 195, 80),
                "overdue": (250, 95, 95),
            }[output.stl_status]
        if label == "Event" and value != "-":
            color = (250, 195, 80) if "VIOLATION" not in value else (250, 95, 95)
        draw.text((x, y), f"{label:<15} {value}", fill=color, font=font)
        y += 22

    y += 8
    draw.text((x, y), "Distance thresholds", fill=(180, 190, 205), font=font)
    y += 18
    bar_left, bar_right = x, x + 285
    bar_top, bar_bottom = y, y + 14
    draw.rectangle((bar_left, bar_top, bar_right, bar_bottom), fill=(55, 63, 76))
    scale_max = 1.0
    for distance, color in (
        (d_warn, (250, 95, 95)),
        (d_safe, (105, 210, 145)),
        (min(output.stl_distance, scale_max), (235, 240, 248)),
    ):
        marker_x = bar_left + int((distance / scale_max) * (bar_right - bar_left))
        marker_x = max(bar_left, min(bar_right, marker_x))
        draw.line((marker_x, bar_top - 3, marker_x, bar_bottom + 3), fill=color, width=2)
    y += 22
    draw.text(
        (x, y),
        f"warn < {d_warn:.2f}    safe >= {d_safe:.2f}",
        fill=(180, 190, 205),
        font=font,
    )
    y += 28
    draw.text(
        (x, y),
        "Scripted mode uses simulator geometry",
        fill=(145, 155, 170),
        font=font,
    )
    draw.text(
        (x, y + 16),
        "for demonstration only; monitor uses lidar.",
        fill=(145, 155, 170),
        font=font,
    )
    return np.asarray(canvas)


class DemoRenderer:
    """Native MuJoCo live viewer or annotated MP4 renderer."""

    def __init__(self, options: DemoOptions, config: Mapping[str, Any]) -> None:
        self.options = options
        self.config = config
        self.video_path: Optional[Path] = None
        self._writer: Any = None
        self._human_initialized = False
        if options.render == "video":
            self.video_path = options.output_dir / "stage1_demo.mp4"
            self._writer = imageio.get_writer(
                self.video_path,
                fps=options.fps,
                codec="libx264",
                pixelformat="yuv420p",
                macro_block_size=None,
            )

    def render(
        self,
        environment: Any,
        output: MonitorOutput,
        totals: RunTotals,
        *,
        policy: str,
        phase: str,
    ) -> None:
        """Render one monitor sample with matching simulator state."""

        if self.options.render == "none":
            return
        builder = environment.unwrapped
        task = builder.task
        if self.options.render == "human":
            import glfw
            import mujoco

            viewer = task._get_viewer("human")  # pinned Safety-Gymnasium 1.0.0 API
            if not self._human_initialized:
                viewer.make_context_current()
                glfw.swap_interval(0)
                self._human_initialized = True
            render_started = time.monotonic()
            rows = overlay_rows(output, totals, policy=policy, phase=phase)
            viewer.add_overlay(
                mujoco.mjtGridPos.mjGRID_TOPRIGHT,
                "STL MONITOR\n" + "\n".join(label for label, _ in rows),
                "\n" + "\n".join(value for _, value in rows),
            )
            task.render(
                width=self.options.width,
                height=self.options.height,
                mode="human",
                cost=builder.cost,
            )
            remaining_frame_time = (1.0 / self.options.fps) - (
                time.monotonic() - render_started
            )
            if remaining_frame_time > 0:
                time.sleep(remaining_frame_time)
            return

        frame = task.render(
            width=self.options.width,
            height=self.options.height,
            mode="rgb_array",
            camera_name=self.options.camera_name,
            cost=builder.cost,
        )
        annotated = annotate_frame(
            frame,
            output,
            totals,
            policy=policy,
            phase=phase,
            d_warn=float(self.config["d_warn"]),
            d_safe=float(self.config["d_safe"]),
        )
        self._writer.append_data(np.ascontiguousarray(annotated))

    def close(self, environment: Any) -> None:
        """Flush video output and close private render contexts if created."""

        if self._writer is not None:
            self._writer.close()
            self._writer = None
        task = environment.unwrapped.task
        for viewer in list(task._viewers.values()):  # pinned Safety-Gymnasium 1.0.0 API
            try:
                if hasattr(viewer, "window"):
                    viewer.free()
                    viewer.window = None
                    # Gymnasium 0.28.1's WindowViewer destructor otherwise
                    # attempts a second GLFW destroy during interpreter exit.
                    viewer.__class__.__del__ = lambda instance: None
                else:
                    viewer.close()
            except (AttributeError, RuntimeError):
                pass
        task._viewers.clear()
        task.viewer = None


def build_log_row(
    *,
    output: MonitorOutput,
    action_index: Optional[int],
    action: Optional[np.ndarray],
    seed: int,
    policy: str,
    phase: str,
    reward: Optional[float],
    native_cost: Optional[float],
    info: Mapping[str, Any],
    totals: RunTotals,
) -> Dict[str, Any]:
    """Build one CSV row while preserving reward/native/STL separation."""

    if action is None:
        action_forward, action_turn = None, None
    else:
        action_forward, action_turn = float(action[0]), float(action[1])
    row: Dict[str, Any] = {
        "action_index": action_index,
        "seed": seed,
        "policy": policy,
        "controller_phase": phase,
        "action_forward": action_forward,
        "action_turn": action_turn,
        "reward": reward,
        "native_cost": native_cost,
        "cost_hazards_info": info.get("cost_hazards"),
        "goal_met": bool(info.get("goal_met", False)),
        "cumulative_reward": totals.reward,
        "cumulative_native_cost": totals.native_cost,
        "cumulative_stl_cost": totals.stl_cost,
    }
    row.update(output.as_dict())
    return row


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write one stable trajectory table."""

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def should_print_status(output: MonitorOutput, interval: int) -> bool:
    """Keep terminal output readable while always showing monitor events."""

    return output.sample_index % interval == 0 or event_label(output) != "-"


def print_status(output: MonitorOutput, totals: RunTotals, phase: str) -> None:
    """Print one compact status line for headless and recorded runs."""

    remaining = "-" if output.stl_remaining_steps is None else str(output.stl_remaining_steps)
    print(
        f"step={output.sample_index:4d} phase={phase:14s} d_t={output.stl_distance:.3f} "
        f"status={output.stl_status:8s} remaining={remaining:>2s} "
        f"event={event_label(output):19s} reward={totals.reward:.3f} "
        f"native_cost={totals.native_cost:.0f} stl_cost={totals.stl_cost}",
        flush=True,
    )


def run_demo(options: DemoOptions) -> Dict[str, Any]:
    """Run one environment/monitor visualization and save reproducible artifacts."""

    import safety_gymnasium

    config = load_rule_config(options.config_path)
    options.output_dir.mkdir(parents=True, exist_ok=True)
    environment = safety_gymnasium.make(str(config["environment_id"]))
    renderer = DemoRenderer(options, config)
    rows: List[Dict[str, Any]] = []
    totals = RunTotals()
    rng = np.random.default_rng(options.seed)
    exit_reason = "max_steps"
    try:
        observation, info = environment.reset(seed=options.seed)
        task = environment.unwrapped.task
        observation_schema = task.obs_info.obs_space_dict
        monitor = BoundedRecoveryMonitor(
            float(config["d_warn"]),
            float(config["d_safe"]),
            int(config["deadline_steps"]),
        )
        distance = distance_from_observation(
            observation,
            observation_schema,
            lidar_range=float(config["lidar_range"]),
        )
        output = monitor.reset(distance)
        totals.minimum_distance = distance
        controller = (
            ScriptedApproachEscapeController(task) if options.policy == "scripted" else None
        )
        phase = controller.phase if controller is not None else "random"
        rows.append(
            build_log_row(
                output=output,
                action_index=None,
                action=None,
                seed=options.seed,
                policy=options.policy,
                phase=phase,
                reward=None,
                native_cost=None,
                info=info,
                totals=totals,
            ),
        )
        renderer.render(
            environment,
            output,
            totals,
            policy=options.policy,
            phase=phase,
        )
        if should_print_status(output, options.status_interval):
            print_status(output, totals, phase)

        for action_index in range(options.max_steps):
            if controller is None:
                action = rng.uniform(environment.action_space.low, environment.action_space.high)
                phase = "random"
            else:
                action = controller.action(task)
                phase = controller.phase
            observation, reward, native_cost, terminated, truncated, info = environment.step(action)
            totals.reward += float(reward)
            totals.native_cost += float(native_cost)
            totals.goal_events += int(bool(info.get("goal_met", False)))
            distance = distance_from_observation(
                observation,
                observation_schema,
                lidar_range=float(config["lidar_range"]),
            )
            output = monitor.step(
                distance,
                terminated=bool(terminated),
                truncated=bool(truncated),
            )
            totals.stl_cost += output.stl_cost
            totals.minimum_distance = min(totals.minimum_distance, distance)
            rows.append(
                build_log_row(
                    output=output,
                    action_index=action_index,
                    action=action,
                    seed=options.seed,
                    policy=options.policy,
                    phase=phase,
                    reward=float(reward),
                    native_cost=float(native_cost),
                    info=info,
                    totals=totals,
                ),
            )
            renderer.render(
                environment,
                output,
                totals,
                policy=options.policy,
                phase=phase,
            )
            if should_print_status(output, options.status_interval):
                print_status(output, totals, phase)

            if terminated or truncated:
                exit_reason = "terminated" if terminated else "truncated"
                break
            if controller is not None and controller.should_stop(distance, output):
                exit_reason = "scripted_recovery_complete"
                break
    finally:
        renderer.close(environment)
        environment.close()

    trajectory_path = options.output_dir / "trajectory.csv"
    write_csv(trajectory_path, rows)
    final_output = output
    summary = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "environment_id": config["environment_id"],
        "seed": options.seed,
        "policy": options.policy,
        "scripted_policy_uses_privileged_geometry": options.policy == "scripted",
        "render_mode": options.render,
        "render_backend": os.environ.get("MUJOCO_GL", "unset"),
        "camera_name": options.camera_name if options.render == "video" else None,
        "rule": {
            "d_warn": float(config["d_warn"]),
            "d_safe": float(config["d_safe"]),
            "deadline_steps": int(config["deadline_steps"]),
            "distance_source": config.get("distance_source"),
        },
        "samples": len(rows),
        "actions": len(rows) - 1,
        "exit_reason": exit_reason,
        "terminated": final_output.terminated,
        "truncated": final_output.truncated,
        "collector_cutoff_pending": exit_reason == "max_steps"
        and final_output.stl_status == "pending",
        "episode_return": totals.reward,
        "native_cost_total": totals.native_cost,
        "stl_cost_total": totals.stl_cost,
        "goal_events": totals.goal_events,
        "minimum_public_distance": totals.minimum_distance,
        "monitor": {
            "final_status": final_output.stl_status,
            "trigger_count": monitor.trigger_count,
            "recovery_count": monitor.recovery_count,
            "deadline_violation_count": monitor.deadline_violation_count,
            "terminal_unresolved_count": monitor.unresolved_count,
        },
        "artifacts": {
            "trajectory_csv": trajectory_path.name,
            "trajectory_csv_sha256": sha256_file(trajectory_path),
            "video": None if renderer.video_path is None else renderer.video_path.name,
            "video_sha256": None
            if renderer.video_path is None
            else sha256_file(renderer.video_path),
        },
        "software": {
            "python": platform.python_version(),
            "numpy": installed_version("numpy"),
            "safety-gymnasium": installed_version("safety-gymnasium"),
            "gymnasium": installed_version("gymnasium"),
            "mujoco": installed_version("mujoco"),
            "pillow": installed_version("Pillow"),
            "imageio": installed_version("imageio"),
            "imageio-ffmpeg": installed_version("imageio-ffmpeg"),
        },
    }
    summary_path = options.output_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"trajectory: {trajectory_path}")
    if renderer.video_path is not None:
        print(f"video:      {renderer.video_path}")
    print(f"summary:    {summary_path}")
    return summary


def default_output_directory() -> Path:
    """Return a collision-resistant local results directory."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return DEFAULT_RESULTS_ROOT / timestamp


def parse_args(argv: Optional[Sequence[str]] = None) -> DemoOptions:
    """Parse and validate the visualization command line."""

    parser = argparse.ArgumentParser(
        description="Run the Stage I environment with the validated STL monitor.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--render", choices=("human", "video", "none"), default="human")
    parser.add_argument("--policy", choices=("scripted", "random"), default="scripted")
    parser.add_argument("--seed", type=int, default=44)
    parser.add_argument("--max-steps", type=int, default=500)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--camera-name", default="fixedfar")
    parser.add_argument("--status-interval", type=int, default=30)
    args = parser.parse_args(argv)
    for name in ("max_steps", "width", "height", "fps", "status_interval"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.render == "human" and not os.environ.get("DISPLAY"):
        parser.error("--render human requires DISPLAY; use --render video on a headless host")
    output_dir = args.output_dir if args.output_dir is not None else default_output_directory()
    return DemoOptions(
        config_path=args.config.resolve(),
        output_dir=output_dir.resolve(),
        render=args.render,
        policy=args.policy,
        seed=args.seed,
        max_steps=args.max_steps,
        width=args.width,
        height=args.height,
        fps=args.fps,
        camera_name=args.camera_name,
        status_interval=args.status_interval,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""

    options = parse_args(argv)
    run_demo(options)
    return 0
