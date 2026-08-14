"""Bounded, resumable D43 fixed-route quick-turn execution support."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import torch
import yaml
from omnisafe.utils.config import Config, check_all_configs, get_default_kwargs_yaml
from omnisafe.utils.tools import recursive_check_config

import safety_stl.omnisafe_env  # noqa: F401
from safety_stl.diagnostic_algorithm import DiagnosticPPOLag
from safety_stl.evaluation import evaluate_checkpoint, write_evaluation_outputs


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = ROOT / "configs/fixed_route_v1/quick_turn.yaml"
HARDWARE_GATE = ROOT / "results/hardware_stability_gate/summary.json"
ADMIN_OVERRIDE = ROOT / "configs/fixed_route_v1/d41_admin_override.yaml"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_mapping(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) if path.suffix in {".yaml", ".yml"} else json.load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"expected mapping: {path}")
    return dict(value)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_contract(
    protocol_path: Path = DEFAULT_PROTOCOL,
    *,
    expected_protocol_id: str = "fixed_route_v1_quick_turn",
    expected_authority: str = "D43",
) -> Tuple[Dict[str, Any], Path, Path]:
    protocol = read_mapping(protocol_path)
    if (
        protocol.get("protocol_id") != expected_protocol_id
        or protocol.get("authority") != expected_authority
    ):
        raise ValueError(
            f"not the authorized {expected_authority} protocol "
            f"{expected_protocol_id}",
        )
    scenario = (ROOT / protocol["prerequisites"]["scenario_config"]).resolve()
    rule = (ROOT / protocol["prerequisites"]["executable_rule_config"]).resolve()
    scenario_data, rule_data = read_mapping(scenario), read_mapping(rule)
    candidate = scenario_data["stl_rule_candidate"]
    if float(candidate["d_warn"]) != float(rule_data["d_warn"]) or float(candidate["d_safe"]) != float(rule_data["d_safe"]):
        raise ValueError("scenario/rule thresholds differ")
    if not isinstance(rule_data.get("deadline_steps"), int) or int(rule_data["deadline_steps"]) <= 0:
        raise ValueError("fixed-route rule lacks calibrated integer K")
    return protocol, scenario, rule


def require_hardware_gate(
    path: Path = HARDWARE_GATE,
    *,
    override_path: Optional[Path] = None,
    protocol_id: str = "fixed_route_v1_quick_turn",
) -> Dict[str, Any]:
    if not path.is_file():
        if override_path is not None and override_path.is_file():
            override = read_mapping(override_path)
            if (
                override.get("status") == "administrator_risk_override"
                and override.get("scope", {}).get("protocol_id") == protocol_id
                and bool(
                    override.get("acknowledgements", {}).get(
                        "prior_mce_and_segfault_risk_accepted_for_this_bounded_run",
                    ),
                )
            ):
                return {
                    **override,
                    "gate_mode": "administrator_risk_override",
                    "evidence_path": str(override_path.resolve()),
                }
        raise RuntimeError(
            "D41 blocks training: missing results/hardware_stability_gate/summary.json",
        )
    gate = read_mapping(path)
    required = (
        gate.get("status") == "passed",
        bool(gate.get("cpu_stability_passed")),
        bool(gate.get("ram_stability_passed")),
        bool(gate.get("discarded_formal_epoch_passed")),
        int(gate.get("new_mce_count", -1)) == 0,
        int(gate.get("new_segfault_count", -1)) == 0,
        int(gate.get("new_cuda_xid_count", -1)) == 0,
        int(gate.get("oom_count", -1)) == 0,
        int(gate.get("nonfinite_count", -1)) == 0,
    )
    if not all(required):
        raise RuntimeError("D41 hardware stability evidence is incomplete or failed")
    return {**gate, "gate_mode": "stability_gate_passed", "evidence_path": str(path.resolve())}


def build_config(
    protocol: Mapping[str, Any], scenario: Path, rule: Path, condition_id: str,
    transitions: int, cost_limit: float, log_dir: Path, *, update_iters: Optional[int] = None,
) -> Config:
    condition = protocol["conditions"][condition_id]
    stage1 = read_mapping(ROOT / "configs/stage1_pilot/protocol.yaml")["omnisafe"]
    training = protocol["training"]
    custom = {
        "seed": int(training["training_seed"]),
        "train_cfgs": copy.deepcopy(stage1["train_cfgs"]),
        "algo_cfgs": copy.deepcopy(stage1["algo_cfgs"]),
        "logger_cfgs": {**copy.deepcopy(stage1["logger_cfgs"]), "log_dir": str(log_dir)},
        "model_cfgs": copy.deepcopy(stage1["model_cfgs"]),
        "lagrange_cfgs": {
            **copy.deepcopy(stage1["lagrange_cfgs_shared"]),
            "lagrangian_multiplier_init": float(training["lagrangian_multiplier_init"]),
            "cost_limit": float(cost_limit),
        },
        "env_cfgs": {
            **copy.deepcopy(stage1["env_cfgs"]),
            "rule_config_path": str(rule),
            "scenario_config_path": str(scenario),
            "asynchronous": False,
        },
    }
    custom["train_cfgs"]["total_steps"] = int(transitions)
    custom["train_cfgs"]["vector_env_nums"] = int(training["vector_env_nums"])
    custom["algo_cfgs"]["steps_per_epoch"] = int(training["steps_per_epoch"])
    custom["algo_cfgs"]["update_iters"] = int(training["update_iters"] if update_iters is None else update_iters)
    custom["algo_cfgs"]["batch_size"] = int(training["batch_size"])
    custom["logger_cfgs"]["save_model_freq"] = max(1, int(transitions) // int(training["steps_per_epoch"]))
    env_id = str(condition["environment_id"])
    cfgs = get_default_kwargs_yaml("PPOLag", env_id, "on-policy")
    recursive_check_config(custom, cfgs)
    cfgs.recurisve_update(custom)
    cfgs.update({"exp_increment_cfgs": custom})
    cfgs.recurisve_update({"exp_name": f"FixedRouteQuickTurn-{{{env_id}}}", "env_id": env_id, "algo": "PPOLag"})
    cfgs.train_cfgs.recurisve_update({"epochs": int(transitions) // int(training["steps_per_epoch"])})
    check_all_configs(cfgs, "on-policy")
    return cfgs


def _checkpoint(run_dir: Path) -> Path:
    values = []
    for path in (run_dir / "torch_save").glob("epoch-*.pt"):
        match = re.fullmatch(r"epoch-(\d+)\.pt", path.name)
        if match:
            values.append((int(match.group(1)), path))
    if not values:
        raise FileNotFoundError("training produced no checkpoint")
    return max(values)[1]


def _progress(path: Path) -> List[Dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [{key: float(value) for key, value in row.items() if value != ""} for row in csv.DictReader(handle)]


def cost_routing_diagnostics(
    rows: Sequence[Mapping[str, float]],
    route_field: Optional[str],
    *,
    relative_tolerance: float = 1e-7,
    absolute_tolerance: float = 1e-6,
) -> Dict[str, Any]:
    """Check logger-aggregated cost routing with a scale-aware float tolerance.

    The selected/source tensors are identical before logging, but independent
    distributed accumulators can differ by a few float32 ULPs.  Exact decimal
    equality of their CSV reductions is therefore not a valid routing test.
    """

    comparisons = []
    for index, row in enumerate(rows):
        selected = float(row["Metrics/SelectedAlgorithmCost"])
        expected = 0.0 if route_field is None else float(row[route_field])
        absolute_error = abs(selected - expected)
        scale = max(abs(selected), abs(expected))
        relative_error = 0.0 if scale == 0.0 else absolute_error / scale
        comparisons.append((absolute_error, relative_error, index, selected, expected))
    maximum = max(comparisons, default=(0.0, 0.0, -1, 0.0, 0.0))
    return {
        "passed": all(
            math.isclose(
                selected,
                expected,
                rel_tol=relative_tolerance,
                abs_tol=absolute_tolerance,
            )
            for _, _, _, selected, expected in comparisons
        ),
        "relative_tolerance": relative_tolerance,
        "absolute_tolerance": absolute_tolerance,
        "maximum_absolute_error": maximum[0],
        "maximum_relative_error": max((item[1] for item in comparisons), default=0.0),
        "maximum_error_epoch_index": maximum[2],
        "maximum_error_selected": maximum[3],
        "maximum_error_expected": maximum[4],
        "row_count": len(comparisons),
    }


def _new_kernel_stop_events(since_unix: float) -> List[str]:
    result = subprocess.run(
        ["journalctl", "-k", "--since", f"@{int(since_unix)}", "--no-pager"],
        check=False,
        capture_output=True,
        text=True,
    )
    pattern = re.compile(
        r"machine.?check|\bmce\b|hardware error|nvrm: xid|out of memory|oom-kill|segfault",
        re.IGNORECASE,
    )
    return [line for line in result.stdout.splitlines() if pattern.search(line)]


def run_cell(
    protocol_path: Path, condition_id: str, transitions: int, cost_limit: float,
    output_dir: Path, *, preflight: bool = False,
    override_path: Path = ADMIN_OVERRIDE,
    expected_protocol_id: str = "fixed_route_v1_quick_turn",
    expected_authority: str = "D43",
) -> Dict[str, Any]:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    protocol, scenario, rule = load_contract(
        protocol_path,
        expected_protocol_id=expected_protocol_id,
        expected_authority=expected_authority,
    )
    hardware_gate = require_hardware_gate(
        override_path=override_path,
        protocol_id=expected_protocol_id,
    )
    if not torch.cuda.is_available():
        raise RuntimeError(f"{expected_authority} requires CUDA")
    cell_root = output_dir / condition_id / ("preflight" if preflight else f"reported-{transitions}")
    latest = cell_root / "manifest.json"
    identity = {
        "protocol_sha256": sha256_file(protocol_path),
        "scenario_sha256": sha256_file(scenario),
        "rule_sha256": sha256_file(rule),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "algorithm_sha256": sha256_file(ROOT / "src/safety_stl/diagnostic_algorithm.py"),
        "environment_sha256": sha256_file(ROOT / "src/safety_stl/omnisafe_env.py"),
        "condition_id": condition_id,
        "transitions": int(transitions),
        "cost_limit": float(cost_limit),
        "preflight": bool(preflight),
        "git_commit": git_commit(),
        "hardware_gate_sha256": sha256_file(Path(str(hardware_gate["evidence_path"]))),
        "hardware_gate_status": hardware_gate.get("status"),
        "hardware_gate_mode": hardware_gate.get("gate_mode"),
        "environment_id": str(protocol["conditions"][condition_id]["environment_id"]),
        "d_warn": float(read_mapping(rule)["d_warn"]),
        "d_safe": float(read_mapping(rule)["d_safe"]),
        "deadline_steps": int(read_mapping(rule)["deadline_steps"]),
        "update_iters": int(protocol["training"]["update_iters"]),
        "device": "cuda:0",
        "gpu_name": torch.cuda.get_device_name(0),
        "torch_version": torch.__version__,
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
    }
    if latest.is_file():
        current = read_mapping(latest)
        if current.get("status") == "success":
            mismatched_identity_keys = [
                key for key, value in identity.items() if current.get(key) != value
            ]
            if not mismatched_identity_keys:
                return dict(current["summary"])
        else:
            mismatched_identity_keys = []
    else:
        mismatched_identity_keys = []
    attempts_root = cell_root / "attempts"
    numbers = []
    if attempts_root.is_dir():
        for path in attempts_root.iterdir():
            match = re.fullmatch(r"attempt-(\d{4})", path.name)
            if path.is_dir() and match:
                numbers.append(int(match.group(1)))
    attempt = attempts_root / f"attempt-{max(numbers, default=0) + 1:04d}"
    attempt.mkdir(parents=True, exist_ok=False)
    manifest = attempt / "manifest.json"
    started_at_unix = time.time()
    running = {
        "status": "running",
        **identity,
        "attempt_dir": str(attempt),
        "started_at_unix": started_at_unix,
        "supersedes_success_with_mismatched_identity_keys": mismatched_identity_keys,
    }
    write_json(manifest, running); write_json(latest, running)
    # The 10k throughput preflight must exercise the same optimizer workload as
    # a reported epoch.  Otherwise its transitions/second estimate is inflated
    # and the wall-clock formula can select a budget that violates D43's cap.
    cfgs = build_config(
        protocol,
        scenario,
        rule,
        condition_id,
        transitions,
        cost_limit,
        attempt / "training",
    )
    torch.cuda.set_device(0)
    torch.cuda.reset_peak_memory_stats(0)
    started = time.monotonic()
    try:
        algorithm = DiagnosticPPOLag(str(protocol["conditions"][condition_id]["environment_id"]), cfgs)
        algorithm.learn(); torch.cuda.synchronize(0)
        kernel_events = _new_kernel_stop_events(started_at_unix)
        if kernel_events:
            raise RuntimeError(
                f"new kernel stop event during {expected_authority} cell: {kernel_events[-5:]}",
            )
        elapsed = time.monotonic() - started
        run_dir = Path(algorithm.logger.log_dir).resolve()
        rows = _progress(run_dir / "progress.csv")
        selected = str(protocol["conditions"][condition_id]["selected_learner_cost"])
        route_field = {"identically_zero": None, "native_hazard_cost": "Metrics/NativeCost", "c1_causal_dense_surrogate": "Metrics/STLDenseCost"}[selected]
        routing_diagnostics = cost_routing_diagnostics(rows, route_field)
        routing = bool(routing_diagnostics["passed"])
        positive = True if route_field is None else any(row[route_field] > 0 for row in rows)
        dense_exceeds_binary = any(
            row["Metrics/STLDenseCost"] > row["Metrics/STLCost"] + 1e-9
            for row in rows
        )
        checkpoint = _checkpoint(run_dir)
        progress_path = run_dir / "progress.csv"
        summary = {
            "condition_id": condition_id, "preflight": preflight, "transitions": transitions,
            "cost_limit": float(cost_limit), "elapsed_seconds": elapsed,
            "transitions_per_second": transitions / elapsed, "run_dir": str(run_dir),
            "progress": str(progress_path), "progress_sha256": sha256_file(progress_path),
            "checkpoint": str(checkpoint), "checkpoint_sha256": sha256_file(checkpoint),
            "routing_exact": routing, "positive_selected_source_observed": positive,
            "routing_diagnostics": routing_diagnostics,
            "dense_exceeds_binary_event_cost": dense_exceeds_binary,
            "last_epoch_cost_metrics": {
                "binary_stl_cost": rows[-1]["Metrics/STLCost"],
                "dense_stl_cost": rows[-1]["Metrics/STLDenseCost"],
                "selected_algorithm_cost": rows[-1]["Metrics/SelectedAlgorithmCost"],
                "positive_cost_step_fraction": rows[-1]["Diagnostics/PositiveCostStepFraction"],
            },
            "all_finite": all(math.isfinite(value) for row in rows for value in row.values()),
            "peak_gpu_memory_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
            "new_kernel_stop_events": kernel_events,
        }
        if not all((routing, positive, summary["all_finite"])):
            raise RuntimeError(f"{expected_authority} cell gate failed: {summary}")
    except BaseException as error:
        failed = {**running, "status": "failed", "elapsed_seconds": time.monotonic() - started, "error_type": type(error).__name__, "error": str(error)}
        write_json(manifest, failed); write_json(latest, failed)
        raise
    success = {**running, "status": "success", "completed_at_unix": time.time(), "elapsed_seconds": elapsed, "summary": summary}
    write_json(manifest, success); write_json(latest, success)
    return summary


def evaluate_cell(
    protocol_path: Path, training: Mapping[str, Any], output: Path, *, deterministic: bool,
    seeds: Sequence[int], trajectories: bool,
    expected_protocol_id: str = "fixed_route_v1_quick_turn",
    expected_authority: str = "D43",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    _, scenario, rule = load_contract(
        protocol_path,
        expected_protocol_id=expected_protocol_id,
        expected_authority=expected_authority,
    )
    checkpoint = Path(str(training["checkpoint"]))
    result = evaluate_checkpoint(
        Path(str(training["run_dir"])), checkpoint.name, seeds,
        max_episode_steps=1000, deterministic=deterministic,
        rule_config_path=rule, scenario_config_path=scenario, save_trajectories=trajectories,
    )
    write_evaluation_outputs(output, *result)
    return result


def derive_task_budgets(episodes: Sequence[Mapping[str, Any]], trajectories: Sequence[Mapping[str, Any]], rule: Mapping[str, Any]) -> Dict[str, Any]:
    native = sum(float(row["native_cost_total"]) for row in episodes) / len(episodes)
    by_episode: Dict[Tuple[int, int], float] = {}
    for row in trajectories:
        if int(row["action_index"]) < 0:
            continue
        key = (int(row["episode_index"]), int(row["evaluation_seed"]))
        cost = 0.0
        if int(row["stl_cost"]):
            cost = 1.0
        elif str(row["monitor_state"]) != "inactive":
            remaining = 0.0 if row["remaining_steps"] is None else float(row["remaining_steps"])
            qd = min(max((float(rule["d_safe"]) - float(row["distance"])) / (float(rule["d_safe"]) - float(rule["d_warn"])), 0.0), 1.0)
            qu = min(max(1.0 - remaining / float(rule["deadline_steps"]), 0.0), 1.0)
            cost = 0.5 * qd + 0.5 * qu
        by_episode[key] = by_episode.get(key, 0.0) + cost
    dense = sum(by_episode.values()) / len(by_episode)
    return {
        "status": "frozen_before_cost_cells", "episode_count": len(episodes), "fraction": 0.70,
        "task_control_mean": {"native_cost_per_episode": native, "c1_surrogate_mass_per_episode": dense},
        "cost_limit": {"native_cost_per_episode": 0.70 * native, "c1_surrogate_mass_per_episode": 0.70 * dense},
        "unit_guard": "native and C1 units are different and were derived separately",
    }


def git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


__all__ = ["DEFAULT_PROTOCOL", "build_config", "cost_routing_diagnostics", "derive_task_budgets", "evaluate_cell", "git_commit", "load_contract", "require_hardware_gate", "run_cell", "sha256_file", "write_json"]
