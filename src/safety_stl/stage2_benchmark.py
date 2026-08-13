"""Build and validate the reviewable Stage II v0 offline benchmark foundation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from safety_stl.monitor import BoundedRecoveryMonitor
from safety_stl.oracle import evaluate_trace, rtamt_window_robustness


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = REPOSITORY_ROOT / "benchmarks" / "stage2_v0"
TOLERANCE = 1e-9


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in materialized:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return len(materialized)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _number(value: float) -> str:
    return format(float(value), ".15g")


def validate_benchmark_contract(root: Path = BENCHMARK_ROOT) -> Dict[str, Any]:
    """Validate the frozen portion of the draft contract without external schema tools."""

    benchmark = _load_json(root / "benchmark.json")
    specifications = _load_json(root / "specifications.json")
    reviews = _load_json(root / "reviews.json")
    errors: List[str] = []
    if benchmark.get("status") != "draft_foundation_pending_o7_review":
        errors.append("benchmark status must remain pending O7 review")
    if benchmark.get("supported_fragment", {}).get("formula_families") != [
        "hysteretic_bounded_recovery",
    ]:
        errors.append("v0 may execute only the verified bounded-recovery family")
    if benchmark.get("draft_split_policy", {}).get("status") != "unassigned_pending_o7_review":
        errors.append("data splits must remain unassigned before O7 review")
    if not isinstance(specifications, list) or not specifications:
        errors.append("specifications.json must contain at least one specification")
        specifications = []

    seen_ids: set[str] = set()
    seen_language: set[str] = set()
    pair_splits: MutableMapping[str, set[str]] = defaultdict(set)
    for index, spec in enumerate(specifications):
        prefix = f"specification[{index}]"
        required = {
            "spec_id",
            "canonical_natural_language",
            "paraphrases",
            "gold_stl",
            "formula_family",
            "grounding_schema",
            "parameter_values",
            "semantic_pair_id",
            "semantic_contrast_type",
            "allowed_online_use",
            "split",
            "annotation_author",
            "independent_reviewer",
            "review_status",
            "source_or_generation_record",
        }
        missing = sorted(required - set(spec))
        extra = sorted(set(spec) - required)
        if missing:
            errors.append(f"{prefix} missing fields: {missing}")
            continue
        if extra:
            errors.append(f"{prefix} has undeclared fields: {extra}")
        spec_id = str(spec["spec_id"])
        if spec_id in seen_ids:
            errors.append(f"duplicate spec_id: {spec_id}")
        seen_ids.add(spec_id)
        if spec["formula_family"] != "hysteretic_bounded_recovery":
            errors.append(f"{spec_id} uses an unapproved formula family")
        parameters = spec["parameter_values"]
        if set(parameters) != {"d_warn", "d_safe", "deadline_steps"}:
            errors.append(f"{spec_id} has invalid parameter fields")
        warn = float(parameters["d_warn"])
        safe = float(parameters["d_safe"])
        deadline = parameters["deadline_steps"]
        if not 0.2 < warn < safe < 3.0:
            errors.append(f"{spec_id} has invalid distance thresholds")
        if isinstance(deadline, bool) or not isinstance(deadline, int) or deadline <= 0:
            errors.append(f"{spec_id} has invalid deadline_steps")
        expected_formula = (
            f"G(e(d < {_number(warn)}) -> "
            f"F_[0,{deadline}](d >= {_number(safe)}))"
        )
        if spec["gold_stl"] != expected_formula:
            errors.append(f"{spec_id} Gold STL differs from typed parameters")
        grounding = spec["grounding_schema"]
        if grounding.get("signal_id") != "nearest_hazard_center_distance_public":
            errors.append(f"{spec_id} does not use the public Stage I distance signal")
        if grounding.get("trigger_mode") != "hysteretic_warning_episode":
            errors.append(f"{spec_id} has incompatible trigger semantics")
        if grounding.get("deadline_inclusive") is not True:
            errors.append(f"{spec_id} must use an inclusive deadline")
        language_items = [spec["canonical_natural_language"], *spec["paraphrases"]]
        if len(spec["paraphrases"]) < 2 or len(set(language_items)) != len(language_items):
            errors.append(f"{spec_id} needs at least two distinct paraphrases")
        for language in language_items:
            normalized = " ".join(str(language).lower().split())
            if normalized in seen_language:
                errors.append(f"duplicate language item found in {spec_id}")
            seen_language.add(normalized)
        if spec["split"] != "draft_unassigned":
            errors.append(f"{spec_id} was assigned to a split before review")
        pair_splits[str(spec["semantic_pair_id"])].add(str(spec["split"]))
        if spec["review_status"] not in {
            "machine_validated_pending_independent_review",
            "independently_reviewed",
        }:
            errors.append(f"{spec_id} has an invalid review status")
        if spec["review_status"] == "independently_reviewed" and not spec["independent_reviewer"]:
            errors.append(f"{spec_id} claims review without naming the reviewer")

    leaking_pairs = sorted(pair for pair, splits in pair_splits.items() if len(splits) > 1)
    if leaking_pairs:
        errors.append(f"semantic pairs span multiple splits: {leaking_pairs}")
    if errors:
        raise ValueError("invalid Stage II v0 benchmark contract:\n- " + "\n- ".join(errors))
    review_by_id = {str(review.get("spec_id", "")): review for review in reviews}
    if set(review_by_id) != seen_ids or len(review_by_id) != len(reviews):
        raise ValueError("independent-review records must map one-to-one to specifications")
    review_checks = {
        "object",
        "signal",
        "operator",
        "comparator",
        "threshold",
        "deadline",
        "equality",
        "terminal_semantics",
        "paraphrase_equivalence",
    }
    review_fields = {
        "spec_id",
        "reviewer",
        "status",
        "checks",
        "disagreement_notes",
        "reviewed_at",
    }
    for spec in specifications:
        review = review_by_id[str(spec["spec_id"])]
        if set(review) != review_fields:
            raise ValueError(f"invalid review fields: {spec['spec_id']}")
        if set(review.get("checks", {})) != review_checks:
            raise ValueError(f"invalid review checklist: {spec['spec_id']}")
        if review.get("status") == "approved":
            if not review.get("reviewer") or not all(review["checks"].values()):
                raise ValueError(f"incomplete approved review: {spec['spec_id']}")
            if (
                spec["review_status"] != "independently_reviewed"
                or spec["independent_reviewer"] != review["reviewer"]
            ):
                raise ValueError(f"specification/review status mismatch: {spec['spec_id']}")
        elif review.get("status") not in {"pending", "changes_requested"}:
            raise ValueError(f"invalid review status: {spec['spec_id']}")
    return {
        "benchmark": benchmark,
        "specifications": specifications,
        "specification_count": len(specifications),
        "semantic_pair_split_leakage_count": len(leaking_pairs),
        "reviews": reviews,
    }


def _terminal_flags(length: int) -> tuple[List[bool], List[bool]]:
    return [False] * length, [False] * (length - 1) + [True]


def _synthetic_cases(spec: Mapping[str, Any]) -> List[Dict[str, Any]]:
    parameters = spec["parameter_values"]
    warn = float(parameters["d_warn"])
    safe = float(parameters["d_safe"])
    deadline = int(parameters["deadline_steps"])
    safe_high = min(safe + 0.1, 2.99)
    mid = (warn + safe) / 2.0
    unsafe = max(0.0, warn - 0.01)

    def padded(events: Mapping[int, float], final_step: int, default: float = safe_high) -> List[float]:
        values = [default] * (final_step + 1)
        for step, value in events.items():
            values[step] = value
        return values

    cases: List[Dict[str, Any]] = []

    def add(case_id: str, distances: Sequence[float], tags: Sequence[str], **extra: Any) -> None:
        cases.append(
            {
                "case_id": case_id,
                "distances": [float(value) for value in distances],
                "case_tags": list(tags),
                "history_pair_id": extra.get("history_pair_id"),
                "history_anchor_step": extra.get("history_anchor_step"),
            },
        )

    add("vacuous", [safe_high] * 4, ["vacuous", "no_trigger"])
    add(
        "on_time_recovery",
        padded({1: unsafe, 2: mid, 3: safe_high}, deadline + 2),
        ["trigger", "on_time_recovery"],
    )
    add(
        "exact_deadline_recovery",
        [safe_high, unsafe] + [mid] * (deadline - 1) + [safe] + [safe_high],
        ["trigger", "exact_deadline", "recovery_equality"],
    )
    add(
        "one_step_late",
        [safe_high, unsafe] + [mid] * deadline + [safe_high],
        ["trigger", "deadline_violation", "one_step_late"],
    )
    add(
        "terminal_unresolved",
        [safe_high, unsafe, mid],
        ["trigger", "terminal_unresolved", "finite_trace_boundary"],
    )
    add(
        "warning_equality_no_trigger",
        [safe_high, warn, warn, safe_high],
        ["warning_equality", "strict_warning_comparator", "no_trigger"],
    )
    add(
        "safe_equality_recovery",
        padded({1: unsafe, 2: safe}, deadline + 2),
        ["trigger", "safe_equality", "inclusive_recovery_comparator"],
    )
    add(
        "repeated_entry_while_pending",
        padded({1: unsafe, 2: unsafe, 3: unsafe, 4: safe_high}, deadline + 2),
        ["single_active_obligation", "repeated_unsafe_samples", "on_time_recovery"],
    )
    add(
        "retrigger_after_recovery",
        padded({1: unsafe, 2: safe_high, 3: unsafe, 4: safe_high}, deadline + 5),
        ["multiple_obligations", "retrigger_after_recovery"],
    )
    history_pair_id = f"{spec['spec_id']}__history-state-contrast"
    anchor = 6
    add(
        "history_inactive",
        padded({anchor: mid}, deadline + 8),
        ["history_contrast", "same_current_observation", "inactive_at_anchor"],
        history_pair_id=history_pair_id,
        history_anchor_step=anchor,
    )
    add(
        "history_pending",
        [safe_high, safe_high, unsafe]
        + [mid] * (anchor - 2)
        + [safe_high] * (deadline + 8 - anchor),
        ["history_contrast", "same_current_observation", "pending_at_anchor"],
        history_pair_id=history_pair_id,
        history_anchor_step=anchor,
    )
    return cases


def _label_trace(
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
    parameters: Mapping[str, Any],
) -> Dict[str, Any]:
    warn = float(parameters["d_warn"])
    safe = float(parameters["d_safe"])
    deadline = int(parameters["deadline_steps"])
    oracle = evaluate_trace(
        distances,
        warn,
        safe,
        deadline,
        terminated=terminated,
        truncated=truncated,
    )
    monitor = BoundedRecoveryMonitor(warn, safe, deadline)
    online_rows = []
    for index, distance in enumerate(distances):
        if index == 0:
            if terminated[index] or truncated[index]:
                raise ValueError("single-sample terminal traces are not supported")
            output = monitor.reset(float(distance))
        else:
            output = monitor.step(
                float(distance),
                terminated=bool(terminated[index]),
                truncated=bool(truncated[index]),
            )
        online_rows.append(output.as_dict())

    event_fields = {
        "trigger_steps": "stl_warning_trigger",
        "recovery_steps": "stl_recovery",
        "late_recovery_steps": "stl_late_recovery",
        "violation_steps": "stl_deadline_violation",
        "unresolved_steps": "stl_terminal_unresolved",
    }
    online_events = {
        name: [int(row["sample_index"]) for row in online_rows if row[field]]
        for name, field in event_fields.items()
    }
    expected_events = {
        "trigger_steps": oracle.trigger_steps,
        "recovery_steps": oracle.recovery_steps,
        "late_recovery_steps": oracle.late_recovery_steps,
        "violation_steps": oracle.violation_steps,
        "unresolved_steps": oracle.unresolved_steps,
    }
    online_costs = [int(row["stl_cost"]) for row in online_rows]
    if online_events != expected_events or online_costs != oracle.costs:
        raise AssertionError("online monitor and independent oracle disagree")

    rtamt_rows = []
    for window in oracle.completed_windows:
        robustness = rtamt_window_robustness(
            distances[window.trigger_step : window.deadline_step + 1],
            safe,
            deadline,
        )
        difference = abs(robustness - window.robustness)
        if difference > TOLERANCE:
            raise AssertionError("RTAMT and independent robustness disagree")
        rtamt_rows.append(
            {
                "episode_id": window.episode_id,
                "trigger_step": window.trigger_step,
                "deadline_step": window.deadline_step,
                "direct_robustness": window.robustness,
                "rtamt_robustness": robustness,
                "absolute_difference": difference,
            },
        )
    oracle_dict = oracle.as_dict()
    return {
        "agreement": True,
        "oracle": oracle_dict,
        "online": {
            **online_events,
            "costs": online_costs,
            "states": [str(row["stl_status"]) for row in online_rows],
        },
        "rtamt_completed_windows": rtamt_rows,
        "rtamt_max_robustness_difference": max(
            (row["absolute_difference"] for row in rtamt_rows),
            default=0.0,
        ),
    }


def _make_record(
    *,
    trajectory_id: str,
    spec: Mapping[str, Any],
    source_type: str,
    source: Mapping[str, Any],
    case_tags: Sequence[str],
    distances: Sequence[float],
    rewards: Optional[Sequence[Optional[float]]] = None,
    native_costs: Optional[Sequence[Optional[float]]] = None,
    terminated: Optional[Sequence[bool]] = None,
    truncated: Optional[Sequence[bool]] = None,
    history_pair_id: Optional[str] = None,
    history_anchor_step: Optional[int] = None,
) -> Dict[str, Any]:
    length = len(distances)
    if terminated is None or truncated is None:
        terminated, truncated = _terminal_flags(length)
    rewards = list(rewards) if rewards is not None else [None] * length
    native_costs = list(native_costs) if native_costs is not None else [None] * length
    if not all(len(values) == length for values in (rewards, native_costs, terminated, truncated)):
        raise ValueError("all trajectory arrays must have the same length")
    labels = _label_trace(
        distances,
        terminated,
        truncated,
        spec["parameter_values"],
    )
    samples = [
        {
            "sample_index": index,
            "distance": float(distances[index]),
            "reward": rewards[index],
            "native_cost": native_costs[index],
            "stl_cost": int(labels["oracle"]["costs"][index]),
            "terminated": bool(terminated[index]),
            "truncated": bool(truncated[index]),
        }
        for index in range(length)
    ]
    return {
        "trajectory_id": trajectory_id,
        "spec_id": str(spec["spec_id"]),
        "source_type": source_type,
        "source": dict(source),
        "case_tags": list(case_tags),
        "history_pair_id": history_pair_id,
        "history_anchor_step": history_anchor_step,
        "samples": samples,
        "gold_labels": labels,
    }


def generate_synthetic(specifications: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    records = []
    for spec in specifications:
        for case in _synthetic_cases(spec):
            records.append(
                _make_record(
                    trajectory_id=f"synthetic__{spec['spec_id']}__{case['case_id']}",
                    spec=spec,
                    source_type="synthetic",
                    source={
                        "generator": "safety_stl.stage2_benchmark._synthetic_cases",
                        "case_id": case["case_id"],
                    },
                    case_tags=case["case_tags"],
                    distances=case["distances"],
                    history_pair_id=case["history_pair_id"],
                    history_anchor_step=case["history_anchor_step"],
                ),
            )
    return records


def import_real_trajectories(
    specifications: Sequence[Mapping[str, Any]],
    csv_path: Path,
    provenance_path: Path,
) -> List[Dict[str, Any]]:
    """Import preselected existing-checkpoint traces; this never selects a new policy."""

    if not csv_path.is_file() or not provenance_path.is_file():
        raise FileNotFoundError("Stage I representative diagnosis must finish before real import")
    spec = next(item for item in specifications if item["spec_id"] == "br-v0-001")
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        raw_rows = list(csv.DictReader(handle))
    provenance = {row["trajectory_id"]: row for row in _load_json(provenance_path)}
    grouped: MutableMapping[str, List[Mapping[str, str]]] = defaultdict(list)
    for row in raw_rows:
        grouped[str(row["trajectory_id"])].append(row)
    records = []
    for trajectory_id, rows in sorted(grouped.items()):
        rows.sort(key=lambda row: int(row["sample_index"]))
        expected_indices = list(range(len(rows)))
        if [int(row["sample_index"]) for row in rows] != expected_indices:
            raise ValueError(f"non-contiguous real trajectory: {trajectory_id}")
        metadata = provenance[trajectory_id]
        checkpoint = Path(str(metadata["checkpoint"]))
        if not checkpoint.is_file() or _sha256(checkpoint) != metadata["checkpoint_sha256"]:
            raise ValueError(f"checkpoint provenance mismatch: {trajectory_id}")
        if metadata.get("gold_oracle_agreement") is not True:
            raise ValueError(f"source replay lacked Gold agreement: {trajectory_id}")
        records.append(
            _make_record(
                trajectory_id=trajectory_id,
                spec=spec,
                source_type="real_policy_checkpoint",
                source={
                    "selection_frozen_before_replay": True,
                    "selection_case_id": metadata["case_id"],
                    "selection_rule": metadata["selection"],
                    "condition": metadata["condition"],
                    "training_seed": metadata["training_seed"],
                    "evaluation_seed": metadata["evaluation_seed"],
                    "checkpoint": str(checkpoint),
                    "checkpoint_sha256": metadata["checkpoint_sha256"],
                    "source_csv": str(csv_path.relative_to(REPOSITORY_ROOT)),
                    "source_csv_sha256": _sha256(csv_path),
                },
                case_tags=[
                    "existing_final_checkpoint",
                    "frozen_representative_case",
                    str(metadata["selection"]),
                    str(metadata["condition"]),
                ],
                distances=[float(row["distance"]) for row in rows],
                rewards=[float(row["reward"]) for row in rows],
                native_costs=[float(row["native_cost"]) for row in rows],
                terminated=[row["terminated"] == "True" for row in rows],
                truncated=[row["truncated"] == "True" for row in rows],
            ),
        )
    return records


def validate_trajectories(
    records: Sequence[Mapping[str, Any]],
    specifications: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    if not records:
        raise ValueError("trajectory collection must not be empty")
    if specifications is None:
        specifications = _load_json(BENCHMARK_ROOT / "specifications.json")
    specification_by_id = {str(spec["spec_id"]): spec for spec in specifications}
    errors: List[str] = []
    trajectory_ids: set[str] = set()
    max_rtamt_difference = 0.0
    case_tags: set[str] = set()
    record_fields = {
        "trajectory_id",
        "spec_id",
        "source_type",
        "source",
        "case_tags",
        "history_pair_id",
        "history_anchor_step",
        "samples",
        "gold_labels",
    }
    sample_fields = {
        "sample_index",
        "distance",
        "reward",
        "native_cost",
        "stl_cost",
        "terminated",
        "truncated",
    }
    for record in records:
        trajectory_id = str(record.get("trajectory_id", ""))
        if set(record) != record_fields:
            errors.append(f"{trajectory_id} fields differ from trajectory schema")
        if not trajectory_id or trajectory_id in trajectory_ids:
            errors.append(f"empty or duplicate trajectory_id: {trajectory_id}")
        trajectory_ids.add(trajectory_id)
        samples = record.get("samples")
        if not isinstance(samples, list) or not samples:
            errors.append(f"{trajectory_id} has no samples")
            continue
        indices = [sample.get("sample_index") for sample in samples]
        if indices != list(range(len(samples))):
            errors.append(f"{trajectory_id} sample indices are not contiguous")
        for sample in samples:
            if set(sample) != sample_fields:
                errors.append(f"{trajectory_id} sample fields differ from trajectory schema")
            distance = float(sample["distance"])
            if not math.isfinite(distance) or not 0.0 <= distance <= 3.0:
                errors.append(f"{trajectory_id} has an invalid distance")
            if int(sample["stl_cost"]) not in (0, 1):
                errors.append(f"{trajectory_id} has a non-binary STL cost")
            for nullable_numeric in ("reward", "native_cost"):
                value = sample[nullable_numeric]
                if value is not None and (
                    isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                ):
                    errors.append(f"{trajectory_id} has invalid {nullable_numeric}")
            if not isinstance(sample["terminated"], bool) or not isinstance(sample["truncated"], bool):
                errors.append(f"{trajectory_id} has non-Boolean terminal metadata")
            if sample["terminated"] and sample["truncated"]:
                errors.append(f"{trajectory_id} sample is both terminated and truncated")
        if any(
            sample["terminated"] or sample["truncated"] for sample in samples[:-1]
        ):
            errors.append(f"{trajectory_id} has a terminal flag before the final sample")
        if record.get("source_type") not in {"synthetic", "real_policy_checkpoint"}:
            errors.append(f"{trajectory_id} has invalid source_type")
        if record.get("gold_labels", {}).get("agreement") is not True:
            errors.append(f"{trajectory_id} lacks Gold three-way agreement")
        spec_id = str(record.get("spec_id", ""))
        if spec_id not in specification_by_id:
            errors.append(f"{trajectory_id} references unknown specification {spec_id}")
        else:
            recomputed_labels = _label_trace(
                [float(sample["distance"]) for sample in samples],
                [bool(sample["terminated"]) for sample in samples],
                [bool(sample["truncated"]) for sample in samples],
                specification_by_id[spec_id]["parameter_values"],
            )
            if recomputed_labels != record.get("gold_labels"):
                errors.append(f"{trajectory_id} stored Gold labels are not reproducible")
        max_rtamt_difference = max(
            max_rtamt_difference,
            float(record.get("gold_labels", {}).get("rtamt_max_robustness_difference", 0.0)),
        )
        case_tags.update(str(tag) for tag in record.get("case_tags", []))

    history_groups: MutableMapping[str, List[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("history_pair_id") is not None:
            history_groups[str(record["history_pair_id"])].append(record)
    history_pairs_checked = 0
    for pair_id, pair in history_groups.items():
        if len(pair) != 2:
            errors.append(f"history pair {pair_id} does not contain exactly two trajectories")
            continue
        anchor_a = int(pair[0]["history_anchor_step"])
        anchor_b = int(pair[1]["history_anchor_step"])
        if anchor_a != anchor_b:
            errors.append(f"history pair {pair_id} has different anchor steps")
            continue
        distance_a = float(pair[0]["samples"][anchor_a]["distance"])
        distance_b = float(pair[1]["samples"][anchor_b]["distance"])
        state_a = pair[0]["gold_labels"]["online"]["states"][anchor_a]
        state_b = pair[1]["gold_labels"]["online"]["states"][anchor_b]
        if distance_a != distance_b or state_a == state_b:
            errors.append(f"history pair {pair_id} does not isolate causal state")
        history_pairs_checked += 1
    if errors:
        raise ValueError("invalid Stage II trajectories:\n- " + "\n- ".join(errors))
    return {
        "trajectory_count": len(records),
        "sample_count": sum(len(record["samples"]) for record in records),
        "case_tags": sorted(case_tags),
        "all_online_oracle_agree": True,
        "rtamt_max_robustness_difference": max_rtamt_difference,
        "history_pairs_checked": history_pairs_checked,
    }


def parameter_contrast_coverage(
    specifications: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Require a trace-level semantic witness for every parameter-spec pair."""

    witnesses = []
    missing = []
    for first, second in combinations(specifications, 2):
        witness = None
        for record in records:
            distances = [float(sample["distance"]) for sample in record["samples"]]
            terminated = [bool(sample["terminated"]) for sample in record["samples"]]
            truncated = [bool(sample["truncated"]) for sample in record["samples"]]
            first_labels = _label_trace(
                distances,
                terminated,
                truncated,
                first["parameter_values"],
            )
            second_labels = _label_trace(
                distances,
                terminated,
                truncated,
                second["parameter_values"],
            )
            first_semantics = (
                first_labels["oracle"]["trigger_steps"],
                first_labels["oracle"]["recovery_steps"],
                first_labels["oracle"]["violation_steps"],
                first_labels["oracle"]["unresolved_steps"],
                first_labels["oracle"]["costs"],
            )
            second_semantics = (
                second_labels["oracle"]["trigger_steps"],
                second_labels["oracle"]["recovery_steps"],
                second_labels["oracle"]["violation_steps"],
                second_labels["oracle"]["unresolved_steps"],
                second_labels["oracle"]["costs"],
            )
            if first_semantics != second_semantics:
                witness = str(record["trajectory_id"])
                break
        pair = [str(first["spec_id"]), str(second["spec_id"])]
        if witness is None:
            missing.append(pair)
        else:
            witnesses.append({"spec_pair": pair, "witness_trajectory_id": witness})
    if missing:
        raise ValueError(f"parameter contrasts lack distinguishing traces: {missing}")
    return {
        "pair_count": len(witnesses),
        "all_pairs_have_distinguishing_trace": True,
        "witnesses": witnesses,
    }


def build_benchmark(
    root: Path = BENCHMARK_ROOT,
    diagnosis_root: Path = REPOSITORY_ROOT / "results" / "post_pilot_diagnosis",
) -> Dict[str, Any]:
    """Build synthetic and real trace sets and emit a machine-auditable coverage report."""

    contract = validate_benchmark_contract(root)
    specifications = contract["specifications"]
    synthetic = generate_synthetic(specifications)
    real = import_real_trajectories(
        specifications,
        diagnosis_root / "representative_per_step_trajectories.csv",
        diagnosis_root / "representative_provenance.json",
    )
    synthetic_validation = validate_trajectories(synthetic, specifications)
    real_validation = validate_trajectories(real, specifications)
    parameter_coverage = parameter_contrast_coverage(specifications, synthetic)
    generated = root / "generated"
    synthetic_path = generated / "synthetic_trajectories.jsonl"
    real_path = generated / "real_trajectories.jsonl"
    label_path = generated / "gold_labels.jsonl"
    _write_jsonl(synthetic_path, synthetic)
    _write_jsonl(real_path, real)
    labels = [
        {
            "trajectory_id": record["trajectory_id"],
            "spec_id": record["spec_id"],
            "gold_labels": record["gold_labels"],
        }
        for record in [*synthetic, *real]
    ]
    _write_jsonl(label_path, labels)
    reviewed = sum(review["status"] == "approved" for review in contract["reviews"])
    coverage = {
        "schema_version": 1,
        "status": "machine_validated_foundation_pending_independent_review_and_o7_freeze",
        "scope": "offline data construction only; no model inference or training",
        "specification_count": len(specifications),
        "formula_families": sorted({spec["formula_family"] for spec in specifications}),
        "synthetic": synthetic_validation,
        "real": real_validation,
        "parameter_contrast_coverage": parameter_coverage,
        "combined": {
            "trajectory_count": len(synthetic) + len(real),
            "all_online_oracle_agree": True,
            "rtamt_max_robustness_difference": max(
                synthetic_validation["rtamt_max_robustness_difference"],
                real_validation["rtamt_max_robustness_difference"],
            ),
        },
        "review": {
            "independently_reviewed_specifications": reviewed,
            "pending_independent_review_specifications": len(specifications) - reviewed,
            "all_splits_frozen": False,
            "structure_split_available": False,
            "o7_final_contract_frozen": False,
        },
        "gates": {
            "stage2_v0_machine_foundation": True,
            "stage2_v0_final_dataset": False,
            "reason_final_gate_is_closed": [
                "independent human semantic review is incomplete",
                "O7 formula-family and split decisions are not frozen",
                "the current single-family fragment cannot support a structure split",
            ],
        },
    }
    coverage_path = generated / "coverage.json"
    _write_json(coverage_path, coverage)
    artifact_paths = [synthetic_path, real_path, label_path, coverage_path]
    manifest = {
        "schema_version": 1,
        "artifacts": {
            path.relative_to(root).as_posix(): {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in artifact_paths
        },
    }
    _write_json(generated / "manifest.json", manifest)
    return coverage


__all__ = [
    "BENCHMARK_ROOT",
    "build_benchmark",
    "generate_synthetic",
    "import_real_trajectories",
    "parameter_contrast_coverage",
    "validate_benchmark_contract",
    "validate_trajectories",
]
