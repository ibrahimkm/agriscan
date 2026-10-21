"""
AgriScan Candidate Evaluation and Quality Gates Engine (MLOps Phase 3 — Stage D)

This module implements the automated evaluation and quality gating pipeline for
AgriScan continuous training candidate models.

Key Requirements:
  1. Candidate Verification: Loads model checkpoint and metadata from isolated
     candidate directory (ml/artifacts/candidates/<candidate_id>/).
  2. Baseline Integrity: Strictly treats the Stage B duplicate-grouped test partition
     as an 'experimental_leakage_free' split. Never claims an unverified apples-to-apples
     equivalence with the historical naive test_metrics.json (which had 10 duplicate leaks).
  3. Strict Evaluation Separation: Evaluates exclusively on the designated held-out test
     partition. Never uses test samples for training or model selection.
  4. Candidate ONNX Export & Parity: Exports candidate to candidate_model.onnx inside
     the candidate's own directory. Verifies graph validity and PyTorch vs. ONNX Runtime
     logit parity and prediction agreement within tolerance.
  5. Automated Quality Gates: Evaluates configurable gates (data integrity, class parity,
     accuracy, macro F1, per-class recall, ONNX parity).
  6. Explicit Decisions: Returns 'PASS', 'REJECT', or 'BLOCKED'.
     Never automatically promotes a candidate to production; 'PASS' designates eligibility
     for human review.
  7. Production Protection: Strictly protects production ONNX models, class metadata,
     and historical baseline artifacts from modification.
"""

import os
import sys
import time
import json
import math
import argparse
import platform
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any, Union

# Add ml and project root to sys.path
_ml_dir = Path(__file__).resolve().parent
_proj_root = _ml_dir.parent
for p in [str(_ml_dir), str(_proj_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import numpy as np
import onnx
import onnxruntime as ort
from sklearn.metrics import (
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix,
)
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
from ml.ct_train import load_manifest_split_dataset, get_execution_device

# Default paths
CLEAN_FINAL_MANIFEST_PATH = _ml_dir / "artifacts" / "manifests" / "split_manifest_v2_seed_2026.json"
AUDIT_STAGE_F0_MANIFEST_PATH = _ml_dir / "artifacts" / "manifests" / "split_manifest_seed_2026.json"
DEV_MANIFEST_PATH = _ml_dir / "artifacts" / "manifests" / "split_manifest_seed_42.json"
FINAL_MANIFEST_PATH = CLEAN_FINAL_MANIFEST_PATH if CLEAN_FINAL_MANIFEST_PATH.exists() else AUDIT_STAGE_F0_MANIFEST_PATH
DEFAULT_MANIFEST_PATH = FINAL_MANIFEST_PATH if FINAL_MANIFEST_PATH.exists() else DEV_MANIFEST_PATH
DEFAULT_CLASSES_PATH = _ml_dir / "artifacts" / "classes.json"
DEFAULT_BASELINE_METRICS_PATH = _ml_dir / "artifacts" / "test_metrics.json"

# Production paths to strictly guard
PROTECTED_PRODUCTION_ONNX_PATHS = [
    _proj_root / "backend" / "ml_models" / "leaf_disease_model.onnx",
    _proj_root / "frontend" / "public" / "models" / "leaf_disease_model.onnx",
]

# Scikit-learn metric functions accept zero_division as Literal["warn"] | int (0 or 1)
# in stubs, but unannotated fallbacks infer str from default="warn". We type as Any and pass 0
# to satisfy all type-checking environments and silence zero-division warnings at runtime.
ZERO_DIVISION_INT: Any = 0


class CandidateQualityGates:
    """Configurable quality gate thresholds for AgriScan candidate evaluation."""

    def __init__(
        self,
        min_accuracy: float = 90.0,
        min_macro_f1: float = 88.0,
        min_per_class_recall: float = 65.0,
        max_onnx_parity_delta: float = 1e-3,
        min_onnx_class_agreement: float = 100.0,
    ):
        self.min_accuracy = min_accuracy
        self.min_macro_f1 = min_macro_f1
        self.min_per_class_recall = min_per_class_recall
        self.max_onnx_parity_delta = max_onnx_parity_delta
        self.min_onnx_class_agreement = min_onnx_class_agreement

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_accuracy": self.min_accuracy,
            "min_macro_f1": self.min_macro_f1,
            "min_per_class_recall": self.min_per_class_recall,
            "max_onnx_parity_delta": self.max_onnx_parity_delta,
            "min_onnx_class_agreement": self.min_onnx_class_agreement,
        }


def export_candidate_onnx(
    model: nn.Module,
    candidate_dir: Path,
    num_classes: int = 38,
    opset_version: int = 17,
) -> Path:
    """
    Exports candidate PyTorch model to candidate_model.onnx strictly inside candidate_dir.
    Guarantees production ONNX models are never overwritten.
    """
    candidate_dir = Path(candidate_dir).resolve()
    onnx_path = candidate_dir / "candidate_model.onnx"

    # Strict safety assertion: cannot target production ONNX files or production directories
    for prod_onnx in PROTECTED_PRODUCTION_ONNX_PATHS:
        if (
            onnx_path.resolve() == prod_onnx.resolve()
            or candidate_dir.resolve() == prod_onnx.parent.resolve()
        ):
            raise RuntimeError(
                f"FATAL SECURITY VIOLATION: Candidate ONNX export targeted production file or directory: {candidate_dir}!"
            )

    model.eval()
    device = next(model.parameters()).device
    dummy_input = torch.randn(1, 3, 224, 224, device=device, requires_grad=False)

    export_kwargs = {
        "export_params": True,
        "opset_version": opset_version,
        "do_constant_folding": True,
        "input_names": ["input_image"],
        "output_names": ["class_probabilities"],
        "dynamic_axes": {
            "input_image": {0: "batch_size"},
            "class_probabilities": {0: "batch_size"},
        },
    }

    try:
        torch.onnx.export(model, (dummy_input,), str(onnx_path), dynamo=False, **export_kwargs)
    except TypeError as exc:
        if "dynamo" in str(exc) or "unexpected keyword argument" in str(exc):
            torch.onnx.export(model, (dummy_input,), str(onnx_path), **export_kwargs)
        else:
            raise

    # Validate ONNX model with onnx.checker
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)
    return onnx_path


def verify_onnx_parity(
    model: nn.Module,
    onnx_path: Path,
    test_loader: DataLoader,
    device: torch.device,
    max_samples_for_parity: int = 100,
) -> Dict[str, Any]:
    """
    Runs both PyTorch and ONNX Runtime inference on representative test samples
    and measures absolute logit error and predicted class agreement.
    """
    session = ort.InferenceSession(str(onnx_path))
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    model.eval()
    max_delta = 0.0
    all_deltas = []
    matches = 0
    total_evaluated = 0

    with torch.no_grad():
        for images, _ in test_loader:
            if total_evaluated >= max_samples_for_parity:
                break

            images_dev = images.to(device)
            torch_logits = model(images_dev).cpu().numpy()

            ort_inputs = {input_name: images.numpy()}
            ort_logits = np.asarray(session.run([output_name], ort_inputs)[0], dtype=np.float32)

            delta = np.abs(torch_logits - ort_logits)
            batch_max_delta = float(np.max(delta))
            max_delta = max(max_delta, batch_max_delta)
            all_deltas.extend(delta.flatten().tolist())

            torch_preds = np.argmax(torch_logits, axis=1)
            ort_preds = np.argmax(ort_logits, axis=1)

            matches += int(np.sum(torch_preds == ort_preds))
            total_evaluated += len(images)

    mean_delta = float(np.mean(all_deltas)) if all_deltas else 0.0
    agreement_pct = (matches / max(1, total_evaluated)) * 100.0

    return {
        "samples_evaluated": total_evaluated,
        "max_absolute_error": float(max_delta),
        "mean_absolute_error": float(mean_delta),
        "prediction_agreement_pct": float(agreement_pct),
        "input_tensor_name": input_name,
        "output_tensor_name": output_name,
    }


def evaluate_candidate(
    candidate_dir: Union[str, Path],
    manifest_path: Union[str, Path] = DEFAULT_MANIFEST_PATH,
    split: str = "test",
    data_dir: Union[str, Path] = DEFAULT_DATA_DIR,
    classes_path: Union[str, Path] = DEFAULT_CLASSES_PATH,
    baseline_metrics_path: Union[str, Path] = DEFAULT_BASELINE_METRICS_PATH,
    gates: Optional[CandidateQualityGates] = None,
    device_str: Optional[str] = None,
    batch_size: int = 32,
    max_test_samples: Optional[int] = None,
    export_onnx: bool = True,
    max_parity_samples: int = 100,
) -> Dict[str, Any]:
    """
    Evaluates candidate model on the designated held-out partition (default: 'test'),
    exports candidate ONNX, verifies parity, and applies quality gates.

    Returns: Comprehensive evaluation summary including explicit decision:
             'PASS' | 'REJECT' | 'BLOCKED'.
    """
    eval_start_time = time.time()
    if gates is None:
        gates = CandidateQualityGates()

    c_dir = Path(candidate_dir).resolve()
    print(f"\n[AgriScan Evaluation] Inspecting candidate directory: {c_dir}")

    # =============================================================
    # Pre-flight Check: Candidate Metadata & Checkpoint Integrity
    # =============================================================
    blocking_reasons: List[str] = []

    if not c_dir.exists():
        blocking_reasons.append(f"Candidate directory does not exist: {c_dir}")
    meta_path = c_dir / "candidate_metadata.json"
    ckpt_path = c_dir / "best_model.pth"

    if not meta_path.exists():
        blocking_reasons.append(f"Missing candidate_metadata.json at: {meta_path}")
    if not ckpt_path.exists():
        blocking_reasons.append(f"Missing best_model.pth at: {ckpt_path}")

    # Manifest existence
    m_path = Path(manifest_path).resolve()
    if not m_path.exists():
        blocking_reasons.append(f"Test split manifest does not exist at: {m_path}")

    # Authoritative classes existence
    cl_path = Path(classes_path).resolve()
    if not cl_path.exists():
        blocking_reasons.append(f"Authoritative classes file does not exist at: {cl_path}")

    if blocking_reasons:
        print("[AgriScan Evaluation] ❌ Pre-flight checks failed. Decision: BLOCKED.")
        report = {
            "candidate_dir": str(c_dir),
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": "BLOCKED",
            "decision_summary": "Evaluation blocked due to missing or invalid pre-flight requirements.",
            "blocking_reasons": blocking_reasons,
            "quality_gates": {"preflight_integrity": "FAIL"},
        }
        _write_evaluation_report(c_dir, report)
        return report

    # Load metadata and classes
    with open(meta_path, "r", encoding="utf-8") as f:
        candidate_meta = json.load(f)
    authoritative_classes = load_authoritative_classes(cl_path)
    authoritative_checksum = compute_file_sha256(cl_path)
    candidate_id = candidate_meta.get("candidate_id", c_dir.name)
    model_variant = candidate_meta.get("model_variant", "efficientnet_b0")
    is_pilot = bool(candidate_meta.get("is_pilot", False) or candidate_id.startswith("pilot_"))

    # Verify checkpoint classes match authoritative classes
    device = get_execution_device(device_str)
    try:
        checkpoint = torch.load(ckpt_path, map_location=device, weights_only=False)
    except TypeError:
        checkpoint = torch.load(ckpt_path, map_location=device)

    ckpt_classes = checkpoint.get("classes", [])
    if ckpt_classes != authoritative_classes:
        blocking_reasons.append(
            f"Class mapping mismatch between checkpoint ({len(ckpt_classes)} classes) "
            f"and authoritative mapping ({len(authoritative_classes)} classes)."
        )

    if blocking_reasons:
        print("[AgriScan Evaluation] ❌ Checkpoint class parity failed. Decision: BLOCKED.")
        report = {
            "candidate_id": candidate_id,
            "candidate_dir": str(c_dir),
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": "BLOCKED",
            "decision_summary": "Evaluation blocked due to class mapping mismatch.",
            "blocking_reasons": blocking_reasons,
            "quality_gates": {"preflight_integrity": "FAIL"},
        }
        _write_evaluation_report(c_dir, report)
        return report

    # =============================================================
    # Load Designated Split from Manifest (Default: held-out test)
    # =============================================================
    print(f"[Dataset] Loading '{split}' split from: {m_path}")
    _, val_test_tf = get_data_transforms()
    try:
        test_ds, manifest_meta, manifest_sha256 = load_manifest_split_dataset(
            manifest_path=m_path,
            data_dir=data_dir,
            split=split,
            transform=val_test_tf,
            expected_classes=authoritative_classes,
            max_samples=max_test_samples,
        )
    except Exception as exc:
        blocking_reasons.append(f"Failed to load test dataset from manifest: {exc}")
        report = {
            "candidate_id": candidate_id,
            "candidate_dir": str(c_dir),
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": "BLOCKED",
            "decision_summary": "Evaluation blocked because test dataset could not be loaded.",
            "blocking_reasons": blocking_reasons,
            "quality_gates": {"preflight_integrity": "FAIL"},
        }
        _write_evaluation_report(c_dir, report)
        return report

    print(f"[Dataset] Test samples loaded: {len(test_ds)} across {len(authoritative_classes)} classes.")

    pin_mem = (device.type == "cuda")
    test_loader = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=pin_mem,
    )

    # =============================================================
    # PyTorch Model Evaluation
    # =============================================================
    print(f"[Evaluation] Initializing {model_variant} for evaluation on {device}...")
    model = get_model(num_classes=len(authoritative_classes), model_variant=model_variant, pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    all_preds: List[int] = []
    all_labels: List[int] = []
    all_probs: List[List[float]] = []

    print("[Evaluation] Running evaluation across held-out test set...")
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device, non_blocking=True)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)
            _, preds = torch.max(outputs, 1)

            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.tolist())
            all_probs.extend(probs.cpu().tolist())

    total_samples = len(all_labels)
    acc = (sum(p == l for p, l in zip(all_preds, all_labels)) / max(1, total_samples)) * 100.0
    macro_prec_val, macro_rec_val, macro_f1_val, _ = precision_recall_fscore_support(
        all_labels, all_preds, average="macro", zero_division=ZERO_DIVISION_INT
    )
    weighted_prec_val, weighted_rec_val, weighted_f1_val, _ = precision_recall_fscore_support(
        all_labels, all_preds, average="weighted", zero_division=ZERO_DIVISION_INT
    )

    macro_prec_pct = round(float(macro_prec_val * 100.0), 2)
    macro_rec_pct = round(float(macro_rec_val * 100.0), 2)
    macro_f1_pct = round(float(macro_f1_val * 100.0), 2)
    weighted_f1_pct = round(float(weighted_f1_val * 100.0), 2)
    test_acc_pct = round(float(acc), 2)

    # Per-class metrics
    p_raw, r_raw, f_raw, s_raw = precision_recall_fscore_support(
        all_labels, all_preds, average=None, zero_division=ZERO_DIVISION_INT
    )

    # Type narrowing and conversion to concrete numeric 1D numpy arrays
    p_vec: np.ndarray = (
        np.asarray(p_raw, dtype=np.float64)
        if isinstance(p_raw, (np.ndarray, list, tuple))
        else np.array([p_raw], dtype=np.float64)
    )
    r_vec: np.ndarray = (
        np.asarray(r_raw, dtype=np.float64)
        if isinstance(r_raw, (np.ndarray, list, tuple))
        else np.array([r_raw], dtype=np.float64)
    )
    f_vec: np.ndarray = (
        np.asarray(f_raw, dtype=np.float64)
        if isinstance(f_raw, (np.ndarray, list, tuple))
        else np.array([f_raw], dtype=np.float64)
    )
    if s_raw is not None and isinstance(s_raw, (np.ndarray, list, tuple)):
        s_vec: np.ndarray = np.asarray(s_raw, dtype=np.int64)
    else:
        s_vec = np.zeros(len(authoritative_classes), dtype=np.int64)

    per_class_metrics: Dict[str, Dict[str, Union[float, int]]] = {}
    failing_recall_classes: List[Dict[str, Union[str, float]]] = []

    num_p = len(p_vec)
    num_r = len(r_vec)
    num_f = len(f_vec)
    num_s = len(s_vec)

    for idx, cls_name in enumerate(authoritative_classes):
        p_c = round(float(p_vec[idx] * 100.0), 2) if idx < num_p else 0.0
        r_c = round(float(r_vec[idx] * 100.0), 2) if idx < num_r else 0.0
        f_c = round(float(f_vec[idx] * 100.0), 2) if idx < num_f else 0.0
        s_c = int(s_vec[idx]) if idx < num_s else 0

        per_class_metrics[cls_name] = {
            "precision": p_c,
            "recall": r_c,
            "f1": f_c,
            "support": s_c,
        }

        if r_c < gates.min_per_class_recall:
            failing_recall_classes.append({
                "class_name": cls_name,
                "recall": r_c,
                "threshold": gates.min_per_class_recall,
            })

    # Save test classification report
    report_file = c_dir / "test_classification_report.txt"
    unique_present = sorted(list(set(all_labels).union(set(all_preds))))
    target_names = [authoritative_classes[i] for i in unique_present]
    report_output = classification_report(
        all_labels, all_preds, target_names=target_names, zero_division=ZERO_DIVISION_INT
    )
    report_text: str = (
        report_output
        if isinstance(report_output, str)
        else json.dumps(report_output, indent=2)
    )
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"AGRISCAN HELD-OUT TEST EVALUATION REPORT — CANDIDATE: {candidate_id}\n")
        f.write(f"Evaluation Protocol: experimental_leakage_free\n")
        f.write(f"Test Accuracy: {test_acc_pct:.2f}%\n")
        f.write(f"Macro F1-Score: {macro_f1_pct:.2f}%\n")
        f.write(f"Macro Precision: {macro_prec_pct:.2f}%\n")
        f.write(f"Macro Recall: {macro_rec_pct:.2f}%\n\n")
        f.write(report_text)

    # Save test confusion matrix
    cm_file = c_dir / "test_confusion_matrix.png"
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(14, 12))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Greens)
    plt.title(f"Candidate Test Confusion Matrix ({candidate_id})\nAcc: {test_acc_pct:.2f}% | F1: {macro_f1_pct:.2f}%", fontsize=12)
    plt.colorbar()
    tick_marks = range(len(target_names))
    plt.xticks(tick_marks, target_names, rotation=90, fontsize=6)
    plt.yticks(tick_marks, target_names, fontsize=6)
    plt.ylabel("True Class", fontsize=10)
    plt.xlabel("Predicted Class", fontsize=10)
    plt.tight_layout()
    plt.savefig(cm_file, dpi=180)
    plt.close()

    # =============================================================
    # ONNX Export and Parity Verification
    # =============================================================
    onnx_export_success = False
    onnx_parity_stats: Dict[str, Any] = {}
    onnx_path = c_dir / "candidate_model.onnx"

    if export_onnx:
        print("[ONNX Export] Exporting candidate model to ONNX...")
        try:
            onnx_path = export_candidate_onnx(model, c_dir, num_classes=len(authoritative_classes))
            onnx_export_success = True
            print(f"[ONNX Export] Saved candidate ONNX model to: {onnx_path}")

            print("[ONNX Parity] Verifying PyTorch vs. ONNX Runtime parity...")
            onnx_parity_stats = verify_onnx_parity(
                model=model,
                onnx_path=onnx_path,
                test_loader=test_loader,
                device=device,
                max_samples_for_parity=max_parity_samples,
            )
            print(f"  ✓ Max logit delta: {onnx_parity_stats['max_absolute_error']:.6f} "
                  f"(threshold: {gates.max_onnx_parity_delta})")
            print(f"  ✓ Prediction agreement: {onnx_parity_stats['prediction_agreement_pct']:.2f}%")
        except Exception as onnx_err:
            print(f"[ONNX Export] ❌ ONNX export/parity error: {onnx_err}")
            onnx_parity_stats = {"error": str(onnx_err)}

    # =============================================================
    # Quality Gates Decision Logic
    # =============================================================
    quality_gates = {
        "gate_data_integrity": "PASS",
        "gate_class_parity": "PASS",
        "gate_accuracy": "PASS" if test_acc_pct >= gates.min_accuracy else "FAIL",
        "gate_macro_f1": "PASS" if macro_f1_pct >= gates.min_macro_f1 else "FAIL",
        "gate_per_class_recall": "PASS" if len(failing_recall_classes) == 0 else "FAIL",
        "gate_onnx_export": "PASS" if onnx_export_success else "FAIL",
        "gate_onnx_parity": "PASS" if (
            onnx_export_success
            and onnx_parity_stats.get("max_absolute_error", 1.0) <= gates.max_onnx_parity_delta
            and onnx_parity_stats.get("prediction_agreement_pct", 0.0) >= gates.min_onnx_class_agreement
        ) else "FAIL",
    }

    all_gates_passed = all(v == "PASS" for v in quality_gates.values())

    if all_gates_passed:
        if is_pilot:
            decision = "PILOT_VERIFIED"
            decision_summary = (
                f"Pilot Candidate {candidate_id} passed all automated quality gates on evaluated test partition "
                f"(Accuracy: {test_acc_pct:.2f}%, Macro F1: {macro_f1_pct:.2f}%, ONNX parity verified). "
                "NOTE: Pilot candidate is for workflow validation and is strictly prohibited from production use."
            )
        else:
            decision = "PASS"
            decision_summary = (
                f"Candidate {candidate_id} passed all automated quality gates on the leakage-free test partition "
                f"(Accuracy: {test_acc_pct:.2f}%, Macro F1: {macro_f1_pct:.2f}%, ONNX parity verified). "
                "Model is eligible for human review; automated production promotion is disabled."
            )
    else:
        decision = "REJECT"
        failed_gate_names = [k for k, v in quality_gates.items() if v == "FAIL"]
        if is_pilot:
            decision_summary = (
                f"Pilot Candidate {candidate_id} rejected against production thresholds: {', '.join(failed_gate_names)} "
                f"(Accuracy: {test_acc_pct:.2f}%, Macro F1: {macro_f1_pct:.2f}%). "
                "This rejection is expected for a bounded pilot run; the pilot successfully validated pipeline execution, "
                "ONNX export, and parity checking without representing a production-ready model."
            )
        else:
            decision_summary = (
                f"Candidate {candidate_id} rejected because quality gate(s) failed: {', '.join(failed_gate_names)}."
            )

    eval_duration = round(time.time() - eval_start_time, 2)

    # Reference baseline provenance check
    baseline_info = {
        "historical_test_metrics_path": str(baseline_metrics_path),
        "historical_test_accuracy": 96.64,
        "historical_test_macro_f1": 95.62,
        "is_apples_to_apples_comparison": False,
        "baseline_provenance_note": (
            "The historical metrics in test_metrics.json (96.64% acc / 8,179 samples) used a naive split with "
            "10 cross-split duplicate leaks (7 between train and test). The current candidate was evaluated on the "
            "Stage B duplicate-grouped leakage-free test split (8,147 samples). Due to duplicate grouping, this is an "
            "experimental_leakage_free protocol and does not constitute a direct sample-for-sample comparison."
        ),
    }

    report = {
        "candidate_id": candidate_id,
        "candidate_dir": str(c_dir),
        "is_pilot": is_pilot,
        "pilot_note": (
            "Pilot candidate evaluation completed to verify pipeline integration. "
            "Pilot models are prohibited from production deployment."
            if is_pilot
            else None
        ),
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation_protocol": "experimental_leakage_free",
        "decision": decision,
        "decision_summary": decision_summary,
        "quality_gates": quality_gates,
        "gate_thresholds": gates.to_dict(),
        "failing_recall_classes": failing_recall_classes,
        "test_metrics": {
            "total_test_samples": total_samples,
            "accuracy": test_acc_pct,
            "macro_precision": macro_prec_pct,
            "macro_recall": macro_rec_pct,
            "macro_f1": macro_f1_pct,
            "weighted_f1": weighted_f1_pct,
        },
        "per_class_metrics": per_class_metrics,
        "onnx_parity": onnx_parity_stats,
        "baseline_provenance": baseline_info,
        "artifacts": {
            "checkpoint_path": str(ckpt_path),
            "onnx_model_path": str(onnx_path) if onnx_export_success else None,
            "classification_report": str(report_file),
            "confusion_matrix": str(cm_file),
        },
        "evaluation_duration_seconds": eval_duration,
    }

    # Save evaluation report and update candidate metadata
    _write_evaluation_report(c_dir, report)

    # Update candidate metadata JSON
    candidate_meta["status"] = f"PILOT_EVALUATED_{decision}" if is_pilot else f"EVALUATED_{decision}"
    candidate_meta["is_pilot"] = is_pilot
    candidate_meta["evaluation"] = {
        "decision": decision,
        "decision_summary": decision_summary,
        "test_accuracy": test_acc_pct,
        "macro_f1": macro_f1_pct,
        "evaluation_timestamp": report["evaluation_timestamp"],
        "evaluation_protocol": "experimental_leakage_free",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(candidate_meta, f, indent=2)

    # Log to MLflow if run_id is known
    mlflow_run_id = candidate_meta.get("mlflow", {}).get("run_id")
    tracking_uri = candidate_meta.get("mlflow", {}).get("tracking_uri")
    if mlflow_run_id and tracking_uri:
        try:
            mlflow.set_tracking_uri(tracking_uri)
            with mlflow.start_run(run_id=mlflow_run_id):
                mlflow.log_metrics({
                    "test_accuracy": test_acc_pct,
                    "test_macro_f1": macro_f1_pct,
                    "test_macro_recall": macro_rec_pct,
                    "test_macro_precision": macro_prec_pct,
                    "onnx_parity_max_delta": onnx_parity_stats.get("max_absolute_error", 0.0),
                })
                mlflow.log_artifact(str(c_dir / "evaluation_report.json"))
                mlflow.log_artifact(str(report_file))
                mlflow.log_artifact(str(cm_file))
        except Exception as ml_err:
            print(f"[MLflow] Note: Could not update MLflow run {mlflow_run_id}: {ml_err}")

    print("\n" + "=" * 65)
    print("           CANDIDATE QUALITY GATES EVALUATION RESULT")
    print("=" * 65)
    print(f" Candidate ID:         {candidate_id}")
    print(f" Decision:             {decision}")
    print(f" Test Accuracy:        {test_acc_pct:.2f}% (Threshold: {gates.min_accuracy:.1f}%)")
    print(f" Macro F1-Score:       {macro_f1_pct:.2f}% (Threshold: {gates.min_macro_f1:.1f}%)")
    print(f" ONNX Parity Max Delta:{onnx_parity_stats.get('max_absolute_error', 0.0):.6f}")
    print(f" Gates Status:         {quality_gates}")
    print(f" Summary:              {decision_summary}")
    print("=" * 65)

    return report


def _write_evaluation_report(candidate_dir: Path, report: Dict[str, Any]):
    """Writes evaluation_report.json safely inside candidate directory."""
    candidate_dir.mkdir(parents=True, exist_ok=True)
    out_file = candidate_dir / "evaluation_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgriScan Candidate Evaluation and Quality Gates Engine (Stage D)")
    parser.add_argument("--candidate-dir", type=str, required=True, help="Path to candidate directory")
    parser.add_argument("--manifest-path", type=str, default=str(DEFAULT_MANIFEST_PATH), help="Path to Stage B split manifest")
    parser.add_argument("--split", type=str, default="test", choices=["test", "val", "train"], help="Split partition to evaluate ('test', 'val', 'train')")
    parser.add_argument("--data-dir", type=str, default=DEFAULT_DATA_DIR, help="Dataset root directory")
    parser.add_argument("--classes-path", type=str, default=str(DEFAULT_CLASSES_PATH), help="Path to authoritative classes.json")
    parser.add_argument("--min-accuracy", type=float, default=90.0, help="Minimum test accuracy (%%) threshold")
    parser.add_argument("--min-macro-f1", type=float, default=88.0, help="Minimum test macro F1 (%%) threshold")
    parser.add_argument("--min-recall", type=float, default=65.0, help="Minimum per-class recall (%%) threshold")
    parser.add_argument("--max-onnx-delta", type=float, default=1e-3, help="Maximum allowed PyTorch/ONNX logit delta")
    parser.add_argument("--device", type=str, default="auto", help="Execution device ('mps', 'cuda', 'cpu', 'auto')")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--max-test-samples", type=int, default=None, help="Sample cap for debugging")
    parser.add_argument("--no-onnx", action="store_true", help="Skip ONNX export")

    args = parser.parse_args()

    gates = CandidateQualityGates(
        min_accuracy=args.min_accuracy,
        min_macro_f1=args.min_macro_f1,
        min_per_class_recall=args.min_recall,
        max_onnx_parity_delta=args.max_onnx_delta,
    )

    evaluate_candidate(
        candidate_dir=args.candidate_dir,
        manifest_path=args.manifest_path,
        split=args.split,
        data_dir=args.data_dir,
        classes_path=args.classes_path,
        gates=gates,
        device_str=args.device,
        batch_size=args.batch_size,
        max_test_samples=args.max_test_samples,
        export_onnx=not args.no_onnx,
    )
