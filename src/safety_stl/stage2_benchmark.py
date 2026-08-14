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
from safety_stl.stage2_specifications import (
    FAMILY_NAMES,
    build_specifications,
    compile_typed_ast,
)
from safety_stl.stage2_formula import evaluate_specification_trace


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
    """Validate the complete frozen D37 contract without external schema tools."""

    benchmark = _load_json(root / "benchmark.json")
    specifications = _load_json(root / "specifications.json")
    reviews = _load_json(root / "reviews.json")
    errors: List[str] = []
    expected_families = list(FAMILY_NAMES.values())
    if benchmark.get("status") not in {
        "d37_40_item_contract_current_revision_reviewed_alias_amendment_pending",
        "d37_40_item_contract_fully_reviewed_alias_free",
    }:
        errors.append("benchmark status must identify the reviewed D37 amendment state")
    if benchmark.get("supported_fragment", {}).get("formula_families") != expected_families:
        errors.append("supported formula families differ from D37")
    if benchmark.get("draft_split_policy", {}).get("status") != "d37_split_frozen":
        errors.append("the D37 split must be frozen")
    if not isinstance(specifications, list) or len(specifications) != 40:
        errors.append("specifications.json must contain exactly 40 specifications")
        specifications = []

    seen_ids: set[str] = set()
    seen_language: set[str] = set()
    pair_splits: MutableMapping[str, set[str]] = defaultdict(set)
    expected_records = {row["spec_id"]: row for row in build_specifications()}
    family_counts: MutableMapping[str, int] = defaultdict(int)
    split_counts: MutableMapping[str, int] = defaultdict(int)
    for index, spec in enumerate(specifications):
        prefix = f"specification[{index}]"
        required = {
            "spec_id",
            "canonical_natural_language",
            "paraphrases",
            "typed_ast",
            "gold_stl",
            "formula_family",
            "grounding_schema",
            "parameter_values",
            "semantic_pair_id",
            "contrast_group_id",
            "semantic_contrast_type",
            "allowed_online_use",
            "online_use_status",
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
        if spec_id not in expected_records:
            errors.append(f"unexpected D37 specification ID: {spec_id}")
            continue
        expected = expected_records[spec_id]
        immutable_fields = required - {
            "annotation_author",
            "independent_reviewer",
            "review_status",
            "source_or_generation_record",
        }
        for field in immutable_fields:
            if spec[field] != expected[field]:
                errors.append(f"{spec_id} differs from D37 in {field}")
        try:
            compiled = compile_typed_ast(spec["typed_ast"])
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"{spec_id} has invalid typed AST: {error}")
        else:
            if compiled != spec["gold_stl"]:
                errors.append(f"{spec_id} typed AST does not compile to Gold STL")
        family_counts[str(spec["formula_family"])] += 1
        split_counts[str(spec["split"])] += 1
        grounding = spec["grounding_schema"]
        if grounding.get("signal_id") != "nearest_hazard_center_distance_public":
            errors.append(f"{spec_id} does not use the public Stage I distance signal")
        if spec["formula_family"] in {
            "hysteretic_bounded_recovery",
            "recovery_plus_persistence",
            "conjunction",
            "disjunction",
        }:
            if grounding.get("trigger_mode") != "hysteretic_warning_episode":
                errors.append(f"{spec_id} has incompatible trigger semantics")
            if grounding.get("deadline_inclusive") is not True:
                errors.append(f"{spec_id} must use an inclusive deadline")
        language_items = [spec["canonical_natural_language"], *spec["paraphrases"]]
        if len(spec["paraphrases"]) != 2 or len(set(language_items)) != 3:
            errors.append(f"{spec_id} needs exactly two distinct paraphrases")
        for language in language_items:
            normalized = " ".join(str(language).lower().split())
            if normalized in seen_language:
                errors.append(f"duplicate language item found in {spec_id}")
            seen_language.add(normalized)
        pair_splits[str(spec["semantic_pair_id"])].add(str(spec["split"]))
        if spec["review_status"] not in {
            "machine_validated_pending_independent_review",
            "independently_reviewed",
        }:
            errors.append(f"{spec_id} has an invalid review status")
        if spec["review_status"] == "independently_reviewed" and not spec["independent_reviewer"]:
            errors.append(f"{spec_id} claims review without naming the reviewer")
        if (
            spec["independent_reviewer"] is not None
            and spec["independent_reviewer"] == spec["annotation_author"]
        ):
            errors.append(f"{spec_id} reviewer is not independent from its author")

    leaking_pairs = sorted(pair for pair, splits in pair_splits.items() if len(splits) > 1)
    if leaking_pairs:
        errors.append(f"semantic pairs span multiple splits: {leaking_pairs}")
    if dict(family_counts) != {family: 8 for family in expected_families}:
        errors.append(f"formula-family counts differ from D37: {dict(family_counts)}")
    if dict(split_counts) != {
        "train": 20,
        "validation": 8,
        "parameter_test": 4,
        "structure_test": 8,
    }:
        errors.append(f"split counts differ from D37: {dict(split_counts)}")
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
        "family_counts": dict(family_counts),
        "split_counts": dict(split_counts),
        "all_held_out_reviewed": all(
            spec["review_status"] == "independently_reviewed"
            for spec in specifications
            if spec["split"] in {"parameter_test", "structure_test"}
        ),
    }


def _terminal_flags(length: int) -> tuple[List[bool], List[bool]]:
    return [False] * length, [False] * (length - 1) + [True]


def _synthetic_cases(spec: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Generate at least 12 deterministic boundary/history traces per family."""

    parameters = spec["parameter_values"]
    family = str(spec["formula_family"])
    has_recovery = family in {
        "hysteretic_bounded_recovery",
        "recovery_plus_persistence",
        "conjunction",
        "disjunction",
    }
    has_avoidance = family in {"bounded_avoidance", "conjunction", "disjunction"}
    warn = float(parameters.get("d_warn", 0.45))
    safe = float(parameters.get("d_safe", max(warn + 0.10, 0.55)))
    deadline = int(parameters.get("deadline_steps", 40))
    persistence = int(parameters.get("persistence_steps", 0))
    avoidance = float(parameters.get("avoidance_threshold", 0.20))
    avoidance_horizon = int(parameters.get("avoidance_horizon_steps", 20))
    high = min(max(safe, avoidance) + 0.15, 2.99)
    mid = (warn + safe) / 2.0
    warning_low = max(0.0, warn - 0.01)
    avoidance_low = max(0.0, avoidance - 0.01)
    common_low = min(warning_low, avoidance_low)
    complete_step = max(deadline + persistence + 3, avoidance_horizon + 2, 12)

    def padded(events: Mapping[int, float], final_step: int, default: float = high) -> List[float]:
        values = [default] * (final_step + 1)
        for step, value in events.items():
            if step < 0 or step > final_step:
                raise ValueError("synthetic event step lies outside its trace")
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

    add("vacuous", [high] * (complete_step + 1), ["vacuous", "no_trigger"])
    add(
        "on_time_recovery",
        padded({1: warning_low, 2: mid}, complete_step),
        ["trigger", "on_time_recovery"],
    )
    exact_events = {1: warning_low}
    for step in range(2, 1 + deadline):
        exact_events[step] = mid
    add(
        "exact_deadline_recovery",
        padded(exact_events, complete_step),
        ["trigger", "exact_deadline", "recovery_equality"],
    )
    late_events = dict(exact_events)
    late_events[1 + deadline] = mid
    add(
        "one_step_late",
        padded(late_events, complete_step),
        ["trigger", "deadline_violation", "one_step_late"],
    )
    add(
        "terminal_unresolved",
        [high, warning_low, mid],
        ["trigger", "terminal_unresolved", "finite_trace_boundary"],
    )
    add(
        "warning_equality_no_trigger",
        [high, warn, warn, high],
        ["warning_equality", "strict_warning_comparator", "no_trigger"],
    )
    add(
        "safe_equality_recovery",
        padded({1: warning_low, 2: safe}, complete_step),
        ["trigger", "safe_equality", "inclusive_recovery_comparator"],
    )
    add(
        "repeated_entry_while_pending",
        padded({1: warning_low, 2: warning_low, 3: warning_low}, complete_step),
        ["single_active_obligation", "repeated_unsafe_samples", "on_time_recovery"],
    )
    add(
        "retrigger_after_recovery",
        padded({1: warning_low, 3: warning_low}, complete_step),
        ["multiple_obligations", "retrigger_after_recovery"],
    )
    history_pair_id = f"{spec['spec_id']}__history-state-contrast"
    anchor = 6
    anchor_value = high if has_avoidance else mid
    add(
        "history_inactive",
        padded({anchor: anchor_value}, complete_step),
        ["history_contrast", "same_current_observation", "inactive_at_anchor"],
        history_pair_id=history_pair_id,
        history_anchor_step=anchor,
    )
    add(
        "history_pending",
        padded(
            {
                2: common_low,
                **(
                    {step: mid for step in range(3, anchor + 1)}
                    if not has_avoidance
                    else {anchor: anchor_value}
                ),
            },
            complete_step,
        ),
        ["history_contrast", "same_current_observation", "pending_at_anchor"],
        history_pair_id=history_pair_id,
        history_anchor_step=anchor,
    )

    persistence_start = 1 + deadline
    for label, offset in (
        ("first", 0),
        ("middle", persistence // 2),
        ("final", persistence),
    ):
        events = {1: warning_low}
        for step in range(2, persistence_start):
            events[step] = mid
        for step in range(persistence_start, persistence_start + persistence + 1):
            events[step] = safe
        events[persistence_start + offset] = mid
        add(
            f"persistence_break_{label}",
            padded(events, max(complete_step, persistence_start + persistence + 1)),
            ["persistence_boundary", f"persistence_break_{label}", "structure_contrast"],
        )

    for label, step in (
        ("first", 0),
        ("middle", avoidance_horizon // 2),
        ("final", avoidance_horizon),
    ):
        add(
            f"avoidance_violation_{label}",
            padded({step: avoidance_low}, complete_step),
            ["avoidance_boundary", f"avoidance_violation_{label}", "structure_contrast"],
        )
    add(
        "avoidance_equality",
        padded({avoidance_horizon // 2: avoidance}, complete_step),
        ["avoidance_equality", "comparator_equality"],
    )
    add(
        "recovery_holds_avoidance_fails",
        padded({1: common_low}, complete_step),
        ["boolean_distinguishing_witness", "recovery_holds", "avoidance_fails"],
    )
    if avoidance < warn:
        recovery_only_low = (avoidance + warn) / 2.0
        events = {1: recovery_only_low}
        for step in range(2, 1 + deadline + persistence + 1):
            events[step] = mid
        add(
            "avoidance_holds_recovery_fails",
            padded(events, complete_step),
            ["boolean_distinguishing_witness", "avoidance_holds", "recovery_fails"],
        )
    if not has_recovery:
        for case in cases:
            case["case_tags"].append("recovery_tags_not_applicable_to_family")
    if not has_avoidance:
        for case in cases:
            case["case_tags"].append("avoidance_tags_are_cross_family_stress_only")
    return cases


def _label_trace(
    distances: Sequence[float],
    terminated: Sequence[bool],
    truncated: Sequence[bool],
    specification: Mapping[str, Any],
) -> Dict[str, Any]:
    return evaluate_specification_trace(
        specification,
        distances,
        terminated,
        truncated,
    )


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
        spec,
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
                specification_by_id[spec_id],
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
    """Check D37 adjacent-parameter and same-index structure contrasts.

    Some frozen same-index combinations are logically aliased when the
    avoidance threshold is at least the warning threshold.  These pairs are
    reported rather than hidden or "repaired" after D37 was frozen.
    """

    by_id = {str(spec["spec_id"]): spec for spec in specifications}
    required_pairs: List[Tuple[str, str, str]] = []
    for prefix in ("br", "rp", "ba", "and", "or"):
        for index in range(1, 8):
            required_pairs.append(
                (f"{prefix}-v0-{index:03d}", f"{prefix}-v0-{index + 1:03d}", "adjacent_parameter"),
            )
    for index in range(1, 9):
        ids = [f"{prefix}-v0-{index:03d}" for prefix in ("br", "rp", "ba", "and", "or")]
        for first_id, second_id in combinations(ids, 2):
            required_pairs.append((first_id, second_id, "same_index_structure"))

    cache: Dict[Tuple[str, str], Tuple[Any, ...]] = {}

    def semantics(spec_id: str, record: Mapping[str, Any]) -> Tuple[Any, ...]:
        key = (spec_id, str(record["trajectory_id"]))
        if key not in cache:
            labels = _label_trace(
                [float(sample["distance"]) for sample in record["samples"]],
                [bool(sample["terminated"]) for sample in record["samples"]],
                [bool(sample["truncated"]) for sample in record["samples"]],
                by_id[spec_id],
            )
            cache[key] = (
                tuple(labels["oracle"]["violation_steps"]),
                tuple(labels["oracle"]["unresolved_steps"]),
                tuple(labels["oracle"]["costs"]),
            )
        return cache[key]

    witnesses = []
    missing = []
    for first_id, second_id, contrast_type in required_pairs:
        witness = None
        for record in records:
            if semantics(first_id, record) != semantics(second_id, record):
                witness = str(record["trajectory_id"])
                break
        if witness is not None:
            witnesses.append(
                {
                    "spec_pair": [first_id, second_id],
                    "contrast_type": contrast_type,
                    "witness_trajectory_id": witness,
                },
            )
            continue
        first = by_id[first_id]
        second = by_id[second_id]
        pair_families = {str(first["formula_family"]), str(second["formula_family"])}
        parameters = first["parameter_values"]
        alias_reason = None
        if pair_families == {"bounded_avoidance", "conjunction"}:
            companion = by_id[first_id.replace("ba-v0", "and-v0")]
            p = companion["parameter_values"]
            if float(p["avoidance_threshold"]) >= float(p["d_warn"]):
                alias_reason = "avoidance_implies_no_warning_so_conjunction_equals_avoidance"
        if pair_families == {"hysteretic_bounded_recovery", "disjunction"}:
            companion = by_id[first_id.replace("br-v0", "or-v0")]
            p = companion["parameter_values"]
            if float(p["avoidance_threshold"]) >= float(p["d_warn"]):
                alias_reason = "recovery_failure_implies_avoidance_failure_so_disjunction_equals_recovery"
        missing.append(
            {
                "spec_pair": [first_id, second_id],
                "contrast_type": contrast_type,
                "classified_logical_alias": alias_reason,
            },
        )
    unclassified = [row for row in missing if row["classified_logical_alias"] is None]
    return {
        "required_pair_count": len(required_pairs),
        "witness_count": len(witnesses),
        "missing_witness_count": len(missing),
        "unclassified_missing_witness_count": len(unclassified),
        "all_non_alias_pairs_have_distinguishing_trace": not unclassified,
        "witnesses": witnesses,
        "missing_or_aliased": missing,
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
    released_spec_ids = {
        str(spec["spec_id"])
        for spec in specifications
        if spec["split"] in {"train", "validation"}
    }
    released_synthetic = [
        record for record in synthetic if record["spec_id"] in released_spec_ids
    ]
    released_synthetic_validation = validate_trajectories(
        released_synthetic,
        specifications,
    )
    _write_jsonl(synthetic_path, released_synthetic)
    _write_jsonl(real_path, real)
    labels = [
        {
            "trajectory_id": record["trajectory_id"],
            "spec_id": record["spec_id"],
            "gold_labels": record["gold_labels"],
        }
        for record in [*synthetic, *real]
        if record["spec_id"] in released_spec_ids
    ]
    _write_jsonl(label_path, labels)
    reviewed = sum(review["status"] == "approved" for review in contract["reviews"])
    final_gate_reasons = []
    if reviewed != len(specifications):
        final_gate_reasons.append(
            f"{len(specifications) - reviewed} specifications require independent review",
        )
    if parameter_coverage["missing_witness_count"]:
        final_gate_reasons.append(
            "owner-selected alias parameter amendment has not reached zero missing witnesses",
        )
    final_dataset_ready = not final_gate_reasons
    coverage = {
        "schema_version": 1,
        "status": (
            "d37_40_item_alias_free_reviewed"
            if final_dataset_ready
            else "d37_40_item_current_revision_reviewed_alias_amendment_pending"
        ),
        "scope": "offline data construction only; no model inference or training",
        "specification_count": len(specifications),
        "formula_families": sorted({spec["formula_family"] for spec in specifications}),
        "synthetic_machine_review_all_40_specs": synthetic_validation,
        "synthetic_released_train_validation": released_synthetic_validation,
        "real": real_validation,
        "parameter_contrast_coverage": parameter_coverage,
        "combined": {
            "released_trajectory_count": len(released_synthetic) + len(real),
            "machine_review_trajectory_count": len(synthetic) + len(real),
            "all_online_oracle_agree": True,
            "rtamt_max_robustness_difference": max(
                synthetic_validation["rtamt_max_robustness_difference"],
                real_validation["rtamt_max_robustness_difference"],
            ),
        },
        "review": {
            "independently_reviewed_specifications": reviewed,
            "pending_independent_review_specifications": len(specifications) - reviewed,
            "all_splits_frozen": True,
            "structure_split_available": True,
            "o7_final_contract_frozen": True,
            "held_out_gold_labels_released_to_model_code": False,
            "released_gold_label_splits": ["train", "validation"],
        },
        "gates": {
            "stage2_v0_machine_foundation": True,
            "stage2_v0_d37_implementation": True,
            "stage2_v0_final_dataset": final_dataset_ready,
            "reason_final_gate_is_closed": final_gate_reasons,
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
