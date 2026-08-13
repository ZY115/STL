"""Evaluate Stage II prediction files against versioned Gold trace labels."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

from safety_stl.stage2_specifications import compile_typed_ast


BOUNDARY_TAGS = {
    "exact_deadline",
    "one_step_late",
    "terminal_unresolved",
    "warning_equality",
    "safe_equality",
}
FORMULA_PATTERN = re.compile(r"^(?:G|F_|\().+")


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, Mapping):
                raise ValueError(f"{path}:{line_number} is not an object")
            rows.append(dict(value))
    return rows


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _confusion(predicted: Sequence[int], gold: Sequence[int]) -> Tuple[int, int, int, int]:
    if len(predicted) != len(gold):
        raise ValueError("prediction and Gold cost arrays differ in length")
    tp = sum(p == 1 and g == 1 for p, g in zip(predicted, gold))
    fp = sum(p == 1 and g == 0 for p, g in zip(predicted, gold))
    tn = sum(p == 0 and g == 0 for p, g in zip(predicted, gold))
    fn = sum(p == 0 and g == 1 for p, g in zip(predicted, gold))
    return tp, fp, tn, fn


def _event_errors(predicted: Sequence[int], gold: Sequence[int]) -> Dict[str, Any]:
    predicted_sorted = sorted(int(step) for step in predicted)
    gold_sorted = sorted(int(step) for step in gold)
    matched = min(len(predicted_sorted), len(gold_sorted))
    absolute_errors = [
        abs(predicted_sorted[index] - gold_sorted[index]) for index in range(matched)
    ]
    return {
        "matched_event_count": matched,
        "unmatched_predicted_event_count": len(predicted_sorted) - matched,
        "unmatched_gold_event_count": len(gold_sorted) - matched,
        "absolute_errors": absolute_errors,
    }


def evaluate_predictions(
    predictions: Sequence[Mapping[str, Any]],
    trajectories: Sequence[Mapping[str, Any]],
    specifications: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Compute trace metrics without granting predictions access to hidden Gold inputs."""

    if not predictions:
        raise ValueError("prediction collection is empty")
    trajectory_by_id = {str(row["trajectory_id"]): row for row in trajectories}
    specification_by_id = {str(row["spec_id"]): row for row in specifications}
    errors: List[str] = []
    seen_keys: set[tuple[str, str]] = set()
    methods = {str(row.get("method_id", "")) for row in predictions}
    if len(methods) != 1 or "" in methods:
        errors.append("one prediction file must contain exactly one non-empty method_id")

    tp = fp = tn = fn = 0
    event_error_values: List[int] = []
    matched_events = unmatched_predicted = unmatched_gold = 0
    exact_records = 0
    boundary_total = boundary_exact = 0
    terminal_total = terminal_exact = 0
    formula_total = formula_exact = 0
    formula_syntax_valid = 0
    structure_total = structure_exact = 0
    structure_compilable = 0
    normalized: MutableMapping[str, Dict[str, List[int]]] = defaultdict(dict)
    active_predictions: MutableMapping[str, Dict[str, List[int]]] = defaultdict(dict)
    prediction_fields = {
        "method_id",
        "trajectory_id",
        "language_variant",
        "predicted_costs",
        "predicted_event_steps",
        "predicted_active_obligation",
        "predicted_stl",
        "predicted_structure",
    }

    for prediction in predictions:
        trajectory_id = str(prediction.get("trajectory_id", ""))
        variant = str(prediction.get("language_variant", ""))
        key = (trajectory_id, variant)
        if set(prediction) != prediction_fields:
            errors.append(f"{key} fields differ from prediction schema")
            continue
        if key in seen_keys:
            errors.append(f"duplicate trajectory/language prediction: {key}")
            continue
        seen_keys.add(key)
        if trajectory_id not in trajectory_by_id:
            errors.append(f"unknown trajectory_id: {trajectory_id}")
            continue
        trajectory = trajectory_by_id[trajectory_id]
        spec = specification_by_id[str(trajectory["spec_id"])]
        valid_variants = {"canonical", *[f"paraphrase_{i}" for i in range(len(spec["paraphrases"]))]}
        if variant not in valid_variants:
            errors.append(f"invalid language variant for {trajectory_id}: {variant}")
        predicted_costs = prediction.get("predicted_costs")
        if not isinstance(predicted_costs, list) or any(value not in (0, 1) for value in predicted_costs):
            errors.append(f"{key} has invalid predicted_costs")
            continue
        gold_costs = [int(sample["stl_cost"]) for sample in trajectory["samples"]]
        if len(predicted_costs) != len(gold_costs):
            errors.append(f"{key} has {len(predicted_costs)} costs; expected {len(gold_costs)}")
            continue
        normalized[trajectory_id][variant] = [int(value) for value in predicted_costs]
        current_tp, current_fp, current_tn, current_fn = _confusion(predicted_costs, gold_costs)
        tp += current_tp
        fp += current_fp
        tn += current_tn
        fn += current_fn

        predicted_steps = prediction.get("predicted_event_steps")
        if not isinstance(predicted_steps, list) or any(
            isinstance(step, bool) or not isinstance(step, int) or step < 0 or step >= len(gold_costs)
            for step in predicted_steps
        ):
            errors.append(f"{key} has invalid predicted_event_steps")
            continue
        if len(set(predicted_steps)) != len(predicted_steps):
            errors.append(f"{key} repeats predicted event steps")
        positive_cost_steps = [index for index, value in enumerate(predicted_costs) if value]
        if sorted(predicted_steps) != positive_cost_steps:
            errors.append(
                f"{key} predicted_event_steps differ from positive predicted_costs",
            )
        gold_steps = [index for index, cost in enumerate(gold_costs) if cost]
        timing = _event_errors(predicted_steps, gold_steps)
        event_error_values.extend(timing["absolute_errors"])
        matched_events += timing["matched_event_count"]
        unmatched_predicted += timing["unmatched_predicted_event_count"]
        unmatched_gold += timing["unmatched_gold_event_count"]
        record_exact = predicted_costs == gold_costs and sorted(predicted_steps) == gold_steps
        exact_records += record_exact
        tags = set(trajectory["case_tags"])
        if tags & BOUNDARY_TAGS:
            boundary_total += 1
            boundary_exact += record_exact
        if "terminal_unresolved" in tags:
            terminal_total += 1
            terminal_exact += record_exact

        predicted_active = prediction.get("predicted_active_obligation")
        if predicted_active is not None:
            if not isinstance(predicted_active, list) or len(predicted_active) != len(gold_costs) or any(
                value not in (0, 1) for value in predicted_active
            ):
                errors.append(f"{key} has invalid predicted_active_obligation")
            else:
                active_predictions[trajectory_id][variant] = [int(value) for value in predicted_active]

        predicted_stl = prediction.get("predicted_stl")
        if predicted_stl is not None:
            if not isinstance(predicted_stl, str):
                errors.append(f"{key} predicted_stl must be a string or null")
                continue
            formula_total += 1
            formula_syntax_valid += FORMULA_PATTERN.fullmatch(str(predicted_stl).strip()) is not None
            formula_exact += str(predicted_stl).strip() == str(spec["gold_stl"])

        predicted_structure = prediction.get("predicted_structure")
        if predicted_structure is not None:
            structure_total += 1
            if not isinstance(predicted_structure, Mapping):
                errors.append(f"{key} predicted_structure must be an object or null")
            else:
                try:
                    compiled_structure = compile_typed_ast(predicted_structure)
                except (KeyError, TypeError, ValueError):
                    compiled_structure = None
                structure_compilable += compiled_structure is not None
                structure_exact += predicted_structure == spec["typed_ast"]
                if predicted_stl is not None and compiled_structure is not None:
                    if compiled_structure != str(predicted_stl).strip():
                        errors.append(f"{key} predicted typed AST and STL string disagree")

    if errors:
        raise ValueError("invalid Stage II predictions:\n- " + "\n- ".join(errors))

    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall > 0
        else None
    )
    paraphrase_groups = 0
    paraphrase_consistent = 0
    for variants in normalized.values():
        if len(variants) >= 2:
            paraphrase_groups += 1
            values = list(variants.values())
            paraphrase_consistent += all(value == values[0] for value in values[1:])

    history_pairs: MutableMapping[str, List[Mapping[str, Any]]] = defaultdict(list)
    for trajectory in trajectories:
        if trajectory.get("history_pair_id") is not None:
            history_pairs[str(trajectory["history_pair_id"])].append(trajectory)
    history_pair_total = history_pair_correct = 0
    for pair in history_pairs.values():
        if len(pair) != 2:
            continue
        common_variants = set(active_predictions[pair[0]["trajectory_id"]]) & set(
            active_predictions[pair[1]["trajectory_id"]],
        )
        for variant in common_variants:
            anchor = int(pair[0]["history_anchor_step"])
            predicted_states = {
                active_predictions[trajectory["trajectory_id"]][variant][anchor]
                for trajectory in pair
            }
            gold_states = {
                int(trajectory["gold_labels"]["online"]["states"][anchor] in {"pending", "overdue"})
                for trajectory in pair
            }
            history_pair_total += 1
            history_pair_correct += predicted_states == gold_states == {0, 1}

    total = tp + fp + tn + fn
    return {
        "schema_version": 1,
        "method_id": next(iter(methods)),
        "prediction_record_count": len(predictions),
        "trace_cost": {
            "true_positive": tp,
            "false_positive": fp,
            "true_negative": tn,
            "false_negative": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "false_negative_rate": _safe_ratio(fn, fn + tp),
            "false_positive_rate": _safe_ratio(fp, fp + tn),
            "accuracy": _safe_ratio(tp + tn, total),
            "exact_record_rate": _safe_ratio(exact_records, len(predictions)),
        },
        "event_timing": {
            "matched_event_count": matched_events,
            "unmatched_predicted_event_count": unmatched_predicted,
            "unmatched_gold_event_count": unmatched_gold,
            "mean_absolute_error_steps": (
                sum(event_error_values) / len(event_error_values) if event_error_values else None
            ),
        },
        "boundary_accuracy": _safe_ratio(boundary_exact, boundary_total),
        "terminal_unresolved_accuracy": _safe_ratio(terminal_exact, terminal_total),
        "paraphrase_consistency": _safe_ratio(paraphrase_consistent, paraphrase_groups),
        "history_state_minimal_pair_accuracy": _safe_ratio(history_pair_correct, history_pair_total),
        "formula": {
            "syntax_validity": _safe_ratio(formula_syntax_valid, formula_total),
            "exact_match": _safe_ratio(formula_exact, formula_total),
        },
        "structured_meaning": {
            "compilable_rate": _safe_ratio(structure_compilable, structure_total),
            "exact_record_accuracy": _safe_ratio(structure_exact, structure_total),
        },
        "coverage": {
            "boundary_prediction_records": boundary_total,
            "terminal_unresolved_prediction_records": terminal_total,
            "paraphrase_groups": paraphrase_groups,
            "history_state_pair_variants": history_pair_total,
            "formula_prediction_records": formula_total,
            "structured_prediction_records": structure_total,
        },
        "notes": [
            "Formula exact match is diagnostic and is not semantic equivalence.",
            "History-pair accuracy requires optional predicted_active_obligation outputs.",
            "D37 admission thresholds are frozen; held-out evaluation remains review-gated.",
        ],
    }


def evaluate_prediction_file(
    prediction_path: Path,
    trajectory_paths: Sequence[Path],
    specification_path: Path,
) -> Dict[str, Any]:
    predictions = _read_jsonl(prediction_path)
    trajectories = [row for path in trajectory_paths for row in _read_jsonl(path)]
    specifications = json.loads(specification_path.read_text(encoding="utf-8"))
    return evaluate_predictions(predictions, trajectories, specifications)


__all__ = ["evaluate_prediction_file", "evaluate_predictions"]
