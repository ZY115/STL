"""Resumable Stage II-A train/validation runners for the frozen D37 methods."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader, Dataset

from safety_stl.stage2_models import (
    CurrentObservationDirectModel,
    HistoryAwareDirectModel,
    direct_multitask_loss,
)
from safety_stl.stage2_specifications import compile_typed_ast


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPOSITORY_ROOT / "configs/stage2_v0/baselines.yaml"
DEFAULT_BENCHMARK = REPOSITORY_ROOT / "benchmarks/stage2_v0"
METHODS = ("formal", "current_direct", "history_direct")
FORMAL_SIGNAL_REGISTRY = (
    "Typed public signal registry: nearest_hazard_center_distance_public is a "
    "float distance in metres reconstructed causally from hazards_lidar; temporal "
    "bounds are integer environment steps. Requirement: "
)
FORMAL_JSON_TOKENS = ("{", "}", ",", "[", "]")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, Mapping):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            records.append(dict(value))
    return records


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_progress(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, Mapping):
        raise ValueError(f"configuration must be a mapping: {path}")
    return dict(value)


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPOSITORY_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _set_seed(seed: int, deterministic: bool) -> None:
    if deterministic:
        # This must be set before the first CUDA context/CuBLAS operation.
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if deterministic and torch.cuda.is_available():
        # The fused attention kernels used by transformer encoders are not
        # deterministic in this PyTorch/CUDA combination. Force the math path.
        torch.backends.cuda.enable_flash_sdp(False)
        torch.backends.cuda.enable_mem_efficient_sdp(False)
        torch.backends.cuda.enable_math_sdp(True)
    torch.use_deterministic_algorithms(deterministic, warn_only=False)


def _atomic_torch_save(value: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(dict(value), temporary)
    os.replace(temporary, path)


def _parameter_count(model: torch.nn.Module) -> Dict[str, int]:
    total = sum(parameter.numel() for parameter in model.parameters())
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    return {"total": total, "trainable": trainable}


def _assert_finite(value: float, label: str) -> None:
    if not math.isfinite(float(value)):
        raise FloatingPointError(f"non-finite {label}: {value}")


def _device(config: Mapping[str, Any]) -> torch.device:
    declared = str(config["training_protocol"]["device"])
    if declared.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("Stage II-A is configured for CUDA but torch.cuda.is_available() is false")
    return torch.device(declared)


def _dataset_hashes(benchmark_root: Path) -> Dict[str, str]:
    benchmark_root = benchmark_root.resolve()
    paths = (
        benchmark_root / "specifications.json",
        benchmark_root / "reviews.json",
        benchmark_root / "generated/training_data_manifest.json",
        benchmark_root / "generated/formal_train_pairs.jsonl",
        benchmark_root / "generated/direct_train_traces.jsonl",
        benchmark_root / "generated/direct_validation_traces.jsonl",
    )
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Stage II-A data are incomplete: {missing}")
    manifest = _read_json(benchmark_root / "generated/training_data_manifest.json")
    for name, record in manifest["artifacts"].items():
        path = benchmark_root / "generated" / name
        if not path.is_file() or sha256_file(path) != str(record["sha256"]):
            raise RuntimeError(f"Stage II-A data hash mismatch: {path}")
    return {path.relative_to(REPOSITORY_ROOT).as_posix(): sha256_file(path) for path in paths}


class _RecordDataset(Dataset):
    def __init__(self, records: Sequence[Mapping[str, Any]]) -> None:
        self.records = list(records)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> Mapping[str, Any]:
        return self.records[index]


def _json_ast(ast: Mapping[str, Any]) -> str:
    return json.dumps(ast, sort_keys=True, separators=(",", ":"))


def formal_source_text(language: str) -> str:
    """Attach the same frozen public signal registry to every formal input."""

    return FORMAL_SIGNAL_REGISTRY + str(language)


def configure_formal_json_tokens(tokenizer: Any, model: torch.nn.Module) -> int:
    """Make JSON structure losslessly representable by the T5 tokenizer."""

    added = int(tokenizer.add_tokens(list(FORMAL_JSON_TOKENS)))
    current_embeddings = int(model.get_input_embeddings().num_embeddings)
    if len(tokenizer) > current_embeddings:
        model.resize_token_embeddings(len(tokenizer))
    probe = '{"node_type":"predicate","threshold":0.5}'
    decoded = tokenizer.decode(tokenizer(probe)["input_ids"], skip_special_tokens=True)
    if json.loads(decoded) != json.loads(probe):
        raise RuntimeError(f"formal tokenizer is not JSON-lossless after extension: {decoded!r}")
    return added


def _formal_validation_records(specifications: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    records = []
    for spec in specifications:
        if spec["split"] != "validation":
            continue
        for variant_index, language in enumerate(
            [spec["canonical_natural_language"], *spec["paraphrases"]],
        ):
            records.append(
                {
                    "pair_id": f"formal-validation__{spec['spec_id']}__{variant_index}",
                    "spec_id": spec["spec_id"],
                    "controlled_natural_language": language,
                    "target_typed_ast": spec["typed_ast"],
                    "target_stl": spec["gold_stl"],
                },
            )
    if len(records) != 24:
        raise AssertionError("formal validation must contain eight specs times three wordings")
    return records


def _formal_collator(tokenizer: Any, max_source: int, max_target: int):
    def collate(records: Sequence[Mapping[str, Any]]) -> Dict[str, torch.Tensor]:
        inputs = tokenizer(
            [formal_source_text(str(record["controlled_natural_language"])) for record in records],
            padding=True,
            truncation=True,
            max_length=max_source,
            return_tensors="pt",
        )
        targets = tokenizer(
            text_target=[_json_ast(record["target_typed_ast"]) for record in records],
            padding=True,
            truncation=True,
            max_length=max_target,
            return_tensors="pt",
        )
        labels = targets["input_ids"]
        labels[labels == tokenizer.pad_token_id] = -100
        return {**inputs, "labels": labels}

    return collate


@torch.no_grad()
def _evaluate_formal(
    model: torch.nn.Module,
    tokenizer: Any,
    records: Sequence[Mapping[str, Any]],
    device: torch.device,
    max_source: int,
    max_target: int,
) -> Dict[str, Any]:
    model.eval()
    exact = compilable = formula_exact = 0
    predictions = []
    for record in records:
        encoded = tokenizer(
            formal_source_text(str(record["controlled_natural_language"])),
            truncation=True,
            max_length=max_source,
            return_tensors="pt",
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}
        output = model.generate(**encoded, max_new_tokens=max_target, num_beams=1, do_sample=False)
        text = tokenizer.decode(output[0], skip_special_tokens=True)
        predicted_ast = None
        predicted_stl = None
        try:
            parsed = json.loads(text)
            if isinstance(parsed, Mapping):
                predicted_ast = dict(parsed)
                predicted_stl = compile_typed_ast(predicted_ast)
                compilable += 1
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass
        ast_exact = predicted_ast == record["target_typed_ast"]
        stl_exact = predicted_stl == record["target_stl"]
        exact += ast_exact
        formula_exact += stl_exact
        predictions.append(
            {
                "pair_id": record["pair_id"],
                "spec_id": record["spec_id"],
                "raw_generation": text,
                "predicted_typed_ast": predicted_ast,
                "predicted_stl": predicted_stl,
                "typed_ast_exact": ast_exact,
                "stl_exact": stl_exact,
            },
        )
    count = len(records)
    return {
        "typed_ast_exact_accuracy": exact / count,
        "compilable_rate": compilable / count,
        "compiled_stl_exact_accuracy": formula_exact / count,
        "predictions": predictions,
    }


def _formal_train(
    *,
    config: Mapping[str, Any],
    benchmark_root: Path,
    run_dir: Path,
    seed: int,
    dry_run: bool,
    resume: bool,
) -> Dict[str, Any]:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    method = config["methods"]["formal_path"]
    train_config = dict(config["training_protocol"]["formal_path"])
    model_name = str(method["pretrained_model"])
    device = _device(config)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    added_json_tokens = configure_formal_json_tokens(tokenizer, model)
    model = model.to(device)
    train_records = _read_jsonl(benchmark_root / "generated/formal_train_pairs.jsonl")
    validation_records = _formal_validation_records(_read_json(benchmark_root / "specifications.json"))
    if dry_run:
        train_records = train_records[:16]
        validation_records = validation_records[:3]
        train_config["epochs"] = 1
    collator = _formal_collator(
        tokenizer,
        int(train_config["max_source_tokens"]),
        int(train_config["max_target_tokens"]),
    )
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        _RecordDataset(train_records),
        batch_size=int(train_config["batch_size"]),
        shuffle=True,
        generator=generator,
        collate_fn=collator,
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(train_config["learning_rate"]),
        weight_decay=float(train_config["weight_decay"]),
    )
    latest_path = run_dir / "latest.pt"
    best_path = run_dir / "best.pt"
    progress_path = run_dir / "progress.csv"
    start_epoch = 0
    best_metric = -math.inf
    progress: List[Dict[str, Any]] = []
    if resume and latest_path.is_file():
        checkpoint = torch.load(latest_path, map_location=device)
        model.load_state_dict(checkpoint["model"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        start_epoch = int(checkpoint["epoch"]) + 1
        best_metric = float(checkpoint["best_metric"])
        if "data_loader_generator_state" in checkpoint:
            generator.set_state(checkpoint["data_loader_generator_state"])
        else:
            # Historical recovery path for checkpoints created before the RNG
            # state was recorded. RandomSampler consumes two randperm calls
            # for a full-length, no-replacement epoch in torch 2.4.1.
            for _ in range(start_epoch):
                torch.randperm(len(train_records), generator=generator)
                torch.randperm(len(train_records), generator=generator)
        if progress_path.is_file():
            with progress_path.open("r", newline="", encoding="utf-8") as handle:
                progress = list(csv.DictReader(handle))
    accumulation = int(train_config["gradient_accumulation_steps"])
    global_updates = (
        int(checkpoint.get("optimizer_updates", start_epoch * math.ceil(len(loader) / accumulation)))
        if start_epoch
        else 0
    )
    started = time.monotonic()
    tokenizer.save_pretrained(run_dir / "tokenizer")
    for epoch in range(start_epoch, int(train_config["epochs"])):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        epoch_loss = 0.0
        for batch_index, batch in enumerate(loader):
            batch = {key: value.to(device) for key, value in batch.items()}
            output = model(**batch)
            loss = output.loss / accumulation
            _assert_finite(float(loss.detach().cpu()), "formal loss")
            loss.backward()
            epoch_loss += float(loss.detach().cpu()) * accumulation
            if (batch_index + 1) % accumulation == 0 or batch_index + 1 == len(loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), float(config["training_protocol"]["gradient_clip_norm"]))
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                global_updates += 1
        validation = _evaluate_formal(
            model,
            tokenizer,
            validation_records,
            device,
            int(train_config["max_source_tokens"]),
            int(train_config["max_target_tokens"]),
        )
        metric = float(validation["typed_ast_exact_accuracy"])
        _assert_finite(metric, "formal validation accuracy")
        elapsed = time.monotonic() - started
        row = {
            "epoch": epoch,
            "mean_train_loss": epoch_loss / max(1, len(loader)),
            "validation_typed_ast_exact_accuracy": metric,
            "validation_compilable_rate": validation["compilable_rate"],
            "validation_compiled_stl_exact_accuracy": validation["compiled_stl_exact_accuracy"],
            "optimizer_updates": global_updates,
            "elapsed_seconds": elapsed,
            "cuda_max_memory_bytes": torch.cuda.max_memory_allocated(device) if device.type == "cuda" else 0,
        }
        progress.append(row)
        improved = metric > best_metric
        best_metric = max(best_metric, metric)
        state = {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "epoch": epoch,
            "best_metric": best_metric,
            "method": "formal",
            "seed": seed,
            "optimizer_updates": global_updates,
            "data_loader_generator_state": generator.get_state(),
        }
        _atomic_torch_save(state, latest_path)
        if improved:
            _atomic_torch_save(
                {"model": model.state_dict(), "epoch": epoch, "metric": metric, "seed": seed},
                best_path,
            )
            _write_json(run_dir / "best_validation_predictions.json", {"predictions": validation["predictions"]})
        _write_progress(progress_path, progress)
        print(json.dumps({"method": "formal", **row}, sort_keys=True), flush=True)
    elapsed = time.monotonic() - started
    return {
        "method": "formal",
        "seed": seed,
        "epochs_completed": int(train_config["epochs"]),
        "optimizer_updates": global_updates,
        "elapsed_seconds": elapsed,
        "throughput_records_per_second": len(train_records) * int(train_config["epochs"]) / max(elapsed, 1e-9),
        "best_validation_metric": best_metric,
        "parameter_count": _parameter_count(model),
        "pretrained_model": model_name,
        "pretrained_revision": getattr(model.config, "_commit_hash", None),
        "added_json_tokens": list(FORMAL_JSON_TOKENS),
        "added_json_token_count": added_json_tokens,
        "checkpoint": str(best_path),
        "checkpoint_sha256": sha256_file(best_path),
        "latest_checkpoint": str(latest_path),
        "latest_checkpoint_sha256": sha256_file(latest_path),
        "finite_metrics": True,
        "dry_run": dry_run,
    }


def _direct_collator(tokenizer: Any):
    def collate(records: Sequence[Mapping[str, Any]]) -> Dict[str, torch.Tensor]:
        language = tokenizer(
            [str(record["controlled_natural_language"]) for record in records],
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        return {
            **language,
            "distances": torch.tensor([record["distances"] for record in records], dtype=torch.float32),
            "costs": torch.tensor([record["gold_costs"] for record in records], dtype=torch.float32),
            "active": torch.tensor(
                [record["gold_active_obligation"] for record in records],
                dtype=torch.float32,
            ),
            "remaining": torch.tensor(
                [record["gold_remaining_fraction"] for record in records],
                dtype=torch.float32,
            ),
        }

    return collate


def _binary_metrics(logits: torch.Tensor, targets: torch.Tensor, threshold: float) -> Dict[str, Any]:
    predicted = torch.sigmoid(logits) >= threshold
    gold = targets >= 0.5
    tp = int((predicted & gold).sum().item())
    fp = int((predicted & ~gold).sum().item())
    tn = int((~predicted & ~gold).sum().item())
    fn = int((~predicted & gold).sum().item())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_negative_rate": fn / (fn + tp) if fn + tp else 0.0,
    }


@torch.no_grad()
def _evaluate_direct(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    method: str,
    threshold: float,
) -> Dict[str, Any]:
    model.eval()
    logits = []
    targets = []
    active_correct = active_total = 0
    remaining_absolute_error = []
    for batch in loader:
        batch = {key: value.to(device) for key, value in batch.items()}
        if method == "current_direct":
            output_logits = model(batch["input_ids"], batch["attention_mask"], batch["distances"])
        else:
            output = model(batch["input_ids"], batch["attention_mask"], batch["distances"])
            output_logits = output["violation_logits"]
            active_prediction = torch.sigmoid(output["active_logits"]) >= threshold
            active_gold = batch["active"] >= 0.5
            active_correct += int((active_prediction == active_gold).sum().item())
            active_total += active_gold.numel()
            mask = active_gold
            if mask.any():
                remaining_absolute_error.extend(
                    torch.abs(output["remaining_prediction"][mask] - batch["remaining"][mask])
                    .detach()
                    .cpu()
                    .tolist(),
                )
        logits.append(output_logits.detach().cpu())
        targets.append(batch["costs"].detach().cpu())
    metrics = _binary_metrics(torch.cat(logits), torch.cat(targets), threshold)
    metrics["active_accuracy"] = active_correct / active_total if active_total else None
    metrics["active_remaining_mae"] = (
        sum(remaining_absolute_error) / len(remaining_absolute_error)
        if remaining_absolute_error
        else None
    )
    return metrics


def _direct_train(
    *,
    method: str,
    config: Mapping[str, Any],
    benchmark_root: Path,
    run_dir: Path,
    seed: int,
    dry_run: bool,
    resume: bool,
) -> Dict[str, Any]:
    from transformers import AutoTokenizer

    if method == "current_direct":
        method_config = config["methods"]["published_direct_current_observation"]
        train_config = dict(config["training_protocol"]["published_direct_current_observation"])
        model_name = str(method_config["pretrained_model"])
        model_class = CurrentObservationDirectModel
    elif method == "history_direct":
        method_config = config["methods"]["history_aware_direct"]
        train_config = dict(config["training_protocol"]["history_aware_direct"])
        model_name = str(method_config["language_model"])
        model_class = HistoryAwareDirectModel
    else:
        raise ValueError(f"unknown direct method: {method}")
    device = _device(config)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = model_class(model_name, hidden_size=128).to(device)
    train_records = _read_jsonl(benchmark_root / "generated/direct_train_traces.jsonl")
    validation_records = _read_jsonl(benchmark_root / "generated/direct_validation_traces.jsonl")
    if dry_run:
        train_records = train_records[:16]
        validation_records = validation_records[:16]
        train_config["epochs"] = 1
    collator = _direct_collator(tokenizer)
    generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(
        _RecordDataset(train_records),
        batch_size=int(train_config["batch_size"]),
        shuffle=True,
        generator=generator,
        collate_fn=collator,
    )
    validation_loader = DataLoader(
        _RecordDataset(validation_records),
        batch_size=int(train_config["batch_size"]),
        shuffle=False,
        collate_fn=collator,
    )
    encoder_parameters = list(model.text.encoder.parameters())
    encoder_ids = {id(parameter) for parameter in encoder_parameters}
    head_parameters = [parameter for parameter in model.parameters() if id(parameter) not in encoder_ids]
    optimizer = torch.optim.AdamW(
        [
            {"params": encoder_parameters, "lr": float(train_config["encoder_learning_rate"])},
            {"params": head_parameters, "lr": float(train_config["head_learning_rate"])},
        ],
        weight_decay=float(train_config["weight_decay"]),
    )
    positive_steps = sum(sum(record["gold_costs"]) for record in train_records)
    total_steps = sum(len(record["gold_costs"]) for record in train_records)
    if positive_steps <= 0:
        raise ValueError("direct training data contain no positive Gold events")
    positive_weight = torch.tensor(
        (total_steps - positive_steps) / positive_steps,
        dtype=torch.float32,
        device=device,
    )
    threshold = float(train_config["decision_threshold"])
    latest_path = run_dir / "latest.pt"
    best_path = run_dir / "best.pt"
    progress_path = run_dir / "progress.csv"
    start_epoch = 0
    best_metric = -math.inf
    progress: List[Dict[str, Any]] = []
    if resume and latest_path.is_file():
        checkpoint = torch.load(latest_path, map_location=device)
        model.load_state_dict(checkpoint["model"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        start_epoch = int(checkpoint["epoch"]) + 1
        best_metric = float(checkpoint["best_metric"])
        if "data_loader_generator_state" in checkpoint:
            generator.set_state(checkpoint["data_loader_generator_state"])
        else:
            for _ in range(start_epoch):
                torch.randperm(len(train_records), generator=generator)
                torch.randperm(len(train_records), generator=generator)
        if progress_path.is_file():
            with progress_path.open("r", newline="", encoding="utf-8") as handle:
                progress = list(csv.DictReader(handle))
    tokenizer.save_pretrained(run_dir / "tokenizer")
    started = time.monotonic()
    optimizer_updates = (
        int(checkpoint.get("optimizer_updates", start_epoch * len(train_loader)))
        if start_epoch
        else 0
    )
    for epoch in range(start_epoch, int(train_config["epochs"])):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            if method == "current_direct":
                logits = model(batch["input_ids"], batch["attention_mask"], batch["distances"])
                loss = torch.nn.functional.binary_cross_entropy_with_logits(
                    logits,
                    batch["costs"],
                    pos_weight=positive_weight,
                )
            else:
                output = model(batch["input_ids"], batch["attention_mask"], batch["distances"])
                loss, _ = direct_multitask_loss(
                    output,
                    costs=batch["costs"],
                    active=batch["active"],
                    remaining=batch["remaining"],
                    positive_weight=positive_weight,
                    active_weight=float(train_config["active_loss_weight"]),
                    remaining_weight=float(train_config["remaining_loss_weight"]),
                )
            _assert_finite(float(loss.detach().cpu()), f"{method} loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(config["training_protocol"]["gradient_clip_norm"]))
            optimizer.step()
            optimizer_updates += 1
            total_loss += float(loss.detach().cpu())
        validation = _evaluate_direct(model, validation_loader, device, method, threshold)
        metric = float(validation["f1"])
        _assert_finite(metric, f"{method} validation F1")
        elapsed = time.monotonic() - started
        row = {
            "epoch": epoch,
            "mean_train_loss": total_loss / max(1, len(train_loader)),
            "validation_precision": validation["precision"],
            "validation_recall": validation["recall"],
            "validation_f1": validation["f1"],
            "validation_false_negative_rate": validation["false_negative_rate"],
            "validation_active_accuracy": validation["active_accuracy"],
            "validation_remaining_mae": validation["active_remaining_mae"],
            "optimizer_updates": optimizer_updates,
            "elapsed_seconds": elapsed,
            "cuda_max_memory_bytes": torch.cuda.max_memory_allocated(device) if device.type == "cuda" else 0,
        }
        progress.append(row)
        improved = metric > best_metric
        best_metric = max(best_metric, metric)
        state = {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "epoch": epoch,
            "best_metric": best_metric,
            "method": method,
            "seed": seed,
            "positive_weight": float(positive_weight.detach().cpu()),
            "optimizer_updates": optimizer_updates,
            "data_loader_generator_state": generator.get_state(),
        }
        _atomic_torch_save(state, latest_path)
        if improved:
            _atomic_torch_save(
                {"model": model.state_dict(), "epoch": epoch, "metric": metric, "seed": seed},
                best_path,
            )
        _write_progress(progress_path, progress)
        print(json.dumps({"method": method, **row}, sort_keys=True), flush=True)
    elapsed = time.monotonic() - started
    model_revision = getattr(model.text.encoder.config, "_commit_hash", None)
    return {
        "method": method,
        "seed": seed,
        "epochs_completed": int(train_config["epochs"]),
        "optimizer_updates": optimizer_updates,
        "elapsed_seconds": elapsed,
        "throughput_traces_per_second": len(train_records) * int(train_config["epochs"]) / max(elapsed, 1e-9),
        "best_validation_metric": best_metric,
        "parameter_count": _parameter_count(model),
        "pretrained_model": model_name,
        "pretrained_revision": model_revision,
        "positive_event_step_weight": float(positive_weight.detach().cpu()),
        "checkpoint": str(best_path),
        "checkpoint_sha256": sha256_file(best_path),
        "latest_checkpoint": str(latest_path),
        "latest_checkpoint_sha256": sha256_file(latest_path),
        "finite_metrics": True,
        "dry_run": dry_run,
    }


def run_stage2a_training(
    method: str,
    seed: int,
    output_dir: Path,
    *,
    config_path: Path = DEFAULT_CONFIG,
    benchmark_root: Path = DEFAULT_BENCHMARK,
    dry_run: bool = False,
    resume: bool = True,
) -> Dict[str, Any]:
    """Run one resumable Stage II-A train/validation cell with immutable hashes."""

    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    config_path = config_path.resolve()
    benchmark_root = benchmark_root.resolve()
    output_dir = output_dir.resolve()
    config = _load_yaml(config_path)
    declared_seeds = [int(value) for value in config["training_protocol"]["model_seeds"]]
    if seed not in declared_seeds and not dry_run:
        raise ValueError(f"seed {seed} is outside the frozen Stage II-A seed list")
    data_hashes = _dataset_hashes(benchmark_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        existing = _read_json(manifest_path)
        if existing.get("status") == "success":
            return dict(existing["summary"])
        if existing.get("config_sha256") != sha256_file(config_path):
            raise RuntimeError("cannot resume Stage II-A run after config hash changed")
        if existing.get("data_sha256") != data_hashes:
            raise RuntimeError("cannot resume Stage II-A run after data hashes changed")
        if existing.get("source_sha256") != sha256_file(Path(__file__).resolve()):
            raise RuntimeError("cannot resume Stage II-A run after trainer source changed")
        model_source = REPOSITORY_ROOT / "src/safety_stl/stage2_models.py"
        if existing.get("model_source_sha256") != sha256_file(model_source):
            raise RuntimeError("cannot resume Stage II-A run after model source changed")
    running_manifest = {
        "schema_version": 1,
        "status": "running",
        "method": method,
        "seed": int(seed),
        "dry_run": bool(dry_run),
        "git_commit": _git_commit(),
        "config_path": str(config_path),
        "config_sha256": sha256_file(config_path),
        "data_sha256": data_hashes,
        "source_path": str(Path(__file__).resolve()),
        "source_sha256": sha256_file(Path(__file__).resolve()),
        "model_source_path": str((REPOSITORY_ROOT / "src/safety_stl/stage2_models.py").resolve()),
        "model_source_sha256": sha256_file(REPOSITORY_ROOT / "src/safety_stl/stage2_models.py"),
        "started_at_unix": time.time(),
    }
    _write_json(manifest_path, running_manifest)
    _set_seed(seed, bool(config["training_protocol"]["deterministic_algorithms"]))
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    try:
        if method == "formal":
            summary = _formal_train(
                config=config,
                benchmark_root=benchmark_root,
                run_dir=output_dir,
                seed=seed,
                dry_run=dry_run,
                resume=resume,
            )
        else:
            summary = _direct_train(
                method=method,
                config=config,
                benchmark_root=benchmark_root,
                run_dir=output_dir,
                seed=seed,
                dry_run=dry_run,
                resume=resume,
            )
    except BaseException as error:
        _write_json(
            manifest_path,
            {
                **running_manifest,
                "status": (
                    "interrupted"
                    if isinstance(error, (KeyboardInterrupt, SystemExit))
                    else "failed"
                ),
                "failed_at_unix": time.time(),
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise
    completed = {
        **running_manifest,
        "status": "success",
        "completed_at_unix": time.time(),
        "summary": summary,
    }
    _write_json(manifest_path, completed)
    return summary


__all__ = [
    "FORMAL_JSON_TOKENS",
    "FORMAL_SIGNAL_REGISTRY",
    "METHODS",
    "configure_formal_json_tokens",
    "formal_source_text",
    "run_stage2a_training",
    "sha256_file",
]
