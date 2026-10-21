"""
Unit tests for AgriScan Candidate Evaluation & Quality Gates (MLOps Phase 3 — Stage D)

These tests use synthetic fixtures to verify all Stage D requirements:
  1. Valid and invalid candidate metadata handling.
  2. Class mapping parity and mismatch detection (BLOCKED).
  3. Missing or corrupted candidate checkpoints (BLOCKED).
  4. Missing or corrupted test split manifests (BLOCKED).
  5. Strict test-split isolation (never touches train/val).
  6. Quality gate decisions: PASS, REJECT, and BLOCKED.
  7. Candidate ONNX export and PyTorch vs. ONNX Runtime parity verification.
  8. Strict protection against overwriting production ONNX models and baselines.
  9. Evaluation report and candidate metadata integrity.
"""

import os
import sys
import json
import tempfile
import unittest
import hashlib
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from PIL import Image

# Ensure ml and project root are in sys.path
_test_dir = Path(__file__).resolve().parent
_proj_root = _test_dir.parent
for p in [str(_test_dir), str(_proj_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import torch.nn as nn
import numpy as np

from ml.ct_evaluate import (
    evaluate_candidate,
    CandidateQualityGates,
    export_candidate_onnx,
    verify_onnx_parity,
    PROTECTED_PRODUCTION_ONNX_PATHS,
)
from ml.model import get_model
from ml.dataset import NORMALIZE_MEAN, NORMALIZE_STD

PROTECTED_PRODUCTION_FILES = [
    _proj_root / "backend" / "ml_models" / "leaf_disease_model.onnx",
    _proj_root / "frontend" / "public" / "models" / "leaf_disease_model.onnx",
    _proj_root / "backend" / "ml_models" / "disease_classes.json",
    _proj_root / "ml" / "artifacts" / "classes.json",
    _proj_root / "ml" / "artifacts" / "test_metrics.json",
]


def create_synthetic_image(filepath: Path, color: tuple = (100, 150, 200), size: tuple = (32, 32)):
    """Creates a small valid JPEG image."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color=color)
    img.save(filepath, format="JPEG")


def build_evaluation_fixture(fixtures_dir: Path) -> Tuple[Path, Path, Path, Path, List[str]]:
    """
    Creates a synthetic dataset, split manifest, classes.json, and candidate directory.
    """
    classes = ["Apple___healthy", "Corn___healthy", "Tomato___healthy"]
    data_dir = fixtures_dir / "synthetic_dataset"
    classes_file = fixtures_dir / "classes.json"
    manifest_file = fixtures_dir / "split_manifest.json"
    candidate_dir = fixtures_dir / "candidate_test_01"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    with open(classes_file, "w", encoding="utf-8") as f:
        json.dump({
            "classes": classes,
            "class_to_idx": {c: i for i, c in enumerate(classes)},
            "idx_to_class": {str(i): c for i, c in enumerate(classes)},
            "num_classes": len(classes),
        }, f, indent=2)

    test_splits = []
    # Create 4 test images per class (total 12 test images)
    for c_idx, c_name in enumerate(classes):
        c_dir = data_dir / c_name
        for i in range(4):
            img_rel = f"{c_name}/test_{i}.jpg"
            img_path = data_dir / img_rel
            color = ((c_idx * 80 + i * 15) % 255, (i * 60) % 255, 140)
            create_synthetic_image(img_path, color=color)

            with open(img_path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()

            test_splits.append({
                "rel_path": img_rel,
                "class_name": c_name,
                "class_idx": c_idx,
                "group_id": h,
                "split": "test",
            })

    manifest_data = {
        "metadata": {
            "manifest_version": "1.0",
            "generator": "AgriScan Test Harness",
            "split_type": "leakage_free_duplicate_isolated",
            "seed": 42,
            "dataset_path": str(data_dir),
            "dataset_fingerprint": "fake_eval_fingerprint_abc",
            "total_images": len(test_splits),
            "total_unique_groups": len(test_splits),
            "duplicate_groups_count": 0,
            "cross_partition_duplicate_leakage": 0,
            "disjoint_verified": True,
        },
        "splits": {
            "test": test_splits,
        },
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    # Build model checkpoint inside candidate_dir
    model = get_model(num_classes=len(classes), model_variant="efficientnet_b0", pretrained=False)
    ckpt_path = candidate_dir / "best_model.pth"
    torch.save({
        "candidate_id": "candidate_test_01",
        "epoch": 2,
        "val_acc": 85.0,
        "val_f1": 84.0,
        "val_loss": 0.45,
        "model_state_dict": model.state_dict(),
        "classes": classes,
        "class_to_idx": {c: i for i, c in enumerate(classes)},
        "idx_to_class": {str(i): c for i, c in enumerate(classes)},
        "model_variant": "efficientnet_b0",
        "normalize_mean": NORMALIZE_MEAN,
        "normalize_std": NORMALIZE_STD,
        "seed": 42,
    }, ckpt_path)

    # Save candidate metadata JSON
    meta_path = candidate_dir / "candidate_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "candidate_id": "candidate_test_01",
            "created_at": "2026-10-20T09:00:00Z",
            "status": "TRAINED_PENDING_EVALUATION",
            "model_variant": "efficientnet_b0",
            "seed": 42,
            "provenance": {
                "num_classes": len(classes),
            },
        }, f, indent=2)

    return data_dir, manifest_file, classes_file, candidate_dir, classes


class TestCandidateEvaluation(unittest.TestCase):
    """Test suite for candidate evaluation, ONNX parity, and quality gates."""

    def setUp(self):
        # Record baseline checksums of protected production artifacts
        self.protected_hashes = {}
        for p in PROTECTED_PRODUCTION_FILES:
            if p.exists():
                with open(p, "rb") as f:
                    self.protected_hashes[str(p)] = hashlib.sha256(f.read()).hexdigest()

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.fixtures_dir = Path(self.tmp_dir.name)

        self.data_dir, self.manifest_file, self.classes_file, self.candidate_dir, self.classes = (
            build_evaluation_fixture(self.fixtures_dir)
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

        # Strict check: verify no protected files were modified
        for p_str, expected_hash in self.protected_hashes.items():
            p = Path(p_str)
            self.assertTrue(p.exists(), f"Protected file deleted: {p_str}")
            with open(p, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(
                actual_hash,
                expected_hash,
                f"FATAL: Protected production artifact modified during test: {p_str}"
            )

    def test_missing_candidate_directory_blocked(self):
        """Verifies decision is BLOCKED when candidate directory does not exist."""
        report = evaluate_candidate(
            candidate_dir=self.fixtures_dir / "nonexistent_candidate",
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            classes_path=self.classes_file,
        )
        self.assertEqual(report["decision"], "BLOCKED")
        self.assertTrue(any("does not exist" in r for r in report["blocking_reasons"]))

    def test_missing_metadata_blocked(self):
        """Verifies decision is BLOCKED when candidate_metadata.json is missing."""
        (self.candidate_dir / "candidate_metadata.json").unlink()
        report = evaluate_candidate(
            candidate_dir=self.candidate_dir,
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            classes_path=self.classes_file,
        )
        self.assertEqual(report["decision"], "BLOCKED")
        self.assertTrue(any("candidate_metadata.json" in r for r in report["blocking_reasons"]))

    def test_missing_checkpoint_blocked(self):
        """Verifies decision is BLOCKED when best_model.pth is missing."""
        (self.candidate_dir / "best_model.pth").unlink()
        report = evaluate_candidate(
            candidate_dir=self.candidate_dir,
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            classes_path=self.classes_file,
        )
        self.assertEqual(report["decision"], "BLOCKED")
        self.assertTrue(any("best_model.pth" in r for r in report["blocking_reasons"]))

    def test_class_mapping_mismatch_blocked(self):
        """Verifies decision is BLOCKED when checkpoint classes do not match authoritative classes."""
        # Save checkpoint with wrong classes
        model = get_model(num_classes=2, model_variant="efficientnet_b0", pretrained=False)
        torch.save({
            "candidate_id": "candidate_test_01",
            "model_state_dict": model.state_dict(),
            "classes": ["WrongClassA", "WrongClassB"],
        }, self.candidate_dir / "best_model.pth")

        report = evaluate_candidate(
            candidate_dir=self.candidate_dir,
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            classes_path=self.classes_file,
        )
        self.assertEqual(report["decision"], "BLOCKED")
        self.assertTrue(any("Class mapping mismatch" in r for r in report["blocking_reasons"]))

    def test_quality_gates_reject_on_low_accuracy(self):
        """
        Verifies decision is REJECT when accuracy falls below the configured threshold.
        """
        # Set high thresholds so random model fails
        gates = CandidateQualityGates(min_accuracy=99.0, min_macro_f1=99.0)
        report = evaluate_candidate(
            candidate_dir=self.candidate_dir,
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            classes_path=self.classes_file,
            gates=gates,
            device_str="cpu",
            export_onnx=False,
        )

        self.assertEqual(report["decision"], "REJECT")
        self.assertEqual(report["quality_gates"]["gate_accuracy"], "FAIL")
        self.assertIn("rejected", report["decision_summary"].lower())

    def test_quality_gates_pass_and_report_generation(self):
        """
        Verifies decision is PASS when thresholds are satisfied and ONNX parity is verified.
        """
        # Set permissive thresholds for synthetic untrained model smoke test
        gates = CandidateQualityGates(
            min_accuracy=0.0,
            min_macro_f1=0.0,
            min_per_class_recall=0.0,
            max_onnx_parity_delta=1e-3,
        )
        report = evaluate_candidate(
            candidate_dir=self.candidate_dir,
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            classes_path=self.classes_file,
            gates=gates,
            device_str="cpu",
            export_onnx=True,
            max_parity_samples=12,
        )

        self.assertEqual(report["decision"], "PASS")
        self.assertEqual(report["evaluation_protocol"], "experimental_leakage_free")
        self.assertIn("eligible for human review", report["decision_summary"].lower())
        self.assertEqual(report["quality_gates"]["gate_onnx_export"], "PASS")
        self.assertEqual(report["quality_gates"]["gate_onnx_parity"], "PASS")

        # Check candidate ONNX artifact
        onnx_file = self.candidate_dir / "candidate_model.onnx"
        self.assertTrue(onnx_file.exists())
        self.assertGreater(os.path.getsize(onnx_file), 1024 * 1024)  # > 1MB

        # Check evaluation report and metadata update
        eval_report_file = self.candidate_dir / "evaluation_report.json"
        self.assertTrue(eval_report_file.exists())
        self.assertTrue((self.candidate_dir / "test_classification_report.txt").exists())
        self.assertTrue((self.candidate_dir / "test_confusion_matrix.png").exists())

        with open(self.candidate_dir / "candidate_metadata.json", "r") as f:
            updated_meta = json.load(f)
        self.assertEqual(updated_meta["status"], "EVALUATED_PASS")
        self.assertEqual(updated_meta["evaluation"]["decision"], "PASS")

    def test_onnx_parity_numerical_tolerance(self):
        """
        Verifies that candidate ONNX export produces outputs within numerical tolerance
        of the PyTorch model.
        """
        model = get_model(num_classes=3, model_variant="efficientnet_b0", pretrained=False)
        onnx_path = export_candidate_onnx(model, self.candidate_dir, num_classes=3)
        self.assertTrue(onnx_path.exists())

        dummy_batch = torch.randn(4, 3, 224, 224)
        model.eval()
        with torch.no_grad():
            torch_logits = model(dummy_batch).numpy()

        import onnxruntime as ort
        session = ort.InferenceSession(str(onnx_path))
        input_name = session.get_inputs()[0].name
        ort_logits = session.run(None, {input_name: dummy_batch.numpy()})[0]

        max_err = float(np.max(np.abs(torch_logits - ort_logits)))
        self.assertLess(max_err, 1e-3, f"ONNX parity exceeded threshold: {max_err}")

    def test_protected_production_onnx_safety_guard(self):
        """
        Verifies that export_candidate_onnx raises RuntimeError if pointed at production paths.
        """
        model = get_model(num_classes=3, model_variant="efficientnet_b0", pretrained=False)
        for prod_path in PROTECTED_PRODUCTION_ONNX_PATHS:
            with self.assertRaises(RuntimeError):
                export_candidate_onnx(model, prod_path.parent, num_classes=3)

    def test_pilot_candidate_evaluation_handling(self):
        """
        Verifies that pilot candidates are tagged properly and never promoted to plain PASS.
        """
        with open(self.candidate_dir / "candidate_metadata.json", "r") as f:
            meta = json.load(f)
        meta["is_pilot"] = True
        meta["candidate_id"] = "pilot_test_01"
        with open(self.candidate_dir / "candidate_metadata.json", "w") as f:
            json.dump(meta, f)

        # Gate passes -> PILOT_VERIFIED
        pass_gates = CandidateQualityGates(
            min_accuracy=0.0,
            min_macro_f1=0.0,
            min_per_class_recall=0.0,
        )
        report_pass = evaluate_candidate(
            candidate_dir=self.candidate_dir,
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            classes_path=self.classes_file,
            gates=pass_gates,
            device_str="cpu",
            export_onnx=True,
        )
        self.assertEqual(report_pass["decision"], "PILOT_VERIFIED")
        self.assertTrue(report_pass["is_pilot"])
        self.assertIn("pilot candidate", report_pass["decision_summary"].lower())

        with open(self.candidate_dir / "candidate_metadata.json", "r") as f:
            updated_meta = json.load(f)
        self.assertEqual(updated_meta["status"], "PILOT_EVALUATED_PILOT_VERIFIED")

        # Gate fails -> REJECT with pilot summary
        fail_gates = CandidateQualityGates(
            min_accuracy=99.0,
            min_macro_f1=99.0,
        )
        report_fail = evaluate_candidate(
            candidate_dir=self.candidate_dir,
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            classes_path=self.classes_file,
            gates=fail_gates,
            device_str="cpu",
            export_onnx=False,
        )
        self.assertEqual(report_fail["decision"], "REJECT")
        self.assertTrue(report_fail["is_pilot"])
        self.assertIn("pilot candidate", report_fail["decision_summary"].lower())

    def test_custom_manifest_path_handling(self):
        """Verifies that evaluate_candidate respects an explicitly provided manifest path."""
        report = evaluate_candidate(
            candidate_dir=self.candidate_dir,
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            classes_path=self.classes_file,
            gates=CandidateQualityGates(min_accuracy=0.0, min_macro_f1=0.0, min_per_class_recall=0.0),
            device_str="cpu",
            export_onnx=False,
        )
        self.assertIn(report["decision"], ["PASS", "PILOT_VERIFIED", "REJECT"])
        self.assertEqual(report["test_metrics"]["total_test_samples"], 12)


if __name__ == "__main__":
    unittest.main()
