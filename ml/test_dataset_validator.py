"""
Unit tests for AgriScan Dataset Validator & Leakage-Free Splitter (MLOps Phase 3 — Stage B)

These tests use lightweight temporary directories and synthetic PIL images.
They verify all Stage B requirements without requiring the real 1.5 GB PlantVillage dataset:
  1. Missing dataset and invalid directory handling.
  2. Missing, unexpected, and empty classes.
  3. Corrupt and unsupported image handling.
  4. Exact duplicate detection (within-class and cross-class).
  5. Duplicate group isolation (zero cross-partition leakage).
  6. Deterministic assignments with identical seeds.
  7. Seed variation and split ratio validation.
  8. Partition disjointness and manifest integrity.
  9. Preservation of protected production model artifacts.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import hashlib
from pathlib import Path
from PIL import Image

# Ensure ml directory is in sys.path
_test_dir = Path(__file__).resolve().parent
_proj_root = _test_dir.parent
for p in [str(_test_dir), str(_proj_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from ml.dataset_validator import (
    DatasetValidator,
    DatasetValidationResult,
    LeakageFreeSplitter,
    validate_dataset,
    create_leakage_free_splits,
    compute_file_sha256,
    verify_image_integrity,
    load_authoritative_classes,
)

# Reference paths for protected production files
PROTECTED_FILES = [
    _proj_root / "backend" / "ml_models" / "leaf_disease_model.onnx",
    _proj_root / "backend" / "ml_models" / "disease_classes.json",
    _proj_root / "ml" / "artifacts" / "classes.json",
    _proj_root / "ml" / "artifacts" / "test_metrics.json",
]


def create_synthetic_image(filepath: Path, color: tuple = (100, 150, 200), size: tuple = (32, 32)):
    """Helper to create a small valid JPEG image."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color=color)
    img.save(filepath, format="JPEG")


class TestDatasetValidator(unittest.TestCase):
    """Test suite for dataset validation, duplicate detection, and leakage-free splitting."""

    def setUp(self):
        # Record initial checksums of protected production artifacts
        self.protected_hashes = {}
        for p in PROTECTED_FILES:
            if p.exists():
                with open(p, "rb") as f:
                    self.protected_hashes[str(p)] = hashlib.sha256(f.read()).hexdigest()

        # Create temporary working directory for test fixtures
        self.test_dir = tempfile.TemporaryDirectory()
        self.fixtures_path = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

        # Verify that NO protected production artifacts were modified
        for p_str, expected_hash in self.protected_hashes.items():
            p = Path(p_str)
            self.assertTrue(p.exists(), f"Protected file was deleted: {p_str}")
            with open(p, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(
                actual_hash,
                expected_hash,
                f"PROTECTED FILE MODIFIED DURING TEST: {p_str}"
            )

    def test_missing_dataset_directory(self):
        """Verifies safe failure when dataset directory is missing."""
        missing_dir = self.fixtures_path / "non_existent_dataset"
        validator = DatasetValidator(data_dir=missing_dir, authoritative_classes=["ClassA", "ClassB"])
        result = validator.validate()

        self.assertFalse(result.is_valid)
        self.assertEqual(result.valid_images_count, 0)
        self.assertTrue(any("does not exist" in err for err in result.errors))

        splitter = LeakageFreeSplitter(validator=validator)
        with self.assertRaises(ValueError):
            splitter.create_splits()

    def test_not_a_directory(self):
        """Verifies failure when dataset path points to a file instead of a directory."""
        file_path = self.fixtures_path / "regular_file.txt"
        file_path.write_text("Hello World")

        validator = DatasetValidator(data_dir=file_path, authoritative_classes=["ClassA"])
        result = validator.validate()
        self.assertFalse(result.is_valid)
        self.assertTrue(any("not a directory" in err for err in result.errors))

    def test_missing_and_unexpected_classes(self):
        """Verifies detection of missing expected classes and unexpected extra classes."""
        expected = ["Apple___healthy", "Tomato___healthy", "Corn___healthy"]
        ds_dir = self.fixtures_path / "dataset"
        ds_dir.mkdir()

        # Only create Apple___healthy and an unexpected Potato___blight
        create_synthetic_image(ds_dir / "Apple___healthy" / "img1.jpg", color=(10, 20, 30))
        create_synthetic_image(ds_dir / "Potato___blight" / "img2.jpg", color=(40, 50, 60))

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        result = validator.validate()

        self.assertFalse(result.is_valid)
        self.assertIn("Tomato___healthy", result.missing_classes)
        self.assertIn("Corn___healthy", result.missing_classes)
        self.assertIn("Potato___blight", result.unexpected_classes)
        self.assertEqual(result.num_classes_found, 2)
        self.assertEqual(result.expected_classes_count, 3)

    def test_empty_class_detection(self):
        """Verifies detection of empty class subdirectories."""
        expected = ["ClassA", "ClassB"]
        ds_dir = self.fixtures_path / "dataset"
        (ds_dir / "ClassA").mkdir(parents=True)
        (ds_dir / "ClassB").mkdir(parents=True)

        # ClassA has an image, ClassB has nothing
        create_synthetic_image(ds_dir / "ClassA" / "sample.jpg")

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        result = validator.validate()

        self.assertFalse(result.is_valid)
        self.assertIn("ClassB", result.empty_classes)
        self.assertEqual(result.class_counts["ClassB"], 0)
        self.assertEqual(result.class_counts["ClassA"], 1)

    def test_corrupt_images_detection(self):
        """Verifies identification of corrupt or unreadable image files."""
        expected = ["ClassA"]
        ds_dir = self.fixtures_path / "dataset"
        c_dir = ds_dir / "ClassA"
        c_dir.mkdir(parents=True)

        # 1 valid image
        create_synthetic_image(c_dir / "valid.jpg")

        # 1 corrupt image (invalid binary payload)
        corrupt_file = c_dir / "corrupted.jpg"
        corrupt_file.write_bytes(b"MALFORMED_HEADER_NOT_A_VALID_IMAGE_DATA_XYZ")

        # 1 unsupported file format
        text_file = c_dir / "info.txt"
        text_file.write_text("Metadata note")

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected, check_readability=True)
        result = validator.validate()

        self.assertFalse(result.is_valid)
        self.assertEqual(result.valid_images_count, 1)
        self.assertEqual(len(result.corrupted_images), 1)
        self.assertIn("corrupted.jpg", result.corrupted_images[0]["file"])
        self.assertEqual(len(result.unsupported_files), 1)
        self.assertIn("info.txt", result.unsupported_files[0]["file"])

    def test_exact_duplicate_detection(self):
        """Verifies exact duplicate detection both within a class and across classes."""
        expected = ["ClassA", "ClassB"]
        ds_dir = self.fixtures_path / "dataset"

        # Unique Image 1
        create_synthetic_image(ds_dir / "ClassA" / "img1.jpg", color=(255, 0, 0))

        # Duplicate of Image 1 in same class (within-class duplicate)
        shutil.copyfile(ds_dir / "ClassA" / "img1.jpg", ds_dir / "ClassA" / "img1_dup.jpg")

        # Unique Image 2 in ClassB
        create_synthetic_image(ds_dir / "ClassB" / "img2.jpg", color=(0, 255, 0))

        # Copy of Image 2 in ClassA (cross-class duplicate!)
        shutil.copyfile(ds_dir / "ClassB" / "img2.jpg", ds_dir / "ClassA" / "img2_cross_dup.jpg")

        # Unique Image 3 in ClassB
        create_synthetic_image(ds_dir / "ClassB" / "img3.jpg", color=(0, 0, 255))

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        result = validator.validate()

        self.assertTrue(result.is_valid)
        self.assertEqual(result.total_files_inspected, 5)
        self.assertEqual(result.valid_images_count, 5)

        # 2 duplicate groups: (img1 + img1_dup) and (img2 + img2_cross_dup)
        self.assertEqual(result.duplicate_groups_count, 2)
        self.assertEqual(result.redundant_images_count, 2)

        # 1 cross-class duplicate group
        self.assertEqual(len(result.cross_class_duplicates), 1)
        cross_group = result.cross_class_duplicates[0]
        self.assertEqual(set(cross_group["classes"]), {"ClassA", "ClassB"})

    def test_duplicate_group_isolation_across_splits(self):
        """
        Verifies that bitwise-identical images are strictly kept in the same partition
        and NEVER leak across train, val, and test splits.
        """
        expected = ["ClassA", "ClassB", "ClassC"]
        ds_dir = self.fixtures_path / "dataset"

        # Create 10 images per class, with duplicates
        for c in expected:
            c_dir = ds_dir / c
            for i in range(10):
                img_path = c_dir / f"img_{i}.jpg"
                create_synthetic_image(img_path, color=(i * 10, i * 20 % 255, i * 25 % 255))

            # Make img_0 have 3 identical copies
            shutil.copyfile(c_dir / "img_0.jpg", c_dir / "img_0_copy1.jpg")
            shutil.copyfile(c_dir / "img_0.jpg", c_dir / "img_0_copy2.jpg")

            # Make img_1 have 1 identical copy
            shutil.copyfile(c_dir / "img_1.jpg", c_dir / "img_1_copy1.jpg")

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        val_result = validator.validate()
        self.assertTrue(val_result.is_valid)

        splitter = LeakageFreeSplitter(
            validator=validator,
            train_ratio=0.70,
            val_ratio=0.15,
            test_ratio=0.15,
            seed=42,
        )
        manifest = splitter.create_splits()

        train_samples = manifest["splits"]["train"]
        val_samples = manifest["splits"]["val"]
        test_samples = manifest["splits"]["test"]

        # Check total sample conservation
        total_split_samples = len(train_samples) + len(val_samples) + len(test_samples)
        self.assertEqual(total_split_samples, val_result.valid_images_count)

        # Extract content hashes per split
        train_hashes = {s["group_id"] for s in train_samples}
        val_hashes = {s["group_id"] for s in val_samples}
        test_hashes = {s["group_id"] for s in test_samples}

        # Check ZERO cross-partition duplicate leakage
        self.assertEqual(train_hashes & val_hashes, set(), "Duplicate leak between Train and Val!")
        self.assertEqual(train_hashes & test_hashes, set(), "Duplicate leak between Train and Test!")
        self.assertEqual(val_hashes & test_hashes, set(), "Duplicate leak between Val and Test!")

        # Verify that every copy of an image appears in the EXACT same split
        hash_to_split = {}
        for split_name in ["train", "val", "test"]:
            for s in manifest["splits"][split_name]:
                h = s["group_id"]
                if h in hash_to_split:
                    self.assertEqual(
                        hash_to_split[h],
                        split_name,
                        f"Image with hash {h} was assigned to multiple splits: {hash_to_split[h]} and {split_name}"
                    )
                else:
                    hash_to_split[h] = split_name

    def test_deterministic_assignments_same_seed(self):
        """Verifies that running with the same seed produces identical split assignments."""
        expected = ["ClassA", "ClassB"]
        ds_dir = self.fixtures_path / "dataset"
        for c in expected:
            for i in range(8):
                create_synthetic_image(ds_dir / c / f"img_{i}.jpg", color=(i * 20, 50, 100))

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        validator.validate()

        splitter1 = LeakageFreeSplitter(validator=validator, seed=42)
        manifest1 = splitter1.create_splits()

        splitter2 = LeakageFreeSplitter(validator=validator, seed=42)
        manifest2 = splitter2.create_splits()

        # Check identical splits
        self.assertEqual(
            manifest1["splits"]["train"],
            manifest2["splits"]["train"]
        )
        self.assertEqual(
            manifest1["splits"]["val"],
            manifest2["splits"]["val"]
        )
        self.assertEqual(
            manifest1["splits"]["test"],
            manifest2["splits"]["test"]
        )

    def test_different_seeds_produce_different_splits(self):
        """Verifies that different seeds yield distinct random assignments."""
        expected = ["ClassA", "ClassB"]
        ds_dir = self.fixtures_path / "dataset"
        for c in expected:
            for i in range(20):
                create_synthetic_image(ds_dir / c / f"img_{i}.jpg", color=(i * 12 % 255, i * 7 % 255, 100))

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        validator.validate()

        splitter_a = LeakageFreeSplitter(validator=validator, seed=42)
        manifest_a = splitter_a.create_splits()

        splitter_b = LeakageFreeSplitter(validator=validator, seed=9999)
        manifest_b = splitter_b.create_splits()

        train_a_paths = [s["rel_path"] for s in manifest_a["splits"]["train"]]
        train_b_paths = [s["rel_path"] for s in manifest_b["splits"]["train"]]

        # They should not be identical when sample count is sufficiently high
        self.assertNotEqual(train_a_paths, train_b_paths)

    def test_split_ratio_validation(self):
        """Verifies ratio sum and positivity validation."""
        validator = DatasetValidator(data_dir=self.fixtures_path, authoritative_classes=["ClassA"])

        # Sum not 1.0
        with self.assertRaises(ValueError):
            LeakageFreeSplitter(validator=validator, train_ratio=0.8, val_ratio=0.1, test_ratio=0.2)

        # Negative ratio
        with self.assertRaises(ValueError):
            LeakageFreeSplitter(validator=validator, train_ratio=1.1, val_ratio=-0.1, test_ratio=0.0)

        # Zero ratio
        with self.assertRaises(ValueError):
            LeakageFreeSplitter(validator=validator, train_ratio=0.8, val_ratio=0.2, test_ratio=0.0)

    def test_split_disjointness_and_manifest_file_io(self):
        """Verifies file disjointness and manifest file saving/loading."""
        expected = ["ClassA", "ClassB"]
        ds_dir = self.fixtures_path / "dataset"
        for c in expected:
            for i in range(6):
                create_synthetic_image(ds_dir / c / f"img_{i}.jpg", color=(i * 30, 20, 80))

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        validator.validate()

        manifest_file = self.fixtures_path / "test_manifest.json"
        splitter = LeakageFreeSplitter(validator=validator, seed=42)
        manifest = splitter.create_splits(output_manifest_path=manifest_file)

        self.assertTrue(manifest_file.exists())

        with open(manifest_file, "r", encoding="utf-8") as f:
            loaded_manifest = json.load(f)

        self.assertEqual(loaded_manifest["metadata"]["seed"], 42)
        self.assertTrue(loaded_manifest["metadata"]["disjoint_verified"])
        self.assertEqual(loaded_manifest["metadata"]["cross_partition_duplicate_leakage"], 0)
        self.assertEqual(
            len(loaded_manifest["splits"]["train"]),
            len(manifest["splits"]["train"])
        )

    def test_classes_with_missing_splits_reported(self):
        """Verifies that classes with too few duplicate groups are clearly reported."""
        expected = ["TinyClass", "NormalClass"]
        ds_dir = self.fixtures_path / "dataset"

        # TinyClass has only 1 group (2 duplicate copies of the same image)
        create_synthetic_image(ds_dir / "TinyClass" / "tiny1.jpg", color=(10, 10, 10))
        shutil.copyfile(ds_dir / "TinyClass" / "tiny1.jpg", ds_dir / "TinyClass" / "tiny1_copy.jpg")

        # NormalClass has 10 distinct images
        for i in range(10):
            create_synthetic_image(ds_dir / "NormalClass" / f"img_{i}.jpg", color=(i * 20, 80, 90))

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        validator.validate()

        splitter = LeakageFreeSplitter(validator=validator, seed=42)
        manifest = splitter.create_splits()

        missing_reports = manifest["metadata"]["classes_with_missing_splits"]
        self.assertEqual(len(missing_reports), 1)
        self.assertEqual(missing_reports[0]["class_name"], "TinyClass")
        self.assertIn("cannot populate train, val, and test", missing_reports[0]["reason"])

    def test_dataset_fingerprint_changes_with_content(self):
        """Verifies that dataset fingerprint changes if any image is altered."""
        expected = ["ClassA"]
        ds_dir = self.fixtures_path / "dataset"
        img1_path = ds_dir / "ClassA" / "img1.jpg"
        create_synthetic_image(img1_path, color=(50, 50, 50))

        v1 = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        res1 = v1.validate()
        fp1 = res1.dataset_fingerprint

        # Alter image content
        create_synthetic_image(img1_path, color=(200, 200, 200))

        v2 = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        res2 = v2.validate()
        fp2 = res2.dataset_fingerprint

        self.assertNotEqual(fp1, fp2)

    def test_disallowed_test_samples_holdout_protection(self):
        """Verifies that designated sample paths are never placed into the test partition."""
        expected = ["ClassA", "ClassB"]
        ds_dir = self.fixtures_path / "dataset"

        for i in range(10):
            create_synthetic_image(ds_dir / "ClassA" / f"img_a_{i}.jpg", color=(i * 10, 50, 60))
            create_synthetic_image(ds_dir / "ClassB" / f"img_b_{i}.jpg", color=(i * 10, 70, 80))

        validator = DatasetValidator(data_dir=ds_dir, authoritative_classes=expected)
        validator.validate()

        # Designate 2 samples from ClassA and 2 from ClassB as disallowed from test
        disallowed = [
            "ClassA/img_a_0.jpg",
            "ClassA/img_a_1.jpg",
            "ClassB/img_b_0.jpg",
            "ClassB/img_b_1.jpg",
        ]

        # Test action = 'train'
        splitter = LeakageFreeSplitter(
            validator=validator,
            seed=42,
            disallowed_test_paths=disallowed,
            disallowed_test_action="train",
        )
        manifest = splitter.create_splits()

        test_paths = {s["rel_path"] for s in manifest["splits"]["test"]}
        train_paths = {s["rel_path"] for s in manifest["splits"]["train"]}

        for p in disallowed:
            self.assertNotIn(p, test_paths, f"Disallowed sample {p} leaked into test!")
            self.assertIn(p, train_paths, f"Disallowed sample {p} was not placed in train!")

        # Verify holdout protection metadata
        hp = manifest["metadata"]["holdout_protection"]
        self.assertTrue(hp["pilot_exposed_excluded_from_test"])
        self.assertEqual(hp["disallowed_test_samples_count"], 4)
        self.assertEqual(hp["test_partition_pilot_overlap"], 0)

        # Test action = 'exclude'
        splitter_ex = LeakageFreeSplitter(
            validator=validator,
            seed=42,
            disallowed_test_paths=disallowed,
            disallowed_test_action="exclude",
        )
        manifest_ex = splitter_ex.create_splits()
        test_paths_ex = {s["rel_path"] for s in manifest_ex["splits"]["test"]}
        excluded_paths = {s["rel_path"] for s in manifest_ex["splits"]["excluded"]}

        for p in disallowed:
            self.assertNotIn(p, test_paths_ex, f"Disallowed sample {p} leaked into test in exclude mode!")
            self.assertIn(p, excluded_paths, f"Disallowed sample {p} was not in excluded split!")


if __name__ == "__main__":
    unittest.main()
