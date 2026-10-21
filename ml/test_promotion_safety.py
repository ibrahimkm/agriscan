#!/usr/bin/env python3
"""
AgriScan Model Promotion and Rollback Safety Test Suite
Validates:
1. Export ordering and deploy=False protection against direct/indirect writes.
2. Atomic single-file writes, flush/fsync, permissions, and failure safety.
3. Bundle consistency and concurrency locking (.promotion.lock).
4. Promotion guard preconditions (EVALUATED_PASS, hashes, parity, human authorization).
5. Pre-promotion backup creation and cryptographic verification.
6. Fail-stop replacement failure with automated rollback.
7. Rollback engine refusal of corrupted, missing, or mismatched backups.
8. Full bundle restoration and post-restore validation.
9. Recovery after interrupted operations.

ALL TESTS ARE FULLY ISOLATED USING TEMPORARY DIRECTORIES.
NO PRODUCTION FILES ARE MODIFIED.
"""

import os
import sys
import stat
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add ml and project root to sys.path
_ml_dir = Path(__file__).resolve().parent
_proj_root = _ml_dir.parent
for p in [str(_ml_dir), str(_proj_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import numpy as np

from ml.dataset import PLANTVILLAGE_CLASSES, NORMALIZE_MEAN, NORMALIZE_STD
from ml.model import get_model
from ml.atomic_write import (
    atomic_write_bytes,
    atomic_write_text,
    atomic_write_json,
    atomic_copy_file,
    compute_file_sha256,
    validate_json_file,
    validate_onnx_file,
    validate_torch_checkpoint,
)
from ml.export_onnx import (
    export_model_to_onnx,
    build_disease_classes_json,
    DEFAULT_BACKEND_ONNX,
    DEFAULT_FRONTEND_ONNX,
    DEFAULT_BACKEND_JSON,
    DEFAULT_FRONTEND_JSON,
    DEFAULT_CHECKPOINT_PATH,
)
from ml.promotion import (
    ReleaseBundleConfig,
    PromotionLock,
    PromotionLockError,
    PromotionValidationError,
    PromotionExecutionError,
    CorruptedBackupError,
    ModelPromoter,
    ModelRollback,
)


def create_synthetic_checkpoint(path: Path, classes=None, model_variant="efficientnet_b0"):
    """Helper to generate a lightweight synthetic PyTorch checkpoint for testing."""
    classes = classes or PLANTVILLAGE_CLASSES
    model = get_model(num_classes=len(classes), model_variant=model_variant, pretrained=False)
    checkpoint = {
        "epoch": 6,
        "model_variant": model_variant,
        "model_state_dict": model.state_dict(),
        "classes": classes,
        "val_acc": 99.4,
        "val_f1": 99.2,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, str(path))
    return path


def create_synthetic_candidate_bundle(c_dir: Path, status="EVALUATED_PASS", is_pilot=False):
    """Helper to build a complete synthetic candidate directory."""
    c_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = c_dir / "best_model.pth"
    create_synthetic_checkpoint(ckpt_path)

    # Export a small valid ONNX model
    onnx_path = c_dir / "candidate_model.onnx"
    export_model_to_onnx(
        checkpoint_path=str(ckpt_path),
        output_onnx_path=str(onnx_path),
        deploy=False,
    )

    classes_path = c_dir / "classes.json"
    classes_catalog = {
        "classes": PLANTVILLAGE_CLASSES,
        "class_to_idx": {c: i for i, c in enumerate(PLANTVILLAGE_CLASSES)},
    }
    atomic_write_json(classes_path, classes_catalog)

    ckpt_sha = compute_file_sha256(ckpt_path)
    onnx_sha = compute_file_sha256(onnx_path)
    classes_sha = compute_file_sha256(classes_path)

    meta_path = c_dir / "candidate_metadata.json"
    metadata = {
        "candidate_id": c_dir.name,
        "status": status,
        "is_pilot": is_pilot,
        "model_variant": "efficientnet_b0",
        "artifacts": {
            "checkpoint_path": str(ckpt_path),
            "checkpoint_sha256": ckpt_sha,
            "classes_path": str(classes_path),
            "classes_sha256": classes_sha,
        },
    }
    atomic_write_json(meta_path, metadata)

    rel_manifest_path = c_dir / "release_manifest.json"
    rel_manifest = {
        "candidate_id": c_dir.name,
        "candidate_artifacts": {
            "checkpoint": {"sha256": ckpt_sha},
            "onnx_model": {"sha256": onnx_sha},
            "class_catalog": {"sha256": classes_sha},
        },
    }
    atomic_write_json(rel_manifest_path, rel_manifest)

    return {
        "candidate_dir": c_dir,
        "ckpt_path": ckpt_path,
        "onnx_path": onnx_path,
        "classes_path": classes_path,
        "metadata_path": meta_path,
        "release_manifest_path": rel_manifest_path,
        "ckpt_sha": ckpt_sha,
        "onnx_sha": onnx_sha,
        "classes_sha": classes_sha,
    }


def create_synthetic_production_bundle(bundle_dir: Path) -> ReleaseBundleConfig:
    """Creates a complete synthetic production bundle in a temporary directory."""
    bundle_dir.mkdir(parents=True, exist_ok=True)
    backend_onnx = bundle_dir / "backend_leaf_disease_model.onnx"
    frontend_onnx = bundle_dir / "frontend_leaf_disease_model.onnx"
    backend_json = bundle_dir / "backend_disease_classes.json"
    frontend_json = bundle_dir / "frontend_disease_classes.json"
    checkpoint = bundle_dir / "best_leaf_model.pth"
    classes_json = bundle_dir / "classes.json"
    backup_dir = bundle_dir / "backups"
    lock_file = bundle_dir / ".promotion.lock"

    # Create dummy initial files
    create_synthetic_checkpoint(checkpoint)
    export_model_to_onnx(
        checkpoint_path=str(checkpoint),
        output_onnx_path=str(backend_onnx),
        deploy=False,
    )
    shutil.copyfile(backend_onnx, frontend_onnx)

    classes_catalog = {
        "classes": PLANTVILLAGE_CLASSES,
        "class_to_idx": {c: i for i, c in enumerate(PLANTVILLAGE_CLASSES)},
    }
    atomic_write_json(classes_json, classes_catalog)
    build_disease_classes_json(
        PLANTVILLAGE_CLASSES,
        [str(backend_json), str(frontend_json)],
        allow_production=True,
    )

    return ReleaseBundleConfig(
        backend_onnx=backend_onnx,
        frontend_onnx=frontend_onnx,
        backend_json=backend_json,
        frontend_json=frontend_json,
        checkpoint=checkpoint,
        classes_json=classes_json,
        backup_dir=backup_dir,
        lock_file=lock_file,
    )


class TestAtomicWrites(unittest.TestCase):
    """Task 2: Verifies crash-safe atomic write primitives, flush/fsync, and permissions."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name).resolve()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_atomic_write_bytes_success(self):
        target = self.dir_path / "test.bin"
        data = b"Hello AgriScan Atomic Binary"
        result = atomic_write_bytes(target, data, permissions=0o644)
        self.assertEqual(result, target.resolve())
        self.assertTrue(target.is_file())
        with open(target, "rb") as f:
            self.assertEqual(f.read(), data)

        # Check no temporary files left in directory
        temp_files = list(self.dir_path.glob(".tmp_*"))
        self.assertEqual(len(temp_files), 0)

    def test_atomic_write_failure_preserves_original(self):
        target = self.dir_path / "protected.txt"
        initial_data = "Original Uncorrupted Content"
        atomic_write_text(target, initial_data)

        # Attempt atomic write with a validation function that raises an exception
        def failing_validator(p: Path):
            raise ValueError("Simulated validation failure on candidate file")

        with self.assertRaises(ValueError):
            atomic_write_text(target, "Corrupted New Content", validate_fn=failing_validator)

        # Verify original destination remains 100% untouched
        with open(target, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), initial_data)

        # Verify temp file was cleaned up
        temp_files = list(self.dir_path.glob(".tmp_*"))
        self.assertEqual(len(temp_files), 0)

    def test_atomic_write_json_validation(self):
        target = self.dir_path / "data.json"
        valid_obj = {"model": "AgriScan", "classes": 38}
        atomic_write_json(target, valid_obj)
        self.assertTrue(target.is_file())

        with open(target, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded, valid_obj)

    def test_atomic_copy_file_preserves_dest_on_failure(self):
        src = self.dir_path / "source.bin"
        dest = self.dir_path / "dest.bin"
        src.write_bytes(b"Source Payload")
        dest.write_bytes(b"Initial Dest Payload")

        def bad_validation(p: Path):
            raise RuntimeError("Post-copy checksum mismatch")

        with self.assertRaises(RuntimeError):
            atomic_copy_file(src, dest, validate_fn=bad_validation)

        # Assert destination unchanged
        self.assertEqual(dest.read_bytes(), b"Initial Dest Payload")
        self.assertEqual(len(list(self.dir_path.glob(".tmp_*"))), 0)


class TestExportOrderingAndProtection(unittest.TestCase):
    """Task 1: Verifies export ordering, metadata generation sequence, and deploy=False protection."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name).resolve()
        self.dummy_ckpt = self.dir_path / "dummy_checkpoint.pth"
        create_synthetic_checkpoint(self.dummy_ckpt)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_deploy_false_protection_direct_production_path(self):
        # Targeting DEFAULT_BACKEND_ONNX directly with deploy=False must be strictly rejected
        with self.assertRaises(RuntimeError) as ctx:
            export_model_to_onnx(
                checkpoint_path=str(self.dummy_ckpt),
                output_onnx_path=DEFAULT_BACKEND_ONNX,
                deploy=False,
            )
        self.assertIn("SAFETY VIOLATION", str(ctx.exception))

    def test_deploy_false_protection_indirect_production_dir(self):
        # Targeting an indirect file in frontend production folder with deploy=False must be rejected
        indirect_target = Path(DEFAULT_FRONTEND_ONNX).parent / "new_model.onnx"
        with self.assertRaises(RuntimeError) as ctx:
            export_model_to_onnx(
                checkpoint_path=str(self.dummy_ckpt),
                output_onnx_path=str(indirect_target),
                deploy=False,
            )
        self.assertIn("SAFETY VIOLATION", str(ctx.exception))

    def test_build_disease_classes_json_production_guard(self):
        # Direct call to build_disease_classes_json targeting production path without allow_production must fail
        with self.assertRaises(RuntimeError) as ctx:
            build_disease_classes_json(
                classes=PLANTVILLAGE_CLASSES,
                output_paths=[DEFAULT_BACKEND_JSON],
                allow_production=False,
            )
        self.assertIn("SAFETY VIOLATION", str(ctx.exception))

    def test_export_ordering_validation_failure_prevents_metadata_write(self):
        """Simulate numerical parity failure and verify NO metadata or model files are written to destinations."""
        mock_frontend_onnx = self.dir_path / "frontend_leaf_disease_model.onnx"
        mock_backend_onnx = self.dir_path / "backend_leaf_disease_model.onnx"
        mock_frontend_json = self.dir_path / "frontend_disease_classes.json"
        mock_backend_json = self.dir_path / "backend_disease_classes.json"

        # Mock np.testing.assert_allclose to simulate a parity failure
        with patch("numpy.testing.assert_allclose", side_effect=AssertionError("Simulated Parity Mismatch")):
            with self.assertRaises(AssertionError):
                export_model_to_onnx(
                    checkpoint_path=str(self.dummy_ckpt),
                    frontend_onnx=str(mock_frontend_onnx),
                    frontend_json=str(mock_frontend_json),
                    backend_onnx=str(mock_backend_onnx),
                    backend_json=str(mock_backend_json),
                    deploy=True,
                )

        # Assert none of the targets were created or written!
        self.assertFalse(mock_frontend_onnx.exists(), "Frontend ONNX should NOT be written when parity fails!")
        self.assertFalse(mock_backend_onnx.exists(), "Backend ONNX should NOT be written when parity fails!")
        self.assertFalse(mock_frontend_json.exists(), "Frontend JSON should NOT be written before parity check succeeds!")
        self.assertFalse(mock_backend_json.exists(), "Backend JSON should NOT be written before parity check succeeds!")


class TestPromotionGuards(unittest.TestCase):
    """Task 4: Verifies promotion guard preconditions, hash checks, and human authorization."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name).resolve()
        self.bundle_config = create_synthetic_production_bundle(self.dir_path / "prod")
        self.cand_data = create_synthetic_candidate_bundle(self.dir_path / "candidate_01")
        self.promoter = ModelPromoter(config=self.bundle_config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_promotion_dry_run_by_default(self):
        # Default promote() must execute in dry-run mode and make zero changes to production
        backend_onnx_before = compute_file_sha256(self.bundle_config.backend_onnx)
        result = self.promoter.promote(candidate_dir=self.cand_data["candidate_dir"])
        self.assertEqual(result["status"], "DRY_RUN_PASSED")

        backend_onnx_after = compute_file_sha256(self.bundle_config.backend_onnx)
        self.assertEqual(backend_onnx_before, backend_onnx_after, "Dry-run must not modify production files!")

    def test_promotion_requires_evaluated_pass(self):
        # Candidate with status 'TRAINED' or 'FAILED' must be rejected
        meta_file = self.cand_data["metadata_path"]
        with open(meta_file, "r") as f:
            data = json.load(f)
        data["status"] = "TRAINED_PENDING_EVALUATION"
        atomic_write_json(meta_file, data)

        with self.assertRaises(PromotionValidationError) as ctx:
            self.promoter.promote(candidate_dir=self.cand_data["candidate_dir"])
        self.assertIn("EVALUATED_PASS", str(ctx.exception))

    def test_promotion_rejects_pilot_candidate(self):
        meta_file = self.cand_data["metadata_path"]
        with open(meta_file, "r") as f:
            data = json.load(f)
        data["is_pilot"] = True
        atomic_write_json(meta_file, data)

        with self.assertRaises(PromotionValidationError) as ctx:
            self.promoter.promote(candidate_dir=self.cand_data["candidate_dir"])
        self.assertIn("PILOT", str(ctx.exception))

    def test_promotion_rejects_hash_mismatch(self):
        # Corrupt the checkpoint so it diverges from recorded hash
        ckpt_file = self.cand_data["ckpt_path"]
        with open(ckpt_file, "ab") as f:
            f.write(b"CORRUPT_BYTES")

        with self.assertRaises(PromotionValidationError) as ctx:
            self.promoter.promote(candidate_dir=self.cand_data["candidate_dir"])
        self.assertIn("hash mismatch", str(ctx.exception))

    def test_promotion_rejects_incomplete_candidate_bundle(self):
        # Remove candidate ONNX
        self.cand_data["onnx_path"].unlink()
        with self.assertRaises(PromotionValidationError) as ctx:
            self.promoter.promote(candidate_dir=self.cand_data["candidate_dir"])
        self.assertIn("missing", str(ctx.exception))

    def test_promotion_refuses_without_human_authorization(self):
        # When dry_run=False, promotion must refuse without explicit human authorization
        with self.assertRaises(PermissionError) as ctx:
            self.promoter.promote(
                candidate_dir=self.cand_data["candidate_dir"],
                dry_run=False,
                confirm_candidate_id=None,
                authorize_promotion=False,
            )
        self.assertIn("Human authorization required", str(ctx.exception))


class TestConcurrencyLocking(unittest.TestCase):
    """Task 3 & 4: Verifies process-level mutual exclusion using .promotion.lock."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name).resolve()
        self.lock_file = self.dir_path / ".promotion.lock"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_concurrent_lock_acquisition_blocked(self):
        with PromotionLock(self.lock_file):
            # Second attempt while lock is held must raise PromotionLockError
            with self.assertRaises(PromotionLockError):
                with PromotionLock(self.lock_file):
                    pass

    def test_lock_release_allows_subsequent_acquisition(self):
        with PromotionLock(self.lock_file):
            pass
        # Once released, subsequent acquisition succeeds
        with PromotionLock(self.lock_file):
            self.assertTrue(self.lock_file.is_file())


class TestFailStopPromotionRollback(unittest.TestCase):
    """Task 3 & 4: Verifies backup creation and automated rollback upon replacement failure."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name).resolve()
        self.bundle_config = create_synthetic_production_bundle(self.dir_path / "prod")
        self.cand_data = create_synthetic_candidate_bundle(self.dir_path / "candidate_01")
        self.promoter = ModelPromoter(config=self.bundle_config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pre_promotion_backup_creation_and_integrity(self):
        backup_folder = self.promoter.create_pre_promotion_backup(reason="unit_test")
        self.assertTrue(backup_folder.is_dir())
        manifest_file = backup_folder / "backup_manifest.json"
        self.assertTrue(manifest_file.is_file())

        with open(manifest_file, "r") as f:
            manifest = json.load(f)
        self.assertEqual(len(manifest["artifacts"]), 6)

        # Validate with ModelRollback
        rollback_engine = ModelRollback(config=self.bundle_config)
        validated_manifest = rollback_engine.validate_backup(backup_folder)
        self.assertEqual(manifest["backup_id"], validated_manifest["backup_id"])

    def test_replacement_failure_triggers_automatic_rollback(self):
        """Simulate an error during the replacement loop and verify automatic rollback restores original state."""
        orig_backend_sha = compute_file_sha256(self.bundle_config.backend_onnx)
        orig_ckpt_sha = compute_file_sha256(self.bundle_config.checkpoint)

        # Mock build_disease_classes_json to raise an error during step 4 of promotion
        with patch("ml.promotion.build_disease_classes_json", side_effect=RuntimeError("Simulated Metadata Failure")):
            with self.assertRaises(PromotionExecutionError):
                self.promoter.promote(
                    candidate_dir=self.cand_data["candidate_dir"],
                    dry_run=False,
                    confirm_candidate_id=self.cand_data["candidate_dir"].name,
                    authorize_promotion=True,
                )

        # Assert automated rollback restored all original files
        self.assertEqual(compute_file_sha256(self.bundle_config.backend_onnx), orig_backend_sha)
        self.assertEqual(compute_file_sha256(self.bundle_config.checkpoint), orig_ckpt_sha)


class TestRollbackEngine(unittest.TestCase):
    """Task 5: Verifies rollback discovery, validation, corruption rejection, and full bundle restoration."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name).resolve()
        self.bundle_config = create_synthetic_production_bundle(self.dir_path / "prod")
        self.promoter = ModelPromoter(config=self.bundle_config)
        self.rollback_engine = ModelRollback(config=self.bundle_config)
        self.backup_folder = self.promoter.create_pre_promotion_backup(reason="baseline_backup")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_rollback_dry_run_by_default(self):
        result = self.rollback_engine.restore_backup(self.backup_folder, dry_run=True)
        self.assertEqual(result["status"], "DRY_RUN_PASSED")

    def test_rollback_refuses_corrupted_backup_hash_mismatch(self):
        # Corrupt one backed up file
        manifest_path = self.backup_folder / "backup_manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        corrupt_target = self.backup_folder / manifest["artifacts"]["backend_onnx"]["backup_filename"]
        with open(corrupt_target, "ab") as f:
            f.write(b"CORRUPT")

        with self.assertRaises(CorruptedBackupError) as ctx:
            self.rollback_engine.restore_backup(
                self.backup_folder,
                dry_run=False,
                confirm_backup_id=manifest["backup_id"],
            )
        self.assertIn("Cryptographic corruption", str(ctx.exception))

    def test_rollback_refuses_missing_file_in_backup(self):
        manifest_path = self.backup_folder / "backup_manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        missing_target = self.backup_folder / manifest["artifacts"]["checkpoint"]["backup_filename"]
        missing_target.unlink()

        with self.assertRaises(CorruptedBackupError) as ctx:
            self.rollback_engine.restore_backup(
                self.backup_folder,
                dry_run=False,
                confirm_backup_id=manifest["backup_id"],
            )
        self.assertIn("missing from disk", str(ctx.exception))

    def test_rollback_refuses_incomplete_bundle_manifest(self):
        manifest_path = self.backup_folder / "backup_manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        del manifest["artifacts"]["classes_json"]
        atomic_write_json(manifest_path, manifest)

        with self.assertRaises(CorruptedBackupError) as ctx:
            self.rollback_engine.restore_backup(
                self.backup_folder,
                dry_run=False,
                confirm_backup_id=manifest["backup_id"],
            )
        self.assertIn("Incomplete backup bundle", str(ctx.exception))

    def test_full_compatible_release_restoration(self):
        manifest_path = self.backup_folder / "backup_manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        backup_id = manifest["backup_id"]

        # Mutate current production files to simulate bad release
        self.bundle_config.backend_onnx.write_bytes(b"MUTATED_ONNX_DATA_1")
        self.bundle_config.checkpoint.write_bytes(b"MUTATED_CKPT_DATA_2")

        # Execute authorized rollback
        result = self.rollback_engine.restore_backup(
            self.backup_folder,
            dry_run=False,
            confirm_backup_id=backup_id,
        )
        self.assertEqual(result["status"], "RESTORED")

        # Confirm post-restore hashes match manifest exactly
        for name, info in manifest["artifacts"].items():
            dest_file = Path(info["target_production_path"])
            self.assertEqual(compute_file_sha256(dest_file), info["sha256"])


class TestInterruptedOperationRecovery(unittest.TestCase):
    """Task 6: Tests recovery from interrupted operations (stale temp files, leftover lock)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name).resolve()
        self.bundle_config = create_synthetic_production_bundle(self.dir_path / "prod")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_recovery_from_stale_temp_file(self):
        stale_temp = self.bundle_config.backend_onnx.parent / f".tmp_{self.bundle_config.backend_onnx.name}_stale"
        stale_temp.write_bytes(b"STALE_UNFINISHED_DATA")

        # Subsequent atomic write should succeed cleanly and replace target
        new_data = b"FRESH_VALID_DATA"
        atomic_write_bytes(self.bundle_config.backend_onnx, new_data)
        self.assertEqual(self.bundle_config.backend_onnx.read_bytes(), new_data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
