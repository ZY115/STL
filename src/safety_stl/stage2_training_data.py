"""Leakage-safe synthetic train/validation data for frozen Stage II-A methods."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

from safety_stl.stage2_formula import evaluate_specification_trace


GENERATION_SEED = 20260812
TRACE_LENGTH = 128
FORMAL_PAIRS_PER_TRAIN_SPEC = 500
DIRECT_TRACES_PER_TRAIN_SPEC = 100
DIRECT_TRACES_PER_VALIDATION_SPEC = 50


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            count += 1
    return count


def _recovery_text(spec: Mapping[str, Any], index: int) -> str:
    p = spec["parameter_values"]
    subjects = (
        "the agent",
        "the point robot",
        "the navigating agent",
        "this agent",
        "the controlled point agent",
    )
    entries = (
        "newly enters closer than",
        "begins a warning episode below",
        "crosses from inactive status to under",
        "first moves inside the warning threshold of",
        "starts a new warning by falling below",
    )
    recoveries = (
        "reach at least",
        "recover to no less than",
        "return to a distance of at least",
        "move back to",
        "attain a nearest-hazard distance of",
    )
    deadline_phrases = (
        "within {deadline} environment steps",
        "no later than {deadline} steps afterward",
        "by the inclusive {deadline}-step deadline",
        "during the next {deadline} steps, counting the deadline sample",
    )
    subject = subjects[index % len(subjects)]
    entry = entries[(index // len(subjects)) % len(entries)]
    recovery = recoveries[(index // 25) % len(recoveries)]
    deadline_phrase = deadline_phrases[(index // 125) % len(deadline_phrases)].format(
        deadline=p["deadline_steps"],
    )
    text = (
        f"Whenever {subject} {entry} {float(p['d_warn']):.2f} simulator units from the nearest "
        f"hazard, {subject} must {recovery} {float(p['d_safe']):.2f} simulator units and {deadline_phrase}."
    )
    if spec["formula_family"] == "recovery_plus_persistence":
        text = text[:-1] + (
            f", then continuously maintain that safe distance from the recovery sample through "
            f"{int(p['persistence_steps'])} further environment steps, inclusively."
        )
    return text


def _avoidance_text(spec: Mapping[str, Any], index: int) -> str:
    p = spec["parameter_values"]
    verbs = ("remain", "stay", "keep itself", "continue", "be maintained")
    quantifiers = ("at every sample", "throughout all samples", "without exception", "for each sample")
    order = index % 2
    core = (
        f"{verbs[index % len(verbs)]} at least {float(p['avoidance_threshold']):.2f} simulator units "
        f"from the nearest hazard {quantifiers[(index // len(verbs)) % len(quantifiers)]} from "
        f"environment step 0 through step {int(p['avoidance_horizon_steps'])}, with both endpoints included"
    )
    if order == 0:
        return f"The agent must {core}."
    return f"During the declared bounded interval, require the agent to {core}."


def render_augmented_language(spec: Mapping[str, Any], index: int) -> str:
    """Render one deterministic meaning-preserving controlled-language variant."""

    family = str(spec["formula_family"])
    if family in {"hysteretic_bounded_recovery", "recovery_plus_persistence"}:
        base = _recovery_text(spec, index)
    elif family == "bounded_avoidance":
        base = _avoidance_text(spec, index)
    elif family == "conjunction":
        recovery_clause = _recovery_text(spec, index)
        if recovery_clause.startswith("Whenever "):
            recovery_clause = recovery_clause[len("Whenever ") :]
        base = (
            "Both complete clauses are required: (A) "
            + recovery_clause
            + " (B) "
            + _avoidance_text(spec, index + 7)
        )
    else:
        raise ValueError("formal train augmentation may use only D37 train structures")
    return f"Controlled requirement {index + 1:03d}: {base}"


def generate_formal_training_pairs(
    specifications: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    train_specs = [spec for spec in specifications if spec["split"] == "train"]
    if len(train_specs) != 20 or any(spec["formula_family"] == "disjunction" for spec in train_specs):
        raise ValueError("formal generation requires the frozen 20-spec non-OR train split")
    records = []
    for spec in train_specs:
        for index in range(FORMAL_PAIRS_PER_TRAIN_SPEC):
            records.append(
                {
                    "pair_id": f"formal-train__{spec['spec_id']}__{index:03d}",
                    "spec_id": spec["spec_id"],
                    "split": "train",
                    "controlled_natural_language": render_augmented_language(spec, index),
                    "target_typed_ast": spec["typed_ast"],
                    "target_stl": spec["gold_stl"],
                    "generation_seed": GENERATION_SEED,
                    "template_index": index,
                },
            )
    if len(records) != 10000:
        raise AssertionError("formal training data must contain exactly 10,000 pairs")
    if len({row["controlled_natural_language"] for row in records}) != len(records):
        raise AssertionError("formal training language records must be unique")
    return records


def _trace_constants(spec: Mapping[str, Any]) -> Tuple[float, float, float, int]:
    p = spec["parameter_values"]
    thresholds = [
        float(p[key])
        for key in ("d_warn", "d_safe", "avoidance_threshold")
        if key in p
    ]
    high = min(max(thresholds) + 0.20, 2.95)
    low = max(min(thresholds) - 0.02, 0.0)
    if "d_warn" in p:
        mid = (float(p["d_warn"]) + float(p["d_safe"])) / 2.0
        horizon = int(p["deadline_steps"]) + int(p.get("persistence_steps", 0))
    else:
        mid = high
        horizon = int(p["avoidance_horizon_steps"])
    return low, mid, high, horizon


def _direct_distance_trace(
    spec: Mapping[str, Any],
    *,
    positive_event: bool,
    rng: np.random.Generator,
) -> List[float]:
    low, mid, high, horizon = _trace_constants(spec)
    values = np.full(TRACE_LENGTH, high, dtype=np.float64)
    jitter = rng.uniform(-0.004, 0.004, size=TRACE_LENGTH)
    values += jitter
    if not positive_event:
        return values.clip(0.0, 3.0).tolist()
    family = str(spec["formula_family"])
    if family in {"bounded_avoidance", "conjunction"}:
        upper = int(spec["parameter_values"].get("avoidance_horizon_steps", 10))
        event_step = int(rng.integers(0, min(upper, TRACE_LENGTH - 1) + 1))
        values[event_step] = low
    elif family in {"hysteretic_bounded_recovery", "recovery_plus_persistence"}:
        trigger = 1
        decision = trigger + horizon
        if decision >= TRACE_LENGTH:
            raise ValueError(f"frozen direct trace exceeds 128 steps: {spec['spec_id']}")
        values[trigger : decision + 1] = mid
        values[trigger] = low
    else:
        raise ValueError("direct train generation may use only train/validation structures")
    return values.clip(0.0, 3.0).tolist()


def _remaining_targets(spec: Mapping[str, Any], states: Sequence[str]) -> List[float]:
    p = spec["parameter_values"]
    if spec["formula_family"] == "bounded_avoidance":
        horizon = int(p["avoidance_horizon_steps"])
    elif spec["formula_family"] == "recovery_plus_persistence":
        horizon = int(p["deadline_steps"]) + int(p["persistence_steps"])
    elif spec["formula_family"] == "conjunction":
        horizon = max(int(p["deadline_steps"]), int(p["avoidance_horizon_steps"]))
    else:
        horizon = int(p["deadline_steps"])
    active_indices = [index for index, state in enumerate(states) if "pending" in state]
    if not active_indices:
        return [0.0] * len(states)
    start = active_indices[0]
    return [
        max(0.0, min(1.0, (start + horizon - index) / horizon))
        if "pending" in state
        else 0.0
        for index, state in enumerate(states)
    ]


def generate_direct_traces(
    specifications: Sequence[Mapping[str, Any]],
    *,
    split: str,
) -> List[Dict[str, Any]]:
    if split not in {"train", "validation"}:
        raise ValueError("direct data generation is restricted to train/validation")
    selected = [spec for spec in specifications if spec["split"] == split]
    expected_specs = 20 if split == "train" else 8
    per_spec = DIRECT_TRACES_PER_TRAIN_SPEC if split == "train" else DIRECT_TRACES_PER_VALIDATION_SPEC
    if len(selected) != expected_specs or any(spec["formula_family"] == "disjunction" for spec in selected):
        raise ValueError("direct generation received an unexpected or held-out split")
    rng = np.random.default_rng(GENERATION_SEED + (0 if split == "train" else 1))
    records = []
    for spec in selected:
        for index in range(per_spec):
            positive = index % 2 == 0
            distances = _direct_distance_trace(spec, positive_event=positive, rng=rng)
            terminated = [False] * TRACE_LENGTH
            truncated = [False] * (TRACE_LENGTH - 1) + [True]
            labels = evaluate_specification_trace(spec, distances, terminated, truncated)
            costs = [int(value) for value in labels["oracle"]["costs"]]
            observed_positive = bool(sum(costs))
            if observed_positive != positive:
                raise AssertionError(
                    f"requested direct class does not match Gold label: {spec['spec_id']}/{index}",
                )
            states = [str(state) for state in labels["online"]["states"]]
            language_variant = index % 3
            language = (
                spec["canonical_natural_language"]
                if language_variant == 0
                else spec["paraphrases"][language_variant - 1]
            )
            records.append(
                {
                    "trace_id": f"direct-{split}__{spec['spec_id']}__{index:03d}",
                    "spec_id": spec["spec_id"],
                    "split": split,
                    "controlled_natural_language": language,
                    "language_variant": (
                        "canonical" if language_variant == 0 else f"paraphrase_{language_variant - 1}"
                    ),
                    "distances": distances,
                    "gold_costs": costs,
                    "gold_active_obligation": [int("pending" in state) for state in states],
                    "gold_remaining_fraction": _remaining_targets(spec, states),
                    "positive_event_case": positive,
                    "generation_seed": GENERATION_SEED,
                },
            )
    expected_count = 2000 if split == "train" else 400
    if len(records) != expected_count:
        raise AssertionError(f"{split} direct data must contain {expected_count} traces")
    positive_count = sum(row["positive_event_case"] for row in records)
    if positive_count * 2 != len(records):
        raise AssertionError("direct data must be exactly balanced by event presence")
    return records


def build_stage2_training_data(
    specifications: Sequence[Mapping[str, Any]],
    output_root: Path,
) -> Dict[str, Any]:
    """Write frozen bulk data locally and a compact hash manifest."""

    formal = generate_formal_training_pairs(specifications)
    direct_train = generate_direct_traces(specifications, split="train")
    direct_validation = generate_direct_traces(specifications, split="validation")
    paths = {
        "formal_train_pairs.jsonl": formal,
        "direct_train_traces.jsonl": direct_train,
        "direct_validation_traces.jsonl": direct_validation,
    }
    records = {}
    for name, rows in paths.items():
        path = output_root / name
        count = _write_jsonl(path, rows)
        records[name] = {"sha256": _sha256(path), "bytes": path.stat().st_size, "records": count}
    schema_path = output_root / "training_data_schema.json"
    _write_json(
        schema_path,
        {
            "schema_version": 1,
            "generation_seed": GENERATION_SEED,
            "formal_pair_count": 10000,
            "direct_train_trace_count": 2000,
            "direct_validation_trace_count": 400,
            "direct_trace_length": TRACE_LENGTH,
            "held_out_or_test_content": "prohibited",
            "supervision": {
                "formal": "train-split typed AST",
                "direct": "train/validation Gold cost, active and auxiliary remaining labels",
            },
        },
    )
    records[schema_path.name] = {
        "sha256": _sha256(schema_path),
        "bytes": schema_path.stat().st_size,
        "records": 1,
    }
    manifest = {
        "schema_version": 1,
        "generation_seed": GENERATION_SEED,
        "test_or_structure_split_record_count": 0,
        "artifacts": records,
    }
    _write_json(output_root / "training_data_manifest.json", manifest)
    return manifest


__all__ = [
    "DIRECT_TRACES_PER_TRAIN_SPEC",
    "DIRECT_TRACES_PER_VALIDATION_SPEC",
    "FORMAL_PAIRS_PER_TRAIN_SPEC",
    "GENERATION_SEED",
    "TRACE_LENGTH",
    "build_stage2_training_data",
    "generate_direct_traces",
    "generate_formal_training_pairs",
    "render_augmented_language",
]
