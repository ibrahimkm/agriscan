"""
AgriScan Safe Model Promotion and Rollback Engine
Implements concurrency-locked, pre-flight validated, and fail-stop model promotion and rollback.

BUNDLE CONSISTENCY AUDIT & ARCHITECTURAL LIMITATIONS:
The AgriScan release bundle consists of multiple artifacts distributed across distinct directories:
1. backend/ml_models/leaf_disease_model.onnx (Inference engine for Node.js / Express backend)
2. frontend/public/models/leaf_disease_model.onnx (In-browser ONNX Runtime Web client model)
3. backend/ml_models/disease_classes.json (Backend agronomic guidance catalog & metadata)
4. frontend/public/models/disease_classes.json (Frontend agronomic guidance catalog & metadata)
5. ml/checkpoints/best_leaf_model.pth (Authoritative PyTorch weights & training state)
6. ml/artifacts/classes.json (Authoritative 38-class index-to-label catalog)

LIMITATION REGARDING SINGLE-POINTER ATOMIC SWITCH:
Because these artifacts reside in disjoint filesystem subtrees across backend, frontend, and
ml directories, a single POSIX directory symlink pointer swap cannot atomically switch all
production targets simultaneously without redesigning Express and Vite serving architectures.

To guarantee release bundle consistency without altering production runtime layout:
1. PromotionLock: Process-level exclusive locking via fcntl.flock prevents race conditions.
2. Complete Pre-Promotion Backup: All bundle components are backed up and verified against
   their SHA-256 digests prior to any production write.
3. Strict Quality Preconditions: Candidate must have status EVALUATED_PASS, verified checksums,
   exact 38-class parity, and validated PyTorch-to-ONNX numerical parity.
4. Atomic Single-File Replacement: Individual files are replaced using POSIX os.replace via
   atomic_copy_file() and atomic_write_json().
5. Fail-Stop Automated Rollback: If any single file replacement or post-replacement verification
   fails, the engine automatically restores the entire prior release bundle.
6. Safe-by-Default Execution: All promotion and rollback commands run in --dry-run validation mode
   unless explicit operator authorization flags are supplied.
"""

import os
import sys
import fcntl
import json
import time
import argparse
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Callable

# Ensure ml and project root in sys.path
_ml_dir = Path(__file__).resolve().parent
_proj_root = _ml_dir.parent
for p in [str(_ml_dir), str(_proj_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import numpy as np
import onnx
import onnxruntime as ort

from ml.model import get_model
from ml.dataset import PLANTVILLAGE_CLASSES
from ml.export_onnx import (
    build_disease_classes_json,
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_FRONTEND_ONNX,
    DEFAULT_FRONTEND_JSON,
    DEFAULT_BACKEND_ONNX,
    DEFAULT_BACKEND_JSON,
)
from ml.atomic_write import (
    atomic_copy_file,
    atomic_write_json,
    compute_file_sha256,
    validate_onnx_file,
    validate_json_file,
    validate_torch_checkpoint,
)


class PromotionLockError(RuntimeError):
    """Raised when the promotion/rollback exclusive lock cannot be acquired."""
    pass


class PromotionValidationError(ValueError):
    """Raised when a candidate or production precondition fails validation."""
    pass


class PromotionExecutionError(RuntimeError):
    """Raised when an error occurs during replacement, triggering rollback."""
    pass


class CorruptedBackupError(ValueError):
    """Raised when a backup directory is missing files or fails cryptographic verification."""
    pass


@dataclass
class ReleaseBundleConfig:
    """Configurable release bundle paths. Allows isolated testing with temporary directories."""
    backend_onnx: Path = field(default_factory=lambda: Path(DEFAULT_BACKEND_ONNX).resolve())
    frontend_onnx: Path = field(default_factory=lambda: Path(DEFAULT_FRONTEND_ONNX).resolve())
    backend_json: Path = field(default_factory=lambda: Path(DEFAULT_BACKEND_JSON).resolve())
    frontend_json: Path = field(default_factory=lambda: Path(DEFAULT_FRONTEND_JSON).resolve())
    checkpoint: Path = field(default_factory=lambda: Path(DEFAULT_CHECKPOINT_PATH).resolve())
    classes_json: Path = field(default_factory=lambda: (_ml_dir / "artifacts" / "classes.json").resolve())
    backup_dir: Path = field(default_factory=lambda: (_ml_dir / "artifacts" / "backups").resolve())
    lock_file: Path = field(default_factory=lambda: (_ml_dir / ".promotion.lock").resolve())

    def get_bundle_map(self) -> Dict[str, Path]:
        return {
            "backend_onnx": self.backend_onnx,
            "frontend_onnx": self.frontend_onnx,
            "backend_json": self.backend_json,
            "frontend_json": self.frontend_json,
            "checkpoint": self.checkpoint,
            "classes_json": self.classes_json,
        }


class PromotionLock:
    """POSIX file locking context manager to prevent concurrent promotion or rollback operations."""

    def __init__(self, lock_path: Path):
        self.lock_path = Path(lock_path).resolve()
        self._fd: Optional[int] = None

    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR, 0o600)
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            if self._fd is not None:
                try:
                    os.close(self._fd)
                except OSError:
                    pass
                self._fd = None
            raise PromotionLockError(
                f"Concurrent operation in progress! Could not acquire exclusive lock on: {self.lock_path}"
            ) from exc
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None


class ModelPromoter:
    """
    Validates candidates, manages verified pre-promotion backups, and performs
    fail-stop atomic model promotion.
    """

    def __init__(self, config: Optional[ReleaseBundleConfig] = None):
        self.config = config or ReleaseBundleConfig()

    def validate_candidate(self, candidate_dir: Path) -> Dict[str, Any]:
        """
        Performs comprehensive pre-flight verification on candidate artifacts:
        1. Checks existence of candidate_metadata.json, best_model.pth, classes.json, candidate_model.onnx.
        2. Asserts status == 'EVALUATED_PASS'.
        3. Asserts is_pilot == False (pilot models strictly prohibited from production).
        4. Validates exact 38-class parity and ordering against authoritative catalog.
        5. Verifies cryptographic SHA-256 hashes against candidate metadata / release manifest.
        6. Verifies ONNX model structural validity with onnx.checker.
        7. Verifies PyTorch-to-ONNX numerical parity within tolerance.
        """
        c_dir = Path(candidate_dir).resolve()
        if not c_dir.is_dir():
            raise PromotionValidationError(f"Candidate directory not found: {c_dir}")

        meta_path = c_dir / "candidate_metadata.json"
        if not meta_path.is_file():
            raise PromotionValidationError(f"Candidate metadata missing: {meta_path}")

        validate_json_file(meta_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # 1. Status and Pilot Checks
        candidate_id = metadata.get("candidate_id")
        status = metadata.get("status")
        if status != "EVALUATED_PASS":
            raise PromotionValidationError(
                f"Candidate '{candidate_id}' has status '{status}'. Only candidates with 'EVALUATED_PASS' are eligible for promotion!"
            )

        if metadata.get("is_pilot", True):
            raise PromotionValidationError(
                f"Candidate '{candidate_id}' is marked as a PILOT candidate. Pilot models cannot be promoted to production!"
            )

        # 2. Candidate Artifacts Existence & Checksums
        ckpt_path = c_dir / "best_model.pth"
        onnx_path = c_dir / "candidate_model.onnx"
        classes_path = c_dir / "classes.json"

        for art_name, art_path in [
            ("Checkpoint", ckpt_path),
            ("ONNX Model", onnx_path),
            ("Class Catalog", classes_path),
        ]:
            if not art_path.is_file():
                raise PromotionValidationError(f"Required candidate artifact missing: {art_name} at {art_path}")

        validate_torch_checkpoint(ckpt_path)
        validate_onnx_file(onnx_path)
        validate_json_file(classes_path)

        # Hash verification against metadata
        recorded_ckpt_sha = metadata.get("artifacts", {}).get("checkpoint_sha256")
        if recorded_ckpt_sha:
            actual_ckpt_sha = compute_file_sha256(ckpt_path)
            if actual_ckpt_sha != recorded_ckpt_sha:
                raise PromotionValidationError(
                    f"Candidate checkpoint hash mismatch! Expected: {recorded_ckpt_sha}, Actual: {actual_ckpt_sha}"
                )

        # Check against release_manifest.json if present
        release_manifest_path = c_dir / "release_manifest.json"
        if release_manifest_path.is_file():
            validate_json_file(release_manifest_path)
            with open(release_manifest_path, "r", encoding="utf-8") as f:
                rel_manifest = json.load(f)
            expected_onnx_sha = rel_manifest.get("candidate_artifacts", {}).get("onnx_model", {}).get("sha256")
            if expected_onnx_sha:
                actual_onnx_sha = compute_file_sha256(onnx_path)
                if actual_onnx_sha != expected_onnx_sha:
                    raise PromotionValidationError(
                        f"Candidate ONNX hash mismatch against release manifest! Expected: {expected_onnx_sha}, Actual: {actual_onnx_sha}"
                    )

        # 3. Class Catalog Validation
        with open(classes_path, "r", encoding="utf-8") as f:
            classes_data = json.load(f)
        candidate_classes = classes_data.get("classes", [])
        if len(candidate_classes) != 38:
            raise PromotionValidationError(
                f"Candidate class catalog must contain exactly 38 classes, found {len(candidate_classes)}"
            )
        if candidate_classes != PLANTVILLAGE_CLASSES:
            raise PromotionValidationError("Candidate class catalog order does not match authoritative PlantVillage classes!")

        # 4. PyTorch to ONNX Numerical Parity Check
        device = torch.device("cpu")
        try:
            ckpt = torch.load(str(ckpt_path), map_location=device, weights_only=False)
        except TypeError:
            ckpt = torch.load(str(ckpt_path), map_location=device)
        model = get_model(num_classes=38, model_variant=metadata.get("model_variant", "efficientnet_b0"), pretrained=False)
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()

        dummy_input = torch.randn(1, 3, 224, 224, dtype=torch.float32)
        with torch.no_grad():
            pt_out = model(dummy_input).numpy()

        ort_session = ort.InferenceSession(str(onnx_path))
        input_name = ort_session.get_inputs()[0].name
        ort_out = ort_session.run(None, {input_name: dummy_input.numpy()})[0]

        max_delta = float(np.max(np.abs(pt_out - ort_out)))
        if max_delta > 1e-3:
            raise PromotionValidationError(
                f"Candidate ONNX parity check failed: max logit difference {max_delta:.6e} exceeds tolerance 0.001"
            )

        return {
            "candidate_id": candidate_id,
            "status": status,
            "checkpoint_sha256": compute_file_sha256(ckpt_path),
            "onnx_sha256": compute_file_sha256(onnx_path),
            "classes_sha256": compute_file_sha256(classes_path),
            "num_classes": len(candidate_classes),
            "max_onnx_delta": max_delta,
            "metadata": metadata,
        }

    def create_pre_promotion_backup(self, reason: str = "pre_promotion") -> Path:
        """
        Creates an atomic, cryptographically verified backup of the current production bundle.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        bundle_map = self.config.get_bundle_map()

        # Pre-check: Ensure all production files exist before initiating backup
        for name, path in bundle_map.items():
            if not path.is_file():
                raise PromotionValidationError(
                    f"Cannot create pre-promotion backup: production file missing for '{name}' at {path}"
                )

        # Compute initial production hashes
        prod_hashes = {name: compute_file_sha256(path) for name, path in bundle_map.items()}
        short_id = prod_hashes["backend_onnx"][:8]
        backup_folder = self.config.backup_dir / f"backup_{timestamp}_{short_id}"
        backup_folder.mkdir(parents=True, exist_ok=True)

        manifest = {
            "backup_id": f"backup_{timestamp}_{short_id}",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reason": reason,
            "bundle_version": "1.0",
            "artifacts": {},
        }

        try:
            for name, src_path in bundle_map.items():
                dest_file = backup_folder / src_path.name
                # Avoid filename collisions in backup folder
                if dest_file.exists():
                    dest_file = backup_folder / f"{name}_{src_path.name}"
                atomic_copy_file(src_path, dest_file)
                copied_sha = compute_file_sha256(dest_file)
                if copied_sha != prod_hashes[name]:
                    raise CorruptedBackupError(
                        f"Backup verification failed for {name}: hash {copied_sha} != production hash {prod_hashes[name]}"
                    )
                manifest["artifacts"][name] = {
                    "backup_filename": dest_file.name,
                    "target_production_path": str(src_path),
                    "sha256": copied_sha,
                    "size_bytes": dest_file.stat().st_size,
                }

            manifest_path = backup_folder / "backup_manifest.json"
            atomic_write_json(manifest_path, manifest, indent=2)
            print(f"[Promotion Guard] Pre-promotion backup successfully created and verified at: {backup_folder}")
            return backup_folder
        except Exception:
            # Clean up incomplete backup folder if failed
            if backup_folder.exists():
                import shutil
                shutil.rmtree(backup_folder, ignore_errors=True)
            raise

    def promote(
        self,
        candidate_dir: Path,
        dry_run: bool = True,
        confirm_candidate_id: Optional[str] = None,
        authorize_promotion: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes safe candidate promotion.
        DEFAULT IS DRY-RUN. Refuses to write to production without explicit confirmation.
        """
        c_dir = Path(candidate_dir).resolve()

        with PromotionLock(self.config.lock_file):
            print("\n[Promotion Guard] Acquired exclusive promotion lock.")
            print(f"[Promotion Guard] Pre-flight validating candidate at: {c_dir}")
            cand_info = self.validate_candidate(c_dir)
            candidate_id = cand_info["candidate_id"]
            print(f"  ✓ Candidate '{candidate_id}' validated successfully (Status: {cand_info['status']}).")
            print(f"  ✓ Candidate ONNX numerical parity verified (max delta: {cand_info['max_onnx_delta']:.6e}).")

            # Validate current production bundle readiness
            bundle_map = self.config.get_bundle_map()
            for name, path in bundle_map.items():
                if not path.is_file():
                    raise PromotionValidationError(f"Current production bundle file missing: {name} at {path}")
            print("  ✓ Current production release bundle verified.")

            # DRY-RUN EXIT PATH: Safe by default
            if dry_run:
                print("\n" + "=" * 65)
                print("       PROMOTION GUARD DRY-RUN MODE: NO PRODUCTION WRITES")
                print("=" * 65)
                print(f" Candidate ID:         {candidate_id}")
                print(f" Candidate Status:     {cand_info['status']}")
                print(f" Candidate Checkpoint: {cand_info['checkpoint_sha256']}")
                print(f" Candidate ONNX:       {cand_info['onnx_sha256']}")
                print(f" Candidate Classes:    {cand_info['classes_sha256']}")
                print(" All preconditions passed. Candidate is ELIGIBLE for promotion.")
                print(" To promote to production, an operator must supply:")
                print("   --no-dry-run --confirm-candidate-id <ID> --authorize-production-promotion")
                print("=" * 65)
                return {
                    "status": "DRY_RUN_PASSED",
                    "candidate_id": candidate_id,
                    "candidate_info": cand_info,
                }

            # HUMAN AUTHORIZATION ENFORCEMENT
            if not authorize_promotion or confirm_candidate_id != candidate_id:
                raise PermissionError(
                    f"PROMOTION REFUSED: Human authorization required. Expected confirmation for '{candidate_id}', got '{confirm_candidate_id}'."
                )

            # PRODUCTION PROMOTION PATH
            print(f"\n[Promotion Guard] Creating pre-promotion backup before modifying production...")
            backup_folder = self.create_pre_promotion_backup(reason=f"pre_promotion_{candidate_id}")

            replaced_artifacts: List[Tuple[str, Path]] = []
            try:
                print(f"[Promotion Guard] Deploying candidate artifacts atomically...")
                c_ckpt = c_dir / "best_model.pth"
                c_onnx = c_dir / "candidate_model.onnx"
                c_classes = c_dir / "classes.json"

                # 1. Update ONNX models (frontend & backend)
                for target_name, target_path in [
                    ("backend_onnx", self.config.backend_onnx),
                    ("frontend_onnx", self.config.frontend_onnx),
                ]:
                    atomic_copy_file(c_onnx, target_path, validate_fn=validate_onnx_file)
                    replaced_artifacts.append((target_name, target_path))
                    print(f"  ✓ Deployed ONNX atomically to: {target_path}")

                # 2. Update PyTorch Checkpoint
                atomic_copy_file(c_ckpt, self.config.checkpoint, validate_fn=validate_torch_checkpoint)
                replaced_artifacts.append(("checkpoint", self.config.checkpoint))
                print(f"  ✓ Deployed Checkpoint atomically to: {self.config.checkpoint}")

                # 3. Update Authoritative Classes JSON
                atomic_copy_file(c_classes, self.config.classes_json, validate_fn=validate_json_file)
                replaced_artifacts.append(("classes_json", self.config.classes_json))
                print(f"  ✓ Deployed classes.json atomically to: {self.config.classes_json}")

                # 4. Generate & Deploy Agronomic Guidance Metadata (frontend & backend)
                with open(c_classes, "r", encoding="utf-8") as f:
                    classes_data = json.load(f)
                build_disease_classes_json(
                    classes=classes_data["classes"],
                    output_paths=[str(self.config.backend_json), str(self.config.frontend_json)],
                    allow_production=True,
                )
                replaced_artifacts.append(("backend_json", self.config.backend_json))
                replaced_artifacts.append(("frontend_json", self.config.frontend_json))
                print("  ✓ Deployed disease_classes.json metadata to backend and frontend.")

                # 5. Post-Promotion Verification: Comprehensive bundle health check
                print("[Promotion Guard] Running post-promotion bundle verification...")
                self._verify_production_bundle()
                print("  ✓ Post-promotion bundle verification PASSED.")

            except Exception as exc:
                print(f"\n[Promotion Guard] ❌ FATAL ERROR during promotion: {exc}")
                print(f"[Promotion Guard] Triggering AUTOMATED FAIL-STOP ROLLBACK to: {backup_folder}")
                rollback_engine = ModelRollback(self.config)
                rollback_engine.restore_backup(backup_folder, dry_run=False, force=True, acquire_lock=False)
                raise PromotionExecutionError(
                    f"Promotion aborted and automatically rolled back to prior release: {exc}"
                ) from exc

            print("\n" + "=" * 65)
            print("          PROMOTION TO PRODUCTION COMPLETED SUCCESSFULLY")
            print("=" * 65)
            print(f" Promoted Candidate: {candidate_id}")
            print(f" Pre-Promotion Backup: {backup_folder}")
            print("=" * 65)

            return {
                "status": "PROMOTED",
                "candidate_id": candidate_id,
                "backup_dir": str(backup_folder),
            }

    def _verify_production_bundle(self) -> None:
        """Verifies that all production artifacts exist, parse, and maintain class parity."""
        bundle_map = self.config.get_bundle_map()
        for name, path in bundle_map.items():
            if not path.is_file():
                raise PromotionValidationError(f"Post-promotion verification failed: missing {name} at {path}")

        validate_onnx_file(self.config.backend_onnx)
        validate_onnx_file(self.config.frontend_onnx)
        validate_torch_checkpoint(self.config.checkpoint)
        validate_json_file(self.config.backend_json)
        validate_json_file(self.config.frontend_json)
        validate_json_file(self.config.classes_json)

        # Verify backend and frontend checksum parity
        backend_onnx_sha = compute_file_sha256(self.config.backend_onnx)
        frontend_onnx_sha = compute_file_sha256(self.config.frontend_onnx)
        if backend_onnx_sha != frontend_onnx_sha:
            raise PromotionValidationError("Backend and Frontend ONNX checksum mismatch post-promotion!")

        backend_meta_sha = compute_file_sha256(self.config.backend_json)
        frontend_meta_sha = compute_file_sha256(self.config.frontend_json)
        if backend_meta_sha != frontend_meta_sha:
            raise PromotionValidationError("Backend and Frontend disease_classes.json checksum mismatch post-promotion!")


class ModelRollback:
    """
    Discovers, verifies, and restores prior release bundles with cryptographic integrity checks.
    """

    def __init__(self, config: Optional[ReleaseBundleConfig] = None):
        self.config = config or ReleaseBundleConfig()

    def list_backups(self) -> List[Dict[str, Any]]:
        """Lists all available backups in the backup directory, sorted newest to oldest."""
        if not self.config.backup_dir.is_dir():
            return []

        backups = []
        for item in sorted(self.config.backup_dir.iterdir(), reverse=True):
            if item.is_dir() and (item / "backup_manifest.json").is_file():
                try:
                    with open(item / "backup_manifest.json", "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    backups.append({
                        "path": str(item),
                        "backup_id": meta.get("backup_id", item.name),
                        "created_at": meta.get("created_at"),
                        "reason": meta.get("reason"),
                        "artifacts_count": len(meta.get("artifacts", {})),
                    })
                except Exception:
                    continue
        return backups

    def validate_backup(self, backup_dir: Path) -> Dict[str, Any]:
        """
        Validates backup completeness and cryptographic integrity against backup_manifest.json:
        1. Checks existence of backup_manifest.json.
        2. Asserts all required bundle artifacts are present.
        3. Recalculates SHA-256 for each file and confirms exact match with manifest.
        4. Validates ONNX and PyTorch checkpoints.
        """
        b_dir = Path(backup_dir).resolve()
        if not b_dir.is_dir():
            raise CorruptedBackupError(f"Backup directory not found: {b_dir}")

        manifest_file = b_dir / "backup_manifest.json"
        if not manifest_file.is_file():
            raise CorruptedBackupError(f"backup_manifest.json missing in backup directory: {b_dir}")

        validate_json_file(manifest_file)
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        artifacts = manifest.get("artifacts", {})
        required_artifacts = {"backend_onnx", "frontend_onnx", "backend_json", "frontend_json", "checkpoint", "classes_json"}

        missing_keys = required_artifacts - set(artifacts.keys())
        if missing_keys:
            raise CorruptedBackupError(f"Incomplete backup bundle: missing artifact definitions for {missing_keys}")

        for name, info in artifacts.items():
            filename = info.get("backup_filename")
            expected_sha = info.get("sha256")
            if not filename or not expected_sha:
                raise CorruptedBackupError(f"Malformed manifest entry for artifact '{name}'")

            target_file = b_dir / filename
            if not target_file.is_file():
                raise CorruptedBackupError(f"Backup file missing from disk: {target_file}")

            actual_sha = compute_file_sha256(target_file)
            if actual_sha != expected_sha:
                raise CorruptedBackupError(
                    f"Cryptographic corruption in backup artifact '{name}': expected {expected_sha}, found {actual_sha}"
                )

        # Validate structural validity of models in backup
        validate_onnx_file(b_dir / artifacts["backend_onnx"]["backup_filename"])
        validate_torch_checkpoint(b_dir / artifacts["checkpoint"]["backup_filename"])
        validate_json_file(b_dir / artifacts["classes_json"]["backup_filename"])

        return manifest

    def restore_backup(
        self,
        backup_dir: Path,
        dry_run: bool = True,
        confirm_backup_id: Optional[str] = None,
        force: bool = False,
        acquire_lock: bool = True,
    ) -> Dict[str, Any]:
        """
        Restores a complete validated backup bundle to production destinations.
        DEFAULT IS DRY-RUN. Refuses to restore without explicit confirmation unless force=True (internal rollback).
        """
        b_dir = Path(backup_dir).resolve()

        def _execute_restore():
            print(f"[Rollback Engine] Validating backup bundle integrity at: {b_dir}")
            manifest = self.validate_backup(b_dir)
            backup_id = manifest.get("backup_id", b_dir.name)
            print(f"  ✓ Backup '{backup_id}' cryptographic integrity verified.")

            # DRY-RUN EXIT PATH: Safe by default
            if dry_run and not force:
                print("\n" + "=" * 65)
                print("        ROLLBACK ENGINE DRY-RUN MODE: NO RESTORATIONS PERFORMED")
                print("=" * 65)
                print(f" Backup ID:       {backup_id}")
                print(f" Created At:      {manifest.get('created_at')}")
                print(f" Reason:          {manifest.get('reason')}")
                print(f" Artifacts Count: {len(manifest.get('artifacts', {}))}")
                print(" Backup is 100% verified and RESTORABLE.")
                print(" To execute rollback, an operator must supply:")
                print("   --no-dry-run --confirm-backup-id <BACKUP_ID>")
                print("=" * 65)
                return {
                    "status": "DRY_RUN_PASSED",
                    "backup_id": backup_id,
                    "manifest": manifest,
                }

            if not force and confirm_backup_id != backup_id:
                raise PermissionError(
                    f"ROLLBACK REFUSED: Confirmation ID mismatch. Expected '{backup_id}', got '{confirm_backup_id}'."
                )

            # RESTORATION PATH
            print(f"[Rollback Engine] Restoring complete compatible bundle '{backup_id}' atomically...")
            artifacts = manifest["artifacts"]
            for name, info in artifacts.items():
                src_file = b_dir / info["backup_filename"]
                dest_path = Path(info["target_production_path"]).resolve()
                atomic_copy_file(src_file, dest_path)
                print(f"  ✓ Restored '{name}' atomically to: {dest_path}")

            # POST-RESTORE VALIDATION
            print("[Rollback Engine] Running post-restore bundle verification...")
            for name, info in artifacts.items():
                dest_path = Path(info["target_production_path"]).resolve()
                if not dest_path.is_file():
                    raise RuntimeError(f"Post-restore check failed: {dest_path} does not exist!")
                restored_sha = compute_file_sha256(dest_path)
                if restored_sha != info["sha256"]:
                    raise RuntimeError(
                        f"Post-restore checksum mismatch on {dest_path}: expected {info['sha256']}, got {restored_sha}"
                    )
            print("  ✓ Post-restore bundle verification PASSED.")

            print("\n" + "=" * 65)
            print("             ROLLBACK RESTORATION COMPLETED")
            print("=" * 65)
            print(f" Restored Release Backup: {backup_id}")
            print("=" * 65)

            return {
                "status": "RESTORED",
                "backup_id": backup_id,
            }

        if acquire_lock:
            with PromotionLock(self.config.lock_file):
                print("\n[Rollback Engine] Acquired exclusive rollback lock.")
                return _execute_restore()
        else:
            return _execute_restore()


def main():
    parser = argparse.ArgumentParser(description="AgriScan Model Promotion and Rollback Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Promotion Parser
    promote_parser = subparsers.add_parser("promote", help="Promote a candidate model to production")
    promote_parser.add_argument("--candidate", type=str, required=True, help="Path to candidate directory")
    promote_parser.add_argument(
        "--no-dry-run",
        action="store_true",
        default=False,
        help="Execute actual production replacement (Default is dry-run validation only)",
    )
    promote_parser.add_argument(
        "--confirm-candidate-id",
        type=str,
        default=None,
        help="Explicit candidate ID confirmation required when not in dry-run mode",
    )
    promote_parser.add_argument(
        "--authorize-production-promotion",
        action="store_true",
        default=False,
        help="Explicit human authorization confirmation flag",
    )

    # Rollback Parser
    rollback_parser = subparsers.add_parser("rollback", help="Rollback production to a prior validated release")
    rollback_parser.add_argument("--backup-dir", type=str, default=None, help="Path to backup directory to restore")
    rollback_parser.add_argument("--list", action="store_true", help="List all available backups")
    rollback_parser.add_argument(
        "--no-dry-run",
        action="store_true",
        default=False,
        help="Execute actual rollback restoration (Default is dry-run validation only)",
    )
    rollback_parser.add_argument(
        "--confirm-backup-id",
        type=str,
        default=None,
        help="Explicit backup ID confirmation required when not in dry-run mode",
    )

    args = parser.parse_args()

    if args.command == "promote":
        promoter = ModelPromoter()
        promoter.promote(
            candidate_dir=Path(args.candidate),
            dry_run=not args.no_dry_run,
            confirm_candidate_id=args.confirm_candidate_id,
            authorize_promotion=args.authorize_production_promotion,
        )
    elif args.command == "rollback":
        rollback_engine = ModelRollback()
        if args.list:
            backups = rollback_engine.list_backups()
            print(f"\nFound {len(backups)} available backup release(s):")
            for b in backups:
                print(f"  - ID: {b['backup_id']} | Date: {b['created_at']} | Path: {b['path']}")
            return

        if not args.backup_dir:
            print("Error: --backup-dir or --list must be provided for rollback.")
            sys.exit(1)

        rollback_engine.restore_backup(
            backup_dir=Path(args.backup_dir),
            dry_run=not args.no_dry_run,
            confirm_backup_id=args.confirm_backup_id,
        )


if __name__ == "__main__":
    main()
