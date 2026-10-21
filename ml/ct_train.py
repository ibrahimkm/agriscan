"""
AgriScan Continuous Training Pipeline (MLOps Phase 3 — Stage C)

This module implements the automated fine-tuning and experiment tracking pipeline
for AgriScan plant leaf disease classification.

Key Requirements:
  1. Consumes the validated dataset and deterministic split manifest from Stage B.
  2. Uses production EfficientNet-B0 architecture with production-compatible normalization.
  3. Tracks experiments, parameters, per-epoch metrics, and artifacts in local MLflow (SQLite).
  4. Supports Apple Silicon MPS acceleration with CPU fallback.
  5. Isolates candidate checkpoints and metadata under ml/artifacts/candidates/<candidate_id>/.
  6. Supports training checkpoint saving and resuming.
  7. Strict evaluation separation: only train and val splits are used during training;
     the held-out test split is strictly preserved for Stage D evaluation.
  8. Strictly protects existing production ONNX models, class mappings, and baselines.
"""

import os
import sys
import time
import json
import math
import random
import platform
import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any, Union
from collections import Counter, defaultdict

ZERO_DIVISION_INT: Any = 0

# Add ml and project root to sys.path
_ml_dir = Path(__file__).resolve().parent
_proj_root = _ml_dir.parent
for p in [str(_ml_dir), str(_proj_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image, UnidentifiedImageError
from sklearn.metrics import precision_recall_fscore_support, classification_report, confusion_matrix
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import mlflow
from mlflow.tracking import MlflowClient

from ml.model import get_model, LeafDiseaseClassifier
from ml.dataset import (
    get_data_transforms,
    DatasetFromSamples,
    NORMALIZE_MEAN,
    NORMALIZE_STD,
    DEFAULT_DATA_DIR,
)
from ml.dataset_validator import compute_file_sha256, load_authoritative_classes

# Default paths
CLEAN_FINAL_MANIFEST_PATH = _ml_dir / "artifacts" / "manifests" / "split_manifest_v2_seed_2026.json"
AUDIT_STAGE_F0_MANIFEST_PATH = _ml_dir / "artifacts" / "manifests" / "split_manifest_seed_2026.json"
DEV_MANIFEST_PATH = _ml_dir / "artifacts" / "manifests" / "split_manifest_seed_42.json"
FINAL_MANIFEST_PATH = CLEAN_FINAL_MANIFEST_PATH if CLEAN_FINAL_MANIFEST_PATH.exists() else AUDIT_STAGE_F0_MANIFEST_PATH
DEFAULT_MANIFEST_PATH = FINAL_MANIFEST_PATH if FINAL_MANIFEST_PATH.exists() else DEV_MANIFEST_PATH
DEFAULT_CLASSES_PATH = _ml_dir / "artifacts" / "classes.json"
DEFAULT_CANDIDATES_DIR = _ml_dir / "artifacts" / "candidates"
DEFAULT_TRACKING_URI = f"sqlite:///{_ml_dir / 'artifacts' / 'mlflow.db'}"
DEFAULT_EXPERIMENT_NAME = "agriscan-continuous-training"


def get_execution_device(requested_device: Optional[str] = None) -> torch.device:
    """
    Selects optimal execution device (Apple Silicon MPS, CUDA, or CPU fallback).
    """
    if requested_device and requested_device.lower() != "auto":
        dev_str = requested_device.lower()
        if dev_str == "mps" and not torch.backends.mps.is_available():
            print("[Device] MPS requested but not available; falling back to CPU.")
            return torch.device("cpu")
        if dev_str == "cuda" and not torch.cuda.is_available():
            print("[Device] CUDA requested but not available; falling back to CPU.")
            return torch.device("cpu")
        return torch.device(dev_str)

    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def set_seed(seed: int = 42):
    """Sets deterministic random seeds across python, numpy, and torch."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_manifest_split_dataset(
    manifest_path: Union[str, Path],
    data_dir: Union[str, Path],
    split: str = "train",
    transform=None,
    expected_classes: Optional[List[str]] = None,
    max_samples: Optional[int] = None,
    samples_per_class: Optional[int] = None,
) -> Tuple[DatasetFromSamples, Dict[str, Any], str]:
    """
    Loads samples for a specific partition ('train' or 'val') from a Stage B split manifest.
    Verifies that all files exist and matches the authoritative class mapping.
    Supports stratified subsampling for bounded pilot runs without changing the authoritative manifest.
    Never silently generates fake data or skips missing files.

    Returns: (DatasetFromSamples, manifest_metadata, manifest_sha256)
    """
    m_path = Path(manifest_path).resolve()
    if not m_path.exists():
        raise FileNotFoundError(
            f"Stage B split manifest not found at: {m_path}\n"
            "Please generate the manifest first via ml/dataset_validator.py."
        )

    manifest_sha256 = compute_file_sha256(m_path)
    with open(m_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    if "splits" not in manifest_data or split not in manifest_data["splits"]:
        raise ValueError(f"Manifest at {m_path} does not contain split partition: '{split}'")

    metadata = manifest_data.get("metadata", {})
    split_items = manifest_data["splits"][split]

    d_dir = Path(data_dir).resolve()
    if not d_dir.exists():
        raise FileNotFoundError(f"Dataset root directory not found at: {d_dir}")

    if expected_classes is None:
        expected_classes = load_authoritative_classes()
    class_to_idx = {name: idx for idx, name in enumerate(expected_classes)}

    samples: List[Tuple[str, int]] = []
    missing_files: List[str] = []

    for item in split_items:
        rel_path = item["rel_path"]
        class_name = item["class_name"]
        file_abs = d_dir / rel_path

        if not file_abs.exists():
            missing_files.append(str(file_abs))
            continue

        if class_name not in class_to_idx:
            raise ValueError(
                f"Class '{class_name}' in manifest is not in authoritative class mapping!"
            )

        samples.append((str(file_abs), class_to_idx[class_name]))

    if missing_files:
        raise FileNotFoundError(
            f"Found {len(missing_files)} missing sample files referenced in manifest split '{split}'.\n"
            f"Example missing file: {missing_files[0]}\n"
            "Aborting training to avoid silent data corruption."
        )

    if len(samples) == 0:
        raise ValueError(f"Split partition '{split}' has 0 valid samples in manifest {m_path}.")

    # Deterministic stratified subsampling for pilot / bounded evaluation runs
    if samples_per_class is not None and samples_per_class > 0:
        class_buckets: Dict[int, List[Tuple[str, int]]] = defaultdict(list)
        for s in samples:
            class_buckets[s[1]].append(s)
        stratified_samples: List[Tuple[str, int]] = []
        for c_idx in sorted(class_buckets.keys()):
            stratified_samples.extend(class_buckets[c_idx][:samples_per_class])
        samples = stratified_samples
    elif max_samples is not None and max_samples > 0 and len(samples) > max_samples:
        class_buckets: Dict[int, List[Tuple[str, int]]] = defaultdict(list)
        for s in samples:
            class_buckets[s[1]].append(s)
        per_class = max(1, max_samples // len(expected_classes))
        stratified_samples: List[Tuple[str, int]] = []
        for c_idx in sorted(class_buckets.keys()):
            stratified_samples.extend(class_buckets[c_idx][:per_class])
        if len(stratified_samples) < max_samples:
            remaining_needed = max_samples - len(stratified_samples)
            for c_idx in sorted(class_buckets.keys()):
                extra = class_buckets[c_idx][per_class:]
                stratified_samples.extend(extra[:remaining_needed])
                remaining_needed = max_samples - len(stratified_samples)
                if remaining_needed <= 0:
                    break
        samples = stratified_samples[:max_samples]

    ds = DatasetFromSamples(samples=samples, classes=expected_classes, transform=transform)
    return ds, metadata, manifest_sha256


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
) -> Tuple[float, float]:
    """Runs a single training epoch."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in dataloader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, preds = torch.max(outputs, 1)
        correct += torch.sum(preds == labels.data).item()
        total += labels.size(0)

    epoch_loss = running_loss / max(1, total)
    epoch_acc = (correct / max(1, total)) * 100.0
    return epoch_loss, epoch_acc


def validate_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, float, float, List[int], List[int]]:
    """Runs evaluation on the validation set."""
    model.eval()
    running_loss = 0.0
    all_preds: List[int] = []
    all_labels: List[int] = []

    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)

            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    total = len(all_labels)
    val_loss = running_loss / max(1, total)
    val_acc = (sum(p == l for p, l in zip(all_preds, all_labels)) / max(1, total)) * 100.0
    _, _, val_f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average="macro", zero_division=ZERO_DIVISION_INT
    )
    val_f1_pct = float(val_f1 * 100.0)
    return val_loss, val_acc, val_f1_pct, all_preds, all_labels


def save_epoch_checkpoint(
    candidate_dir: Path,
    checkpoint_name: str,
    epoch: int,
    stage: str,
    model: nn.Module,
    optimizer: optim.Optimizer,
    classes: List[str],
    val_loss: float,
    val_acc: float,
    val_f1: float,
    best_val_f1: float,
    best_val_acc: float,
    best_metrics: Dict[str, Any],
    seed: int,
    candidate_id: str,
    mlflow_run_id: str,
    manifest_metadata: Dict[str, Any],
    manifest_sha256: str,
    classes_checksum: str,
    is_pilot: bool = False,
    resumed_from_run_id: Optional[str] = None,
    ancestor_run_ids: Optional[List[str]] = None,
) -> Path:
    """
    Saves an intermediate epoch checkpoint (e.g. checkpoint_last.pth or best_model.pth)
    for crash resilience and seamless resume capability.
    """
    candidate_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = candidate_dir / checkpoint_name
    checkpoint_data = {
        "candidate_id": candidate_id,
        "is_pilot": is_pilot,
        "epoch": epoch,
        "stage": stage,
        "val_acc": val_acc,
        "val_f1": val_f1,
        "val_loss": val_loss,
        "best_val_f1": best_val_f1,
        "best_val_acc": best_val_acc,
        "best_metrics": best_metrics,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "classes": classes,
        "class_to_idx": {cls: idx for idx, cls in enumerate(classes)},
        "idx_to_class": {str(idx): cls for idx, cls in enumerate(classes)},
        "model_variant": "efficientnet_b0",
        "normalize_mean": NORMALIZE_MEAN,
        "normalize_std": NORMALIZE_STD,
        "seed": seed,
        "rng_state": torch.get_rng_state(),
        "dataset_fingerprint": manifest_metadata.get("dataset_fingerprint", ""),
        "manifest_sha256": manifest_sha256,
        "classes_checksum": classes_checksum,
        "mlflow_run_id": mlflow_run_id,
        "resumed_from_run_id": resumed_from_run_id,
        "ancestor_run_ids": ancestor_run_ids or [],
    }
    torch.save(checkpoint_data, ckpt_path)
    return ckpt_path


def save_candidate_artifacts(
    candidate_dir: Path,
    candidate_id: str,
    model: nn.Module,
    optimizer: optim.Optimizer,
    classes: List[str],
    config: Dict[str, Any],
    best_metrics: Dict[str, Any],
    all_preds: List[int],
    all_labels: List[int],
    mlflow_run_id: str,
    training_duration: float,
    device: torch.device,
    manifest_metadata: Dict[str, Any],
    manifest_sha256: str,
    classes_checksum: str,
    is_pilot: bool = False,
    pilot_warning: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Saves isolated candidate model checkpoint and machine-readable metadata.
    Guarantees no production files are touched.
    """
    candidate_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save candidate checkpoint
    checkpoint_path = candidate_dir / "best_model.pth"
    if checkpoint_path.exists():
        try:
            saved_best = torch.load(checkpoint_path, map_location=device, weights_only=False)
            if "model_state_dict" in saved_best:
                model.load_state_dict(saved_best["model_state_dict"])
        except Exception:
            pass

    checkpoint_data = {
        "candidate_id": candidate_id,
        "is_pilot": is_pilot,
        "epoch": best_metrics.get("epoch", 0),
        "val_acc": best_metrics.get("val_acc", 0.0),
        "val_f1": best_metrics.get("val_f1", 0.0),
        "val_loss": best_metrics.get("val_loss", 0.0),
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "classes": classes,
        "class_to_idx": {cls: idx for idx, cls in enumerate(classes)},
        "idx_to_class": {str(idx): cls for idx, cls in enumerate(classes)},
        "model_variant": config.get("model_variant", "efficientnet_b0"),
        "normalize_mean": NORMALIZE_MEAN,
        "normalize_std": NORMALIZE_STD,
        "seed": config.get("seed", 42),
        "dataset_fingerprint": manifest_metadata.get("dataset_fingerprint", ""),
        "manifest_sha256": manifest_sha256,
        "classes_checksum": classes_checksum,
        "mlflow_run_id": mlflow_run_id,
        "resumed_from_run_id": config.get("resumed_from_run_id"),
        "ancestor_run_ids": config.get("ancestor_run_ids", []),
    }
    torch.save(checkpoint_data, checkpoint_path)
    checkpoint_sha256 = compute_file_sha256(checkpoint_path)

    # 2. Save classes.json copy in candidate dir
    classes_path = candidate_dir / "classes.json"
    with open(classes_path, "w", encoding="utf-8") as f:
        json.dump({
            "classes": classes,
            "class_to_idx": {cls: idx for idx, cls in enumerate(classes)},
            "idx_to_class": {str(idx): cls for idx, cls in enumerate(classes)},
            "num_classes": len(classes),
        }, f, indent=2)

    # 3. Save validation classification report & confusion matrix
    report_file = candidate_dir / "validation_report.txt"
    cm_file = candidate_dir / "confusion_matrix.png"

    unique_present = sorted(list(set(all_labels).union(set(all_preds))))
    target_names = [classes[i] for i in unique_present]
    report_output = classification_report(
        all_labels, all_preds, target_names=target_names, zero_division=ZERO_DIVISION_INT
    )
    report_text: str = (
        report_output
        if isinstance(report_output, str)
        else json.dumps(report_output, indent=2)
    )
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"AGRISCAN VALIDATION REPORT — CANDIDATE: {candidate_id}\n")
        f.write(f"Validation Accuracy: {best_metrics.get('val_acc', 0.0):.2f}%\n")
        f.write(f"Validation Macro F1: {best_metrics.get('val_f1', 0.0):.2f}%\n\n")
        f.write(report_text)

    # Confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(12, 10))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Greens)
    plt.title(f"Validation Confusion Matrix ({candidate_id})\nAcc: {best_metrics.get('val_acc', 0.0):.2f}% | F1: {best_metrics.get('val_f1', 0.0):.2f}%", fontsize=12)
    plt.colorbar()
    tick_marks = range(len(target_names))
    plt.xticks(tick_marks, target_names, rotation=90, fontsize=6)
    plt.yticks(tick_marks, target_names, fontsize=6)
    plt.ylabel("True Class", fontsize=10)
    plt.xlabel("Predicted Class", fontsize=10)
    plt.tight_layout()
    plt.savefig(cm_file, dpi=180)
    plt.close()

    # 4. Save comprehensive candidate metadata JSON
    metadata = {
        "candidate_id": candidate_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_pilot": is_pilot,
        "pilot_warning": pilot_warning,
        "status": "PILOT_TRAINED_PENDING_EVALUATION" if is_pilot else "TRAINED_PENDING_EVALUATION",
        "model_variant": config.get("model_variant", "efficientnet_b0"),
        "seed": config.get("seed", 42),
        "mlflow": {
            "tracking_uri": config.get("tracking_uri"),
            "experiment_name": config.get("experiment_name"),
            "run_id": mlflow_run_id,
            "resumed_from_run_id": config.get("resumed_from_run_id"),
            "ancestor_run_ids": config.get("ancestor_run_ids", []),
        },
        "environment": {
            "device": str(device),
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "mlflow_version": mlflow.__version__,
            "platform": platform.platform(),
        },
        "provenance": {
            "split_manifest_path": str(config.get("manifest_path")),
            "split_manifest_sha256": manifest_sha256,
            "dataset_fingerprint": manifest_metadata.get("dataset_fingerprint", ""),
            "classes_checksum": classes_checksum,
            "num_classes": len(classes),
            "train_samples": config.get("train_samples", 0),
            "val_samples": config.get("val_samples", 0),
            "resumed_from_checkpoint": config.get("resume_from"),
            "resumed_from_run_id": config.get("resumed_from_run_id"),
            "ancestor_run_ids": config.get("ancestor_run_ids", []),
        },
        "training_config": config,
        "best_metrics": best_metrics,
        "artifacts": {
            "candidate_dir": str(candidate_dir),
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": checkpoint_sha256,
            "classes_path": str(classes_path),
            "validation_report": str(report_file),
            "confusion_matrix": str(cm_file),
        },
        "training_duration_seconds": round(training_duration, 2),
    }

    metadata_file = candidate_dir / "candidate_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


def train_candidate(
    data_dir: Union[str, Path] = DEFAULT_DATA_DIR,
    manifest_path: Union[str, Path] = DEFAULT_MANIFEST_PATH,
    classes_path: Union[str, Path] = DEFAULT_CLASSES_PATH,
    candidates_dir: Union[str, Path] = DEFAULT_CANDIDATES_DIR,
    candidate_id: Optional[str] = None,
    tracking_uri: str = DEFAULT_TRACKING_URI,
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    model_variant: str = "efficientnet_b0",
    epochs_stage1: int = 2,
    epochs_stage2: int = 4,
    batch_size: int = 32,
    lr_stage1: float = 1e-3,
    lr_stage2: float = 2e-4,
    weight_decay: float = 1e-4,
    seed: int = 42,
    device_str: Optional[str] = None,
    resume_from: Optional[Union[str, Path]] = None,
    max_train_samples: Optional[int] = None,
    max_val_samples: Optional[int] = None,
    pilot_samples_per_class: Optional[int] = None,
    is_pilot: bool = False,
    register_model: bool = False,
) -> Dict[str, Any]:
    """
    Main entry point for Stage C continuous training with MLflow tracking.
    """
    start_time = time.time()
    set_seed(seed)

    if pilot_samples_per_class is not None and pilot_samples_per_class > 0:
        is_pilot = True

    if candidate_id is None:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        candidate_id = f"pilot_{timestamp_str}_seed{seed}" if is_pilot else f"candidate_{timestamp_str}_seed{seed}"
    elif is_pilot and not candidate_id.startswith("pilot_"):
        candidate_id = f"pilot_{candidate_id}"

    candidate_dir = Path(candidates_dir).resolve() / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    # Resolve device
    device = get_execution_device(device_str)
    print(f"\n[AgriScan CT] Starting training run for Candidate: {candidate_id}")
    print(f"[AgriScan CT] Execution Device: {device}")
    print(f"[AgriScan CT] Candidate Output Dir: {candidate_dir}")

    # Load authoritative classes
    c_path = Path(classes_path).resolve()
    if not c_path.exists():
        raise FileNotFoundError(f"Classes mapping file not found at: {c_path}")
    classes = load_authoritative_classes(c_path)
    classes_checksum = compute_file_sha256(c_path)
    num_classes = len(classes)

    # Setup MLflow
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    try:
        exp = client.get_experiment_by_name(experiment_name)
        if exp is None:
            exp_id = client.create_experiment(experiment_name)
        else:
            exp_id = exp.experiment_id
    except Exception as exc:
        print(f"[MLflow] Warning: Experiment lookup error ({exc}). Falling back to default experiment.")
        exp_id = "0"

    # Load Stage B split datasets (Train and Val ONLY)
    train_transform, val_transform = get_data_transforms()
    print(f"[Dataset] Loading train split from manifest: {manifest_path}")
    train_ds, manifest_metadata, manifest_sha256 = load_manifest_split_dataset(
        manifest_path=manifest_path,
        data_dir=data_dir,
        split="train",
        transform=train_transform,
        expected_classes=classes,
        max_samples=max_train_samples,
        samples_per_class=pilot_samples_per_class,
    )

    print(f"[Dataset] Loading validation split from manifest: {manifest_path}")
    val_ds, _, _ = load_manifest_split_dataset(
        manifest_path=manifest_path,
        data_dir=data_dir,
        split="val",
        transform=val_transform,
        expected_classes=classes,
        max_samples=max_val_samples,
        samples_per_class=pilot_samples_per_class,
    )

    print(f"[Dataset] Samples loaded — Train: {len(train_ds)} | Val: {len(val_ds)}")

    # Class-weighted loss for class imbalance
    train_labels = [lbl for _, lbl in train_ds.samples]
    class_counts = Counter(train_labels)
    total_train = len(train_labels)
    class_weights = [
        total_train / (num_classes * max(1, class_counts.get(c, 1)))
        for c in range(num_classes)
    ]
    criterion_weight = torch.tensor(class_weights, dtype=torch.float32).to(device)
    criterion = nn.CrossEntropyLoss(weight=criterion_weight)

    # DataLoaders (conservative for 8GB Mac)
    pin_mem = (device.type == "cuda")
    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=pin_mem,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=pin_mem,
    )

    # Model instantiation
    print(f"[Model] Initializing {model_variant} with {num_classes} outputs...")
    model = get_model(num_classes=num_classes, model_variant=model_variant, pretrained=True)
    model.to(device)

    start_epoch = 1
    best_val_f1 = 0.0
    best_val_acc = 0.0
    best_metrics: Dict[str, Any] = {}
    best_preds: List[int] = []
    best_labels: List[int] = []

    resume_ckpt = None
    res_path: Optional[Path] = None
    resumed_run_id = None
    ancestor_run_ids: List[str] = []
    # Resume capability
    if resume_from:
        res_path = Path(resume_from).resolve()
        if not res_path.exists():
            raise FileNotFoundError(f"Resume checkpoint not found at: {res_path}")
        print(f"[Resume] Loading checkpoint from: {res_path}")
        try:
            ckpt = torch.load(res_path, map_location=device, weights_only=False)
        except TypeError:
            ckpt = torch.load(res_path, map_location=device)
        resume_ckpt = ckpt
        model.load_state_dict(ckpt["model_state_dict"])
        start_epoch = ckpt.get("epoch", 0) + 1
        best_val_f1 = ckpt.get("best_val_f1", ckpt.get("val_f1", 0.0))
        best_val_acc = ckpt.get("best_val_acc", ckpt.get("val_acc", 0.0))
        best_metrics = ckpt.get("best_metrics", {})
        if "rng_state" in ckpt:
            try:
                torch.set_rng_state(ckpt["rng_state"])
            except Exception:
                pass

        # Track MLflow provenance lineage
        resumed_run_id = ckpt.get("mlflow_run_id")
        if "ancestor_run_ids" in ckpt and isinstance(ckpt["ancestor_run_ids"], list):
            for arid in ckpt["ancestor_run_ids"]:
                if arid and arid not in ancestor_run_ids:
                    ancestor_run_ids.append(arid)
        try:
            client = MlflowClient(tracking_uri=tracking_uri)
            candidate_runs = client.search_runs(
                experiment_ids=[exp_id],
                filter_string=f"tags.`mlflow.runName` = '{candidate_id}'",
                order_by=["attribute.start_time ASC"],
            )
            for cr in candidate_runs:
                if cr.info.run_id not in ancestor_run_ids:
                    ancestor_run_ids.append(cr.info.run_id)
        except Exception:
            if resumed_run_id and resumed_run_id not in ancestor_run_ids:
                ancestor_run_ids.append(resumed_run_id)

        print(f"[Resume] Resumed from epoch {start_epoch-1} (Previous Best F1: {best_val_f1:.2f}%)")
        if ancestor_run_ids:
            print(f"[Resume] Prior ancestor MLflow runs: {ancestor_run_ids}")

    # Start MLflow run
    with mlflow.start_run(experiment_id=exp_id, run_name=candidate_id) as run:
        run_id = run.info.run_id
        print(f"[MLflow] Active Run ID: {run_id}")

        if res_path is not None:
            mlflow.set_tag("resumed_from_checkpoint", str(res_path))
        if resumed_run_id:
            mlflow.set_tag("resumed_from_run_id", resumed_run_id)
        if ancestor_run_ids:
            mlflow.set_tag("ancestor_run_ids", json.dumps(ancestor_run_ids))

        training_config = {
            "candidate_id": candidate_id,
            "is_pilot": is_pilot,
            "pilot_samples_per_class": pilot_samples_per_class,
            "model_variant": model_variant,
            "seed": seed,
            "batch_size": batch_size,
            "epochs_stage1": epochs_stage1,
            "epochs_stage2": epochs_stage2,
            "lr_stage1": lr_stage1,
            "lr_stage2": lr_stage2,
            "weight_decay": weight_decay,
            "tracking_uri": tracking_uri,
            "experiment_name": experiment_name,
            "manifest_path": str(manifest_path),
            "manifest_sha256": manifest_sha256,
            "dataset_fingerprint": manifest_metadata.get("dataset_fingerprint", ""),
            "classes_checksum": classes_checksum,
            "train_samples": len(train_ds),
            "val_samples": len(val_ds),
            "num_classes": num_classes,
            "resume_from": str(res_path) if res_path is not None else None,
            "resumed_from_run_id": resumed_run_id,
            "ancestor_run_ids": ancestor_run_ids,
        }

        # Log parameters to MLflow
        mlflow.log_params({
            "candidate_id": candidate_id,
            "is_pilot": is_pilot,
            "pilot_samples_per_class": str(pilot_samples_per_class),
            "model_variant": model_variant,
            "seed": seed,
            "batch_size": batch_size,
            "epochs_stage1": epochs_stage1,
            "epochs_stage2": epochs_stage2,
            "lr_stage1": lr_stage1,
            "lr_stage2": lr_stage2,
            "weight_decay": weight_decay,
            "device": str(device),
            "train_samples": len(train_ds),
            "val_samples": len(val_ds),
            "num_classes": num_classes,
            "manifest_sha256": manifest_sha256[:16],
            "dataset_fingerprint": str(manifest_metadata.get("dataset_fingerprint", ""))[:16],
        })

        global_epoch = 0
        optimizer: optim.Optimizer = optim.AdamW(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=lr_stage1,
            weight_decay=weight_decay,
        )

        # =============================================================
        # STAGE 1: Feature Extraction (Classifier Head)
        # =============================================================
        if epochs_stage1 > 0 and start_epoch <= epochs_stage1:
            print("\n" + "=" * 65)
            print(f" STAGE 1: Training Classifier Head ({epochs_stage1} Epochs)")
            print("=" * 65)
            model.freeze_backbone()
            optimizer = optim.AdamW(
                filter(lambda p: p.requires_grad, model.parameters()),
                lr=lr_stage1,
                weight_decay=weight_decay,
            )

            for ep in range(start_epoch, epochs_stage1 + 1):
                global_epoch = ep
                t_loss, t_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
                v_loss, v_acc, v_f1, preds, labels = validate_epoch(model, val_loader, criterion, device)

                print(
                    f"Stage 1 — Ep {ep:02d}/{epochs_stage1:02d} | "
                    f"Train Loss: {t_loss:.4f} | Train Acc: {t_acc:.2f}% | "
                    f"Val Loss: {v_loss:.4f} | Val Acc: {v_acc:.2f}% | Val F1: {v_f1:.2f}%"
                )

                mlflow.log_metrics({
                    "stage1_train_loss": t_loss,
                    "stage1_train_acc": t_acc,
                    "val_loss": v_loss,
                    "val_acc": v_acc,
                    "val_macro_f1": v_f1,
                    "learning_rate": lr_stage1,
                }, step=global_epoch)

                is_best = (v_f1 >= best_val_f1)
                if is_best:
                    best_val_f1 = v_f1
                    best_val_acc = v_acc
                    best_metrics = {
                        "epoch": global_epoch,
                        "stage": "stage1",
                        "val_acc": v_acc,
                        "val_f1": v_f1,
                        "val_loss": v_loss,
                    }
                    best_preds = preds
                    best_labels = labels

                # Save checkpoint_last.pth for crash resilience and resume
                save_epoch_checkpoint(
                    candidate_dir=candidate_dir,
                    checkpoint_name="checkpoint_last.pth",
                    epoch=global_epoch,
                    stage="stage1",
                    model=model,
                    optimizer=optimizer,
                    classes=classes,
                    val_loss=v_loss,
                    val_acc=v_acc,
                    val_f1=v_f1,
                    best_val_f1=best_val_f1,
                    best_val_acc=best_val_acc,
                    best_metrics=best_metrics,
                    seed=seed,
                    candidate_id=candidate_id,
                    mlflow_run_id=run_id,
                    manifest_metadata=manifest_metadata,
                    manifest_sha256=manifest_sha256,
                    classes_checksum=classes_checksum,
                    is_pilot=is_pilot,
                    resumed_from_run_id=resumed_run_id,
                    ancestor_run_ids=ancestor_run_ids,
                )

                if is_best:
                    save_epoch_checkpoint(
                        candidate_dir=candidate_dir,
                        checkpoint_name="best_model.pth",
                        epoch=global_epoch,
                        stage="stage1",
                        model=model,
                        optimizer=optimizer,
                        classes=classes,
                        val_loss=v_loss,
                        val_acc=v_acc,
                        val_f1=v_f1,
                        best_val_f1=best_val_f1,
                        best_val_acc=best_val_acc,
                        best_metrics=best_metrics,
                        seed=seed,
                        candidate_id=candidate_id,
                        mlflow_run_id=run_id,
                        manifest_metadata=manifest_metadata,
                        manifest_sha256=manifest_sha256,
                        classes_checksum=classes_checksum,
                        is_pilot=is_pilot,
                        resumed_from_run_id=resumed_run_id,
                        ancestor_run_ids=ancestor_run_ids,
                    )

        # =============================================================
        # STAGE 2: End-to-End Fine-Tuning
        # =============================================================
        if epochs_stage2 > 0:
            print("\n" + "=" * 65)
            print(f" STAGE 2: End-to-End Fine-Tuning ({epochs_stage2} Epochs)")
            print("=" * 65)
            model.unfreeze_backbone()
            optimizer = optim.AdamW(
                model.parameters(),
                lr=lr_stage2,
                weight_decay=weight_decay,
            )
            scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=epochs_stage2, eta_min=1e-6
            )

            stage2_start = max(1, start_epoch - epochs_stage1)
            if resume_ckpt and stage2_start > 1 and "optimizer_state_dict" in resume_ckpt and resume_ckpt.get("stage") == "stage2":
                try:
                    optimizer.load_state_dict(resume_ckpt["optimizer_state_dict"])
                    for _ in range(stage2_start - 1):
                        scheduler.step()
                    print(f"[Resume] Restored Stage 2 optimizer state and advanced scheduler to epoch {stage2_start}")
                except Exception as exc:
                    print(f"[Resume] Note: Optimizer/scheduler state reinit ({exc})")

            for s2_ep in range(stage2_start, epochs_stage2 + 1):
                global_epoch = epochs_stage1 + s2_ep
                curr_lr = optimizer.param_groups[0]["lr"]

                t_loss, t_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
                v_loss, v_acc, v_f1, preds, labels = validate_epoch(model, val_loader, criterion, device)
                scheduler.step()

                print(
                    f"Stage 2 — Ep {s2_ep:02d}/{epochs_stage2:02d} | "
                    f"Train Loss: {t_loss:.4f} | Train Acc: {t_acc:.2f}% | "
                    f"Val Loss: {v_loss:.4f} | Val Acc: {v_acc:.2f}% | Val F1: {v_f1:.2f}% | "
                    f"LR: {curr_lr:.6f}"
                )

                mlflow.log_metrics({
                    "stage2_train_loss": t_loss,
                    "stage2_train_acc": t_acc,
                    "val_loss": v_loss,
                    "val_acc": v_acc,
                    "val_macro_f1": v_f1,
                    "learning_rate": curr_lr,
                }, step=global_epoch)

                is_best = (v_f1 >= best_val_f1)
                if is_best:
                    best_val_f1 = v_f1
                    best_val_acc = v_acc
                    best_metrics = {
                        "epoch": global_epoch,
                        "stage": "stage2",
                        "val_acc": v_acc,
                        "val_f1": v_f1,
                        "val_loss": v_loss,
                    }
                    best_preds = preds
                    best_labels = labels

                # Save checkpoint_last.pth for crash resilience and resume
                save_epoch_checkpoint(
                    candidate_dir=candidate_dir,
                    checkpoint_name="checkpoint_last.pth",
                    epoch=global_epoch,
                    stage="stage2",
                    model=model,
                    optimizer=optimizer,
                    classes=classes,
                    val_loss=v_loss,
                    val_acc=v_acc,
                    val_f1=v_f1,
                    best_val_f1=best_val_f1,
                    best_val_acc=best_val_acc,
                    best_metrics=best_metrics,
                    seed=seed,
                    candidate_id=candidate_id,
                    mlflow_run_id=run_id,
                    manifest_metadata=manifest_metadata,
                    manifest_sha256=manifest_sha256,
                    classes_checksum=classes_checksum,
                    is_pilot=is_pilot,
                    resumed_from_run_id=resumed_run_id,
                    ancestor_run_ids=ancestor_run_ids,
                )

                if is_best:
                    save_epoch_checkpoint(
                        candidate_dir=candidate_dir,
                        checkpoint_name="best_model.pth",
                        epoch=global_epoch,
                        stage="stage2",
                        model=model,
                        optimizer=optimizer,
                        classes=classes,
                        val_loss=v_loss,
                        val_acc=v_acc,
                        val_f1=v_f1,
                        best_val_f1=best_val_f1,
                        best_val_acc=best_val_acc,
                        best_metrics=best_metrics,
                        seed=seed,
                        candidate_id=candidate_id,
                        mlflow_run_id=run_id,
                        manifest_metadata=manifest_metadata,
                        manifest_sha256=manifest_sha256,
                        classes_checksum=classes_checksum,
                        is_pilot=is_pilot,
                        resumed_from_run_id=resumed_run_id,
                        ancestor_run_ids=ancestor_run_ids,
                    )

        total_duration = time.time() - start_time

        # If best_preds is empty (e.g. 0 epochs), run a final evaluation pass
        if not best_preds:
            v_loss, v_acc, v_f1, best_preds, best_labels = validate_epoch(model, val_loader, criterion, device)
            best_metrics = {
                "epoch": global_epoch,
                "stage": "evaluated",
                "val_acc": v_acc,
                "val_f1": v_f1,
                "val_loss": v_loss,
            }

        # Log final summary metrics
        mlflow.log_metrics({
            "best_val_acc": best_metrics.get("val_acc", 0.0),
            "best_val_f1": best_metrics.get("val_f1", 0.0),
            "best_val_loss": best_metrics.get("val_loss", 0.0),
            "best_epoch": best_metrics.get("epoch", 0),
            "training_duration_seconds": total_duration,
        })

        # Save candidate artifacts
        pilot_warning = (
            "PILOT CANDIDATE: Trained on a small stratified subset for workflow validation only. "
            "Metrics are not final model-quality metrics."
            if is_pilot
            else None
        )
        candidate_meta = save_candidate_artifacts(
            candidate_dir=candidate_dir,
            candidate_id=candidate_id,
            model=model,
            optimizer=optimizer,
            classes=classes,
            config=training_config,
            best_metrics=best_metrics,
            all_preds=best_preds,
            all_labels=best_labels,
            mlflow_run_id=run_id,
            training_duration=total_duration,
            device=device,
            manifest_metadata=manifest_metadata,
            manifest_sha256=manifest_sha256,
            classes_checksum=classes_checksum,
            is_pilot=is_pilot,
            pilot_warning=pilot_warning,
        )

        # Log candidate artifacts to MLflow
        mlflow.log_artifact(str(candidate_dir / "candidate_metadata.json"))
        mlflow.log_artifact(str(candidate_dir / "classes.json"))
        mlflow.log_artifact(str(candidate_dir / "validation_report.txt"))
        mlflow.log_artifact(str(candidate_dir / "confusion_matrix.png"))

        # Optional MLflow Model Registry registration check
        registry_status = "SKIPPED"
        if register_model:
            try:
                reg_name = "AgriScan-Candidate-Models"
                print(f"[MLflow] Attempting registration under: {reg_name}")
                client.create_registered_model(reg_name)
            except Exception:
                pass  # Model already registered or registry active
            try:
                reg_info = mlflow.register_model(
                    model_uri=f"runs:/{run_id}/model",
                    name="AgriScan-Candidate-Models",
                )
                registry_status = f"REGISTERED (version {reg_info.version})"
                print(f"[MLflow Registry] Success: {registry_status}")
            except Exception as reg_err:
                registry_status = f"UNSUPPORTED_OR_FAILED: {str(reg_err)}"
                print(f"[MLflow Registry] Note: {registry_status}")

        candidate_meta["mlflow_registry_status"] = registry_status

    print("\n" + "=" * 65)
    print("           CONTINUOUS TRAINING PIPELINE COMPLETE")
    print("=" * 65)
    print(f" Candidate ID:         {candidate_id}")
    print(f" Candidate Directory:  {candidate_dir}")
    print(f" Is Pilot Candidate:   {is_pilot}")
    print(f" Best Val Accuracy:    {best_metrics.get('val_acc', 0.0):.2f}%")
    print(f" Best Val Macro F1:    {best_metrics.get('val_f1', 0.0):.2f}%")
    print(f" MLflow Run ID:        {run_id}")
    print(f" MLflow Tracking URI:  {tracking_uri}")
    print(f" Total Duration:       {total_duration:.1f}s")
    print("=" * 65)

    return candidate_meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgriScan Continuous Training Pipeline (Stage C)")
    parser.add_argument("--data-dir", type=str, default=DEFAULT_DATA_DIR, help="Dataset root directory")
    parser.add_argument("--manifest-path", "--manifest", type=str, default=str(DEFAULT_MANIFEST_PATH), help="Path to Stage B split manifest")
    parser.add_argument("--classes-path", type=str, default=str(DEFAULT_CLASSES_PATH), help="Path to classes.json")
    parser.add_argument("--candidates-dir", type=str, default=str(DEFAULT_CANDIDATES_DIR), help="Candidate output directory")
    parser.add_argument("--candidate-id", type=str, default=None, help="Unique candidate identifier")
    parser.add_argument("--tracking-uri", type=str, default=DEFAULT_TRACKING_URI, help="MLflow tracking URI")
    parser.add_argument("--experiment-name", type=str, default=DEFAULT_EXPERIMENT_NAME, help="MLflow experiment name")
    parser.add_argument("--model-variant", type=str, default="efficientnet_b0", help="Model backbone variant")
    parser.add_argument("--epochs-stage1", type=int, default=2, help="Classifier head epochs")
    parser.add_argument("--epochs-stage2", type=int, default=4, help="Fine-tuning epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr-stage1", type=float, default=1e-3, help="Stage 1 learning rate")
    parser.add_argument("--lr-stage2", type=float, default=2e-4, help="Stage 2 learning rate")
    parser.add_argument("--weight-decay", type=float, default=1e-4, help="Weight decay")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="auto", help="Execution device ('mps', 'cuda', 'cpu', 'auto')")
    parser.add_argument("--resume-from", type=str, default=None, help="Checkpoint path to resume from")
    parser.add_argument("--max-train-samples", type=int, default=None, help="Sample cap for debugging")
    parser.add_argument("--max-val-samples", type=int, default=None, help="Sample cap for debugging")
    parser.add_argument("--pilot-samples-per-class", type=int, default=None, help="Samples per class for pilot run")
    parser.add_argument("--pilot", action="store_true", help="Run bounded pilot training run")
    parser.add_argument("--register-model", action="store_true", help="Attempt MLflow Model Registry registration")

    args = parser.parse_args()

    train_candidate(
        data_dir=args.data_dir,
        manifest_path=args.manifest_path,
        classes_path=args.classes_path,
        candidates_dir=args.candidates_dir,
        candidate_id=args.candidate_id,
        tracking_uri=args.tracking_uri,
        experiment_name=args.experiment_name,
        model_variant=args.model_variant,
        epochs_stage1=args.epochs_stage1,
        epochs_stage2=args.epochs_stage2,
        batch_size=args.batch_size,
        lr_stage1=args.lr_stage1,
        lr_stage2=args.lr_stage2,
        weight_decay=args.weight_decay,
        seed=args.seed,
        device_str=args.device,
        resume_from=args.resume_from,
        max_train_samples=args.max_train_samples,
        max_val_samples=args.max_val_samples,
        pilot_samples_per_class=args.pilot_samples_per_class,
        is_pilot=args.pilot,
        register_model=args.register_model,
    )
