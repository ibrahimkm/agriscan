"""
Unit tests for AgriScan Continuous Training Pipeline & MLflow Tracking (MLOps Phase 3 — Stage C)

These tests use lightweight temporary directories and synthetic PIL images.
They verify all Stage C requirements without requiring the real 1.5 GB PlantVillage dataset:
  1. Configuration validation & error handling.
  2. Dataset split manifest loading and class-mapping consistency.
  3. MLflow run creation, parameter logging, and per-epoch metric logging using an isolated local SQLite DB.
  4. Candidate directory isolation under ml/artifacts/candidates/<candidate_id>/.
  5. Candidate metadata integrity, status='TRAINED_PENDING_EVALUATION', and checksums.
  6. Checkpoint save, structure, and resume capability.
  7. Deterministic random seed handling.
  8. CPU smoke-training test (fast end-to-end execution).
  9. Strict protection of production model files and baseline evaluation artifacts.
"""

import os
import sys
import json
import tempfile
import unittest
import hashlib
from pathlib import Path
from typing import Tuple, List
from PIL import Image

# Ensure ml and project root are in sys.path
_test_dir = Path(__file__).resolve().parent
_proj_root = _test_dir.parent
for p in [str(_test_dir), str(_proj_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import mlflow
from mlflow.tracking import MlflowClient

from ml.ct_train import (
    train_candidate,
    load_manifest_split_dataset,
    save_candidate_artifacts,
    get_execution_device,
    set_seed,
)
from ml.dataset import get_data_transforms
from ml.model import get_model

# Production files that MUST remain untouched
PROTECTED_FILES = [
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


def build_synthetic_fixture(fixtures_dir: Path) -> Tuple[Path, Path, Path, List[str]]:
    """
    Creates a synthetic mini-dataset and Stage B split manifest for fast testing.
    """
    classes = ["Apple___healthy", "Corn___healthy", "Tomato___healthy"]
    data_dir = fixtures_dir / "synthetic_dataset"
    classes_file = fixtures_dir / "classes.json"
    manifest_file = fixtures_dir / "split_manifest.json"

    with open(classes_file, "w", encoding="utf-8") as f:
        json.dump({
            "classes": classes,
            "class_to_idx": {c: i for i, c in enumerate(classes)},
            "idx_to_class": {str(i): c for i, c in enumerate(classes)},
            "num_classes": len(classes),
        }, f, indent=2)

    train_splits = []
    val_splits = []
    test_splits = []

    # Create 4 images per class (2 train, 1 val, 1 test)
    for c_idx, c_name in enumerate(classes):
        c_dir = data_dir / c_name
        for i in range(4):
            img_rel = f"{c_name}/img_{i}.jpg"
            img_path = data_dir / img_rel
            color = ((c_idx * 70 + i * 20) % 255, (i * 50) % 255, 120)
            create_synthetic_image(img_path, color=color)

            with open(img_path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()

            item = {
                "rel_path": img_rel,
                "class_name": c_name,
                "class_idx": c_idx,
                "group_id": h,
            }

            if i < 2:
                item["split"] = "train"
                train_splits.append(item)
            elif i == 2:
                item["split"] = "val"
                val_splits.append(item)
            else:
                item["split"] = "test"
                test_splits.append(item)

    manifest_data = {
        "metadata": {
            "manifest_version": "1.0",
            "generator": "AgriScan Test Harness",
            "split_type": "leakage_free_duplicate_isolated",
            "seed": 42,
            "dataset_path": str(data_dir),
            "dataset_fingerprint": "fake_test_fingerprint_12345",
            "total_images": len(train_splits) + len(val_splits) + len(test_splits),
            "total_unique_groups": 12,
            "duplicate_groups_count": 0,
            "cross_partition_duplicate_leakage": 0,
            "disjoint_verified": True,
        },
        "splits": {
            "train": train_splits,
            "val": val_splits,
            "test": test_splits,
        },
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return data_dir, manifest_file, classes_file, classes


class TestContinuousTraining(unittest.TestCase):
    """Test suite for Stage C continuous training and MLflow integration."""

    def setUp(self):
        # Record baseline checksums of protected production artifacts
        self.protected_hashes = {}
        for p in PROTECTED_FILES:
            if p.exists():
                with open(p, "rb") as f:
                    self.protected_hashes[str(p)] = hashlib.sha256(f.read()).hexdigest()

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.fixtures_dir = Path(self.tmp_dir.name)

        # Build synthetic fixtures
        self.data_dir, self.manifest_file, self.classes_file, self.classes = build_synthetic_fixture(self.fixtures_dir)
        self.tracking_uri = f"sqlite:///{self.fixtures_dir / 'test_mlflow.db'}"
        self.candidates_dir = self.fixtures_dir / "candidates"

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
                f"FATAL: Protected production artifact modified: {p_str}"
            )

    def test_configuration_validation_errors(self):
        """Verifies safe failure on invalid configuration parameters."""
        # Nonexistent data directory
        with self.assertRaises(FileNotFoundError):
            train_candidate(
                data_dir=self.fixtures_dir / "nonexistent_dir",
                manifest_path=self.manifest_file,
                classes_path=self.classes_file,
                candidates_dir=self.candidates_dir,
                tracking_uri=self.tracking_uri,
            )

        # Nonexistent manifest
        with self.assertRaises(FileNotFoundError):
            train_candidate(
                data_dir=self.data_dir,
                manifest_path=self.fixtures_dir / "nonexistent_manifest.json",
                classes_path=self.classes_file,
                candidates_dir=self.candidates_dir,
                tracking_uri=self.tracking_uri,
            )

    def test_manifest_split_dataset_loading(self):
        """Verifies that samples are accurately loaded from the Stage B split manifest."""
        train_tf, val_tf = get_data_transforms()
        train_ds, meta, m_hash = load_manifest_split_dataset(
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            split="train",
            transform=train_tf,
            expected_classes=self.classes,
        )

        self.assertEqual(len(train_ds), 6)  # 2 samples per class * 3 classes
        self.assertEqual(meta["dataset_fingerprint"], "fake_test_fingerprint_12345")
        self.assertTrue(len(m_hash) == 64)  # Valid SHA-256

        # Check sample retrieval and label bounds
        img, lbl = train_ds[0]
        self.assertIsInstance(img, torch.Tensor)
        self.assertEqual(img.shape, (3, 224, 224))
        self.assertIn(lbl, [0, 1, 2])

    def test_manifest_split_missing_file_detection(self):
        """Verifies that missing sample files referenced by manifest raise clear FileNotFoundError."""
        # Delete one image file from data_dir
        sample_img = self.data_dir / "Apple___healthy" / "img_0.jpg"
        sample_img.unlink()

        with self.assertRaises(FileNotFoundError):
            load_manifest_split_dataset(
                manifest_path=self.manifest_file,
                data_dir=self.data_dir,
                split="train",
                expected_classes=self.classes,
            )

    def test_deterministic_seed_handling(self):
        """Verifies reproducible seed behavior."""
        set_seed(42)
        rand1 = torch.randn(5)
        set_seed(42)
        rand2 = torch.randn(5)
        self.assertTrue(torch.equal(rand1, rand2))

    def test_cpu_smoke_training_and_mlflow_logging(self):
        """
        Runs a complete end-to-end continuous training smoke run on CPU
        using the synthetic fixtures. Verifies MLflow metrics and candidate artifacts.
        """
        candidate_id = "test_candidate_smoke_01"
        meta = train_candidate(
            data_dir=self.data_dir,
            manifest_path=self.manifest_file,
            classes_path=self.classes_file,
            candidates_dir=self.candidates_dir,
            candidate_id=candidate_id,
            tracking_uri=self.tracking_uri,
            experiment_name="smoke-test-exp",
            model_variant="efficientnet_b0",
            epochs_stage1=1,
            epochs_stage2=1,
            batch_size=2,
            lr_stage1=1e-3,
            lr_stage2=1e-4,
            seed=42,
            device_str="cpu",
        )

        # 1. Candidate Metadata Checks
        self.assertEqual(meta["candidate_id"], candidate_id)
        self.assertEqual(meta["status"], "TRAINED_PENDING_EVALUATION")
        self.assertEqual(meta["model_variant"], "efficientnet_b0")
        self.assertEqual(meta["provenance"]["num_classes"], 3)
        self.assertEqual(meta["provenance"]["train_samples"], 6)
        self.assertEqual(meta["provenance"]["val_samples"], 3)
        self.assertIn("checkpoint_sha256", meta["artifacts"])

        # 2. Candidate Artifacts on Disk
        c_dir = self.candidates_dir / candidate_id
        self.assertTrue((c_dir / "best_model.pth").exists())
        self.assertTrue((c_dir / "candidate_metadata.json").exists())
        self.assertTrue((c_dir / "classes.json").exists())
        self.assertTrue((c_dir / "validation_report.txt").exists())
        self.assertTrue((c_dir / "confusion_matrix.png").exists())

        # 3. Checkpoint Contents
        ckpt = torch.load(c_dir / "best_model.pth", map_location="cpu", weights_only=False)
        self.assertEqual(ckpt["candidate_id"], candidate_id)
        self.assertIn("model_state_dict", ckpt)
        self.assertIn("optimizer_state_dict", ckpt)
        self.assertEqual(ckpt["classes"], self.classes)

        # 4. MLflow Run and Logged Metrics Verification
        client = MlflowClient(tracking_uri=self.tracking_uri)
        run_id = meta["mlflow"]["run_id"]
        run = client.get_run(run_id)

        self.assertEqual(run.info.status, "FINISHED")
        self.assertIn("best_val_acc", run.data.metrics)
        self.assertIn("best_val_f1", run.data.metrics)
        self.assertEqual(run.data.params["candidate_id"], candidate_id)
        self.assertEqual(run.data.params["model_variant"], "efficientnet_b0")

        # Verify artifacts were logged to MLflow
        mlflow_artifacts = [a.path for a in client.list_artifacts(run_id)]
        self.assertIn("candidate_metadata.json", mlflow_artifacts)
        self.assertIn("classes.json", mlflow_artifacts)
        self.assertIn("validation_report.txt", mlflow_artifacts)
        self.assertIn("confusion_matrix.png", mlflow_artifacts)

    def test_checkpoint_resume(self):
        """Verifies checkpoint saving and resuming functionality."""
        candidate_1 = "test_candidate_part1"
        meta1 = train_candidate(
            data_dir=self.data_dir,
            manifest_path=self.manifest_file,
            classes_path=self.classes_file,
            candidates_dir=self.candidates_dir,
            candidate_id=candidate_1,
            tracking_uri=self.tracking_uri,
            experiment_name="resume-test-exp",
            model_variant="efficientnet_b0",
            epochs_stage1=1,
            epochs_stage2=0,
            batch_size=2,
            seed=42,
            device_str="cpu",
        )

        ckpt_path = self.candidates_dir / candidate_1 / "best_model.pth"
        self.assertTrue(ckpt_path.exists())

        # Resume into candidate_2
        candidate_2 = "test_candidate_part2"
        meta2 = train_candidate(
            data_dir=self.data_dir,
            manifest_path=self.manifest_file,
            classes_path=self.classes_file,
            candidates_dir=self.candidates_dir,
            candidate_id=candidate_2,
            tracking_uri=self.tracking_uri,
            experiment_name="resume-test-exp",
            model_variant="efficientnet_b0",
            epochs_stage1=1,
            epochs_stage2=1,
            batch_size=2,
            seed=42,
            device_str="cpu",
            resume_from=ckpt_path,
        )

        self.assertEqual(meta2["candidate_id"], candidate_2)
        self.assertTrue((self.candidates_dir / candidate_2 / "best_model.pth").exists())

    def test_candidate_directory_isolation(self):
        """Verifies that candidates are isolated and do not overwrite production models."""
        c1 = "candidate_isolated_01"
        c2 = "candidate_isolated_02"

        train_candidate(
            data_dir=self.data_dir,
            manifest_path=self.manifest_file,
            classes_path=self.classes_file,
            candidates_dir=self.candidates_dir,
            candidate_id=c1,
            tracking_uri=self.tracking_uri,
            experiment_name="isolation-exp",
            epochs_stage1=1,
            epochs_stage2=0,
            batch_size=2,
            device_str="cpu",
        )

        train_candidate(
            data_dir=self.data_dir,
            manifest_path=self.manifest_file,
            classes_path=self.classes_file,
            candidates_dir=self.candidates_dir,
            candidate_id=c2,
            tracking_uri=self.tracking_uri,
            experiment_name="isolation-exp",
            epochs_stage1=1,
            epochs_stage2=0,
            batch_size=2,
            device_str="cpu",
        )

        dir_c1 = self.candidates_dir / c1
        dir_c2 = self.candidates_dir / c2

        self.assertTrue(dir_c1.exists())
        self.assertTrue(dir_c2.exists())
        self.assertNotEqual(dir_c1, dir_c2)

    def test_stratified_subsampling(self):
        """Verifies that samples_per_class and max_samples return balanced stratified samples."""
        ds_per_class, _, _ = load_manifest_split_dataset(
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            split="train",
            expected_classes=self.classes,
            samples_per_class=1,
        )
        self.assertEqual(len(ds_per_class), len(self.classes))
        labels = [lbl for _, lbl in ds_per_class.samples]
        self.assertEqual(sorted(labels), list(range(len(self.classes))))

        ds_max_samples, _, _ = load_manifest_split_dataset(
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            split="train",
            expected_classes=self.classes,
            max_samples=3,
        )
        self.assertEqual(len(ds_max_samples), 3)
        labels_max = [lbl for _, lbl in ds_max_samples.samples]
        self.assertEqual(sorted(labels_max), list(range(len(self.classes))))

    def test_checkpoint_last_saved_and_resumed(self):
        """Verifies checkpoint_last.pth is saved on epoch finish and can be resumed."""
        c_id = "candidate_resume_checkpoint_last"
        meta1 = train_candidate(
            data_dir=self.data_dir,
            manifest_path=self.manifest_file,
            classes_path=self.classes_file,
            candidates_dir=self.candidates_dir,
            candidate_id=c_id,
            tracking_uri=self.tracking_uri,
            experiment_name="ckpt-last-exp",
            epochs_stage1=1,
            epochs_stage2=0,
            batch_size=2,
            device_str="cpu",
        )
        ckpt_last = self.candidates_dir / c_id / "checkpoint_last.pth"
        self.assertTrue(ckpt_last.exists())

        c_resume_id = "candidate_resumed_from_last"
        meta2 = train_candidate(
            data_dir=self.data_dir,
            manifest_path=self.manifest_file,
            classes_path=self.classes_file,
            candidates_dir=self.candidates_dir,
            candidate_id=c_resume_id,
            tracking_uri=self.tracking_uri,
            experiment_name="ckpt-last-exp",
            epochs_stage1=1,
            epochs_stage2=1,
            batch_size=2,
            device_str="cpu",
            resume_from=ckpt_last,
        )
        self.assertEqual(meta2["candidate_id"], c_resume_id)
        self.assertTrue((self.candidates_dir / c_resume_id / "checkpoint_last.pth").exists())

    def test_pilot_candidate_tagging(self):
        """Verifies that pilot candidate runs are labeled with pilot prefix and metadata."""
        meta = train_candidate(
            data_dir=self.data_dir,
            manifest_path=self.manifest_file,
            classes_path=self.classes_file,
            candidates_dir=self.candidates_dir,
            candidate_id=None,
            tracking_uri=self.tracking_uri,
            experiment_name="pilot-tag-exp",
            epochs_stage1=1,
            epochs_stage2=0,
            batch_size=2,
            device_str="cpu",
            pilot_samples_per_class=1,
            is_pilot=True,
        )
        self.assertTrue(meta["candidate_id"].startswith("pilot_"))
        self.assertTrue(meta["is_pilot"])
        self.assertEqual(meta["status"], "PILOT_TRAINED_PENDING_EVALUATION")
        self.assertIsNotNone(meta["pilot_warning"])

    def test_manifest_provenance_recording(self):
        """Verifies that candidate metadata records the exact manifest path and SHA-256."""
        c_id = "candidate_provenance_test"
        meta = train_candidate(
            data_dir=self.data_dir,
            manifest_path=self.manifest_file,
            classes_path=self.classes_file,
            candidates_dir=self.candidates_dir,
            candidate_id=c_id,
            tracking_uri=self.tracking_uri,
            experiment_name="provenance-exp",
            epochs_stage1=1,
            epochs_stage2=0,
            batch_size=2,
            device_str="cpu",
        )
        self.assertIn("provenance", meta)
        prov = meta["provenance"]
        self.assertEqual(prov["split_manifest_path"], str(self.manifest_file))
        with open(self.manifest_file, "rb") as f:
            expected_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(prov["split_manifest_sha256"], expected_sha)

    def test_split_partition_isolation(self):
        """Verifies that load_manifest_split_dataset strictly isolates train, val, and test."""
        train_ds, _, _ = load_manifest_split_dataset(
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            split="train",
            expected_classes=self.classes,
        )
        val_ds, _, _ = load_manifest_split_dataset(
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            split="val",
            expected_classes=self.classes,
        )
        test_ds, _, _ = load_manifest_split_dataset(
            manifest_path=self.manifest_file,
            data_dir=self.data_dir,
            split="test",
            expected_classes=self.classes,
        )

        train_files = {s[0] for s in train_ds.samples}
        val_files = {s[0] for s in val_ds.samples}
        test_files = {s[0] for s in test_ds.samples}

        self.assertEqual(len(train_files & val_files), 0, "Train and Val partitions overlap!")
        self.assertEqual(len(train_files & test_files), 0, "Train and Test partitions overlap!")
        self.assertEqual(len(val_files & test_files), 0, "Val and Test partitions overlap!")

    def test_final_evaluation_manifest_integrity(self):
        """Audits the generated seed-2026 final manifest if present on disk."""
        from ml.ct_train import FINAL_MANIFEST_PATH
        if not FINAL_MANIFEST_PATH.exists():
            return

        with open(FINAL_MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        meta = manifest_data["metadata"]
        self.assertEqual(meta["seed"], 2026)
        self.assertEqual(meta["split_type"], "leakage_free_duplicate_isolated")
        self.assertEqual(meta["cross_partition_duplicate_leakage"], 0)
        self.assertEqual(meta["dataset_fingerprint"], "2d9c9a36074078889844b0e83e15357229c36430142e76f991a414033d617e39")

        splits = manifest_data["splits"]
        train_paths = {x["rel_path"] for x in splits["train"]}
        val_paths = {x["rel_path"] for x in splits["val"]}
        test_paths = {x["rel_path"] for x in splits["test"]}

        train_groups = {x["group_id"] for x in splits["train"]}
        val_groups = {x["group_id"] for x in splits["val"]}
        test_groups = {x["group_id"] for x in splits["test"]}

        self.assertEqual(len(train_paths & val_paths), 0)
        self.assertEqual(len(train_paths & test_paths), 0)
        self.assertEqual(len(val_paths & test_paths), 0)

        self.assertEqual(len(train_groups & val_groups), 0)
        self.assertEqual(len(train_groups & test_groups), 0)
        self.assertEqual(len(val_groups & test_groups), 0)

        self.assertEqual(len({x["class_name"] for x in splits["train"]}), 38)
        self.assertEqual(len({x["class_name"] for x in splits["val"]}), 38)
        self.assertEqual(len({x["class_name"] for x in splits["test"]}), 38)

    def test_v2_manifest_pilot_holdout_isolation(self):
        """
        Regression test ensuring no Stage E pilot-exposed images or duplicate groups
        appear in the clean final test partition (split_manifest_v2_seed_2026.json).
        """
        from ml.ct_train import CLEAN_FINAL_MANIFEST_PATH
        exposed_file = _test_dir / "artifacts" / "manifests" / "stage_e_exposed_pilot_samples.json"

        if not CLEAN_FINAL_MANIFEST_PATH.exists() or not exposed_file.exists():
            return

        with open(exposed_file, "r", encoding="utf-8") as f:
            exp_data = json.load(f)
        exposed_paths = {s["rel_path"] for s in exp_data.get("exposed_samples", [])}
        exposed_groups = {s["group_id"] for s in exp_data.get("exposed_samples", [])}
        self.assertEqual(len(exposed_paths), 190)

        with open(CLEAN_FINAL_MANIFEST_PATH, "r", encoding="utf-8") as f:
            m_v2 = json.load(f)

        test_paths = {x["rel_path"] for x in m_v2["splits"]["test"]}
        test_groups = {x["group_id"] for x in m_v2["splits"]["test"]}
        val_paths = {x["rel_path"] for x in m_v2["splits"]["val"]}
        train_paths = {x["rel_path"] for x in m_v2["splits"]["train"]}

        # 1. Zero pilot exposed paths in test
        overlap_test = test_paths & exposed_paths
        self.assertEqual(
            len(overlap_test),
            0,
            f"FATAL REGRESSION: Pilot-exposed samples found in final test partition: {overlap_test}",
        )

        # 2. Zero pilot duplicate groups in test
        overlap_groups = test_groups & exposed_groups
        self.assertEqual(
            len(overlap_groups),
            0,
            f"FATAL REGRESSION: Pilot-exposed duplicate groups found in final test partition: {overlap_groups}",
        )

        # 3. All 190 exposed samples placed in train (or val, none in test)
        self.assertEqual(len(train_paths & exposed_paths), 190)
        self.assertEqual(len(val_paths & exposed_paths), 0)

        # 4. Partition disjointness
        self.assertEqual(len(train_paths & test_paths), 0)
        self.assertEqual(len(train_paths & val_paths), 0)
        self.assertEqual(len(val_paths & test_paths), 0)

        # 5. Class coverage
        self.assertEqual(len({x["class_name"] for x in m_v2["splits"]["test"]}), 38)
        self.assertEqual(len({x["class_name"] for x in m_v2["splits"]["val"]}), 38)
        self.assertEqual(len({x["class_name"] for x in m_v2["splits"]["train"]}), 38)


if __name__ == "__main__":
    unittest.main()
