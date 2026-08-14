"""Frozen, model-independent selection of the Stage II real-policy corpus."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

from safety_stl.stage2_formula import evaluate_specification_trace


CONDITIONS = ("task_only", "native_cost", "gold_stl_cost")
TRAINING_SEEDS = (1101, 2202, 3303, 4404, 5505)
STRATA = ("no_missed", "single_deadline", "multiple_deadline", "with_terminal_unresolved")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _int(value: Any) -> int:
    return int(float(value))


def outcome_stratum(row: Mapping[str, Any]) -> str:
    deadline = _int(row["deadline_violation_count"])
    unresolved = _int(row["terminal_unresolved_count"])
    if deadline + unresolved == 0:
        return "no_missed"
    if unresolved > 0:
        return "with_terminal_unresolved"
    if deadline == 1:
        return "single_deadline"
    return "multiple_deadline"


def select_stratified_real_episodes(
    episode_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Select one deterministic episode per condition/seed/outcome stratum."""

    grouped: MutableMapping[Tuple[str, int, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in episode_rows:
        condition = str(row["condition"])
        if condition not in CONDITIONS:
            continue
        training_seed = _int(row["training_seed"])
        grouped[(condition, training_seed, outcome_stratum(row))].append(row)
    selected: List[Dict[str, Any]] = []
    for condition in CONDITIONS:
        for training_seed in TRAINING_SEEDS:
            for stratum in STRATA:
                candidates = grouped[(condition, training_seed, stratum)]
                if not candidates:
                    raise ValueError(
                        f"real-corpus stratum is empty: {condition}/{training_seed}/{stratum}",
                    )
                row = min(candidates, key=lambda value: _int(value["evaluation_seed"]))
                selected.append(
                    {
                        "condition": condition,
                        "training_seed": training_seed,
                        "evaluation_seed": _int(row["evaluation_seed"]),
                        "outcome_stratum": stratum,
                        "episode_length": _int(row["episode_length"]),
                        "deadline_violation_count": _int(row["deadline_violation_count"]),
                        "terminal_unresolved_count": _int(row["terminal_unresolved_count"]),
                        "selection_rule": (
                            "lowest evaluation seed within each frozen "
                            "condition/training-seed/outcome stratum"
                        ),
                    },
                )
    if len(selected) != 60 or len({tuple(row[key] for key in ("condition", "training_seed", "evaluation_seed")) for row in selected}) != 60:
        raise AssertionError("stratified real corpus must contain 60 distinct episodes")
    return selected


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            count += 1
    return count


def extract_real_policy_corpus(
    full_geometry_path: Path,
    episode_rows_path: Path,
    specifications: Sequence[Mapping[str, Any]],
    output_root: Path,
    *,
    include_held_out_labels: bool = False,
) -> Dict[str, Any]:
    """Extract 60 traces and label only review-authorized specification splits."""

    with episode_rows_path.open("r", newline="", encoding="utf-8") as handle:
        selection = select_stratified_real_episodes(list(csv.DictReader(handle)))
    selected_keys = {
        (row["condition"], row["training_seed"], row["evaluation_seed"]): row
        for row in selection
    }
    grouped: MutableMapping[Tuple[str, int, int], List[Dict[str, Any]]] = defaultdict(list)
    with gzip.open(full_geometry_path, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (str(row["condition"]), _int(row["training_seed"]), _int(row["evaluation_seed"]))
            if key in selected_keys:
                grouped[key].append(dict(row))
    if set(grouped) != set(selected_keys):
        missing = sorted(set(selected_keys) - set(grouped))
        raise ValueError(f"selected real-policy traces missing from spatial replay: {missing}")

    full_geometry_sha256 = _sha256(full_geometry_path)
    episode_rows_sha256 = _sha256(episode_rows_path)
    raw_records = []
    for key in sorted(grouped, key=lambda item: (CONDITIONS.index(item[0]), item[1], item[2])):
        rows = sorted(grouped[key], key=lambda row: _int(row["sample_index"]))
        expected = list(range(len(rows)))
        if [_int(row["sample_index"]) for row in rows] != expected:
            raise ValueError(f"non-contiguous real-policy trace: {key}")
        selection_row = selected_keys[key]
        if len(rows) != selection_row["episode_length"] + 1:
            raise ValueError(f"real-policy trace length mismatch: {key}")
        trajectory_id = f"real60__{key[0]}__train-{key[1]}__eval-{key[2]}"
        raw_records.append(
            {
                "trajectory_id": trajectory_id,
                "source": {
                    **selection_row,
                    "full_geometry_path": str(full_geometry_path),
                    "full_geometry_sha256": full_geometry_sha256,
                    "episode_rows_path": str(episode_rows_path),
                    "episode_rows_sha256": episode_rows_sha256,
                },
                "samples": [
                    {
                        "sample_index": _int(row["sample_index"]),
                        "distance": float(row["public_lidar_distance"]),
                        "reward": float(row["reward"]),
                        "native_cost": float(row["native_cost"]),
                        "terminated": row["terminated"].lower() == "true",
                        "truncated": row["truncated"].lower() == "true",
                    }
                    for row in rows
                ],
            },
        )

    held_out = [
        spec for spec in specifications if spec["split"] in {"parameter_test", "structure_test"}
    ]
    all_held_out_reviewed = all(
        spec["review_status"] == "independently_reviewed" for spec in held_out
    )
    coverage = _read_json(output_root / "coverage.json")
    contrast_coverage = coverage.get("parameter_contrast_coverage", {})
    alias_amendment_complete = int(contrast_coverage.get("missing_witness_count", 0)) == 0
    if include_held_out_labels and not all_held_out_reviewed:
        raise PermissionError("held-out Gold labels remain closed until independent review")
    if include_held_out_labels and not alias_amendment_complete:
        raise PermissionError("held-out Gold labels remain closed until alias amendment")
    allowed_splits = {"train", "validation"}
    if include_held_out_labels:
        allowed_splits.update({"parameter_test", "structure_test"})
    label_records = []
    machine_review_label_record_count = 0
    max_rtamt_difference = 0.0
    for raw in raw_records:
        distances = [float(sample["distance"]) for sample in raw["samples"]]
        terminated = [bool(sample["terminated"]) for sample in raw["samples"]]
        truncated = [bool(sample["truncated"]) for sample in raw["samples"]]
        for spec in specifications:
            labels = evaluate_specification_trace(spec, distances, terminated, truncated)
            machine_review_label_record_count += 1
            max_rtamt_difference = max(
                max_rtamt_difference,
                float(labels["rtamt_max_robustness_difference"]),
            )
            if spec["split"] not in allowed_splits:
                continue
            label_records.append(
                {
                    "trajectory_id": raw["trajectory_id"],
                    "spec_id": spec["spec_id"],
                    "split": spec["split"],
                    "gold_labels": labels,
                },
            )

    selection_path = output_root / "real_corpus_selection.json"
    raw_path = output_root / "real_policy_corpus.jsonl"
    label_path = output_root / "real_policy_train_validation_labels.jsonl"
    schema_path = output_root / "real_policy_corpus_schema.json"
    _write_json(selection_path, selection)
    _write_jsonl(raw_path, raw_records)
    _write_jsonl(label_path, label_records)
    _write_json(
        schema_path,
        {
            "schema_version": 1,
            "trajectory_fields": ["trajectory_id", "source", "samples"],
            "sample_fields": [
                "sample_index",
                "distance",
                "reward",
                "native_cost",
                "terminated",
                "truncated",
            ],
            "selection_strata": list(STRATA),
            "selection_count_per_condition": 20,
            "held_out_label_policy": (
                "forbidden_until_all_held_out_records_are_reviewed_and_alias_amendment_passes"
            ),
        },
    )
    manifest = {
        "schema_version": 1,
        "trajectory_count": len(raw_records),
        "sample_count": sum(len(row["samples"]) for row in raw_records),
        "label_record_count": len(label_records),
        "machine_review_label_record_count": machine_review_label_record_count,
        "labeled_splits": sorted(allowed_splits),
        "held_out_labels_released": bool(include_held_out_labels),
        "all_held_out_reviewed": all_held_out_reviewed,
        "alias_amendment_complete": alias_amendment_complete,
        "rtamt_max_robustness_difference": max_rtamt_difference,
        "inputs": {
            "full_geometry.csv.gz": {
                "path": str(full_geometry_path),
                "sha256": full_geometry_sha256,
                "bytes": full_geometry_path.stat().st_size,
            },
            "episode_records.csv": {
                "path": str(episode_rows_path),
                "sha256": episode_rows_sha256,
                "bytes": episode_rows_path.stat().st_size,
            },
        },
        "artifacts": {
            path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in (selection_path, raw_path, label_path, schema_path)
        },
    }
    _write_json(output_root / "real_corpus_manifest.json", manifest)
    return manifest


__all__ = [
    "CONDITIONS",
    "STRATA",
    "extract_real_policy_corpus",
    "outcome_stratum",
    "select_stratified_real_episodes",
]
