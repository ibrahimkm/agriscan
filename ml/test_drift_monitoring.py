#!/usr/bin/env python3
"""
Unit Test Suite for AgriScan ML Drift Monitoring (ml/monitor_drift.py)
Tests:
1. Normal (aligned) prediction distribution -> STABLE status
2. Significant distribution shift -> SIGNIFICANT_DRIFT status
3. Sample sufficiency gating (< min_samples) -> INSUFFICIENT_DATA status
4. Jensen-Shannon divergence bounding (0 <= JSD <= 1)
5. Low-confidence anomaly detection
"""

import os
import sys
import unittest
from pathlib import Path

_ml_dir = str(Path(__file__).resolve().parent)
_proj_root = str(Path(__file__).resolve().parent.parent)
for p in [_ml_dir, _proj_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

from ml.monitor_drift import (
    DriftDetector,
    calculate_psi,
    calculate_jensen_shannon_divergence,
    DEFAULT_BASELINE_PATH,
)


class TestDriftMonitoring(unittest.TestCase):
    def setUp(self):
        # Default detector reflecting unconfigured production state
        self.default_detector = DriftDetector(baseline_path=DEFAULT_BASELINE_PATH, min_samples=30)
        # Synthetic test detector with allow_unconfigured_baseline=True for algorithmic math verification
        self.synthetic_detector = DriftDetector(
            baseline_path=DEFAULT_BASELINE_PATH,
            min_samples=30,
            allow_unconfigured_baseline=True,
        )
        self.baseline_classes = self.synthetic_detector.baseline["class_proportions"]

    def test_unconfigured_prediction_drift_baseline_safeguard(self):
        """
        Verify that production model prediction-distribution drift is explicitly disabled
        when the baseline contains only dataset class proportions (not empirical model predictions).
        """
        sample_predictions = {
            "Apple___Apple_scab": 50,
            "Tomato___healthy": 50,
        }
        report = self.default_detector.evaluate_drift(sample_predictions)
        self.assertEqual(report["status"], "BASELINE_UNCONFIGURED")
        self.assertFalse(report["drift_detected"])
        self.assertEqual(report["baseline_type"], "dataset_class_distribution_prior")
        self.assertIn("UNCONFIGURED", report["message"])
        self.assertIn("dataset class frequencies", report["message"])

    def test_sample_sufficiency_gating(self):
        """Synthetic fixture: When total samples < min_samples (30), returns INSUFFICIENT_DATA without false alarm."""
        small_sample = {
            "Apple___Apple_scab": 5,
            "Tomato___healthy": 3,
        }
        report = self.synthetic_detector.evaluate_drift(small_sample)
        self.assertEqual(report["status"], "INSUFFICIENT_DATA")
        self.assertFalse(report["drift_detected"])
        self.assertEqual(report["sample_count"], 8)
        self.assertIn("below minimum threshold", report["message"])

    def test_stable_aligned_distribution(self):
        """Synthetic fixture: When synthetic predictions match baseline proportions, PSI is low and status is STABLE (algorithmic math test, not production evidence)."""
        aligned_predictions = {}
        target_total = 1000
        for cls_name, prop in self.baseline_classes.items():
            aligned_predictions[cls_name] = max(1, int(round(prop * target_total)))

        report = self.synthetic_detector.evaluate_drift(aligned_predictions)
        self.assertEqual(report["status"], "STABLE")
        self.assertFalse(report["drift_detected"])
        self.assertLess(report["metrics"]["class_psi"], 0.10)

    def test_significant_drift_detection(self):
        """Synthetic fixture: When synthetic predictions skew heavily to a single class, flags SIGNIFICANT_DRIFT (algorithmic math test, not production evidence)."""
        shifted_predictions = {
            "Apple___Apple_scab": 950,
            "Tomato___healthy": 50,
        }
        report = self.synthetic_detector.evaluate_drift(shifted_predictions)
        self.assertEqual(report["status"], "SIGNIFICANT_DRIFT")
        self.assertTrue(report["drift_detected"])
        self.assertGreaterEqual(report["metrics"]["class_psi"], 0.25)
        self.assertTrue(len(report["top_shifted_classes"]) > 0)
        self.assertIn("Investigate foliar sample sources", report["recommendation"])

    def test_jensen_shannon_divergence_bounded(self):
        """JS divergence must always be between 0.0 and 1.0."""
        dist_a = {"A": 0.5, "B": 0.5}
        dist_b = {"A": 0.1, "B": 0.9}
        jsd = calculate_jensen_shannon_divergence(dist_a, dist_b)
        self.assertGreaterEqual(jsd, 0.0)
        self.assertLessEqual(jsd, 1.0)

        # Identical distributions should have JSD == 0
        jsd_identical = calculate_jensen_shannon_divergence(dist_a, dist_a)
        self.assertAlmostEqual(jsd_identical, 0.0, places=3)

    def test_confidence_anomaly_detection(self):
        """Synthetic fixture: High low-confidence rate (>15%) triggers confidence warning flag."""
        predictions = {cls: 10 for cls in list(self.baseline_classes.keys())[:10]}
        conf_data = {"low_confidence_count": 25}  # 25 out of 100 = 25% (>15%)

        report = self.synthetic_detector.evaluate_drift(predictions, confidence_data=conf_data)
        self.assertTrue(report["confidence_analysis"]["low_confidence_warning"])
        self.assertEqual(report["confidence_analysis"]["low_confidence_rate"], 0.25)

    def test_pepper_bell_crop_normalization_matches_baseline(self):
        """
        Regression test: Verify Pepper,_bell crop key matches dataset prior crop_proportions
        and does not falsely report zero expected proportion due to comma removal.
        """
        pepper_predictions = {
            "Pepper,_bell___Bacterial_spot": 25,
            "Pepper,_bell___healthy": 25,
        }
        report = self.synthetic_detector.evaluate_drift(pepper_predictions)
        self.assertIn("crop_details", report)
        crop_details = report["crop_details"]

        # Ensure exact key exists with positive expected proportion
        self.assertIn("Pepper,_bell", crop_details)
        expected_prop = crop_details["Pepper,_bell"]["expected_proportion"]
        self.assertGreater(
            expected_prop,
            0.0,
            f"Expected Pepper,_bell proportion to be > 0.0, got {expected_prop}",
        )
        self.assertAlmostEqual(expected_prop, 0.0456, places=3)
        self.assertEqual(crop_details["Pepper,_bell"]["actual_count"], 50)

        # Confirm corrupted key without comma is NOT present
        self.assertNotIn("Pepper_bell", crop_details)

    def test_all_baseline_crops_normalization(self):
        """
        Mapping test: Verify that all 38 classes split on '___'[0] correspond to valid dataset prior crop_proportions
        without creating any unexpected orphan keys with 0 expected frequency.
        """
        baseline_crops = self.synthetic_detector.baseline.get("crop_proportions", {})
        extracted_crops = set()
        for cls_name in self.baseline_classes.keys():
            crop = cls_name.split("___")[0]
            extracted_crops.add(crop)
            self.assertIn(
                crop,
                baseline_crops,
                f"Class '{cls_name}' produced crop '{crop}' not found in baseline crop_proportions",
            )

        self.assertEqual(extracted_crops, set(baseline_crops.keys()))
        self.assertEqual(len(extracted_crops), 14)


if __name__ == "__main__":
    unittest.main()
