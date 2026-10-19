#!/usr/bin/env python3
"""
AgriScan Continuous ML Monitoring & Drift Analysis Engine
Statistically grounded detection of data and prediction drift:
1. Population Stability Index (PSI) calculation against documented baseline
2. Jensen-Shannon (JS) divergence calculation
3. Sample sufficiency gating (avoids noisy false alerts on low traffic)
4. Confidence distribution tracking and low-confidence anomaly detection
5. Zero dependency on raw images or proprietary platforms

Important distinctions:
- Prediction distribution shifts are signals for agronomic investigation, NOT proof of model failure.
- True accuracy requires ground-truth labels evaluated via offline test sets.
- Drift alerts do NOT automatically retrain or promote models.
"""

import os
import sys
import json
import math
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

_proj_root = str(Path(__file__).resolve().parent.parent)
_ml_dir = str(Path(__file__).resolve().parent)
DEFAULT_BASELINE_PATH = os.path.join(_ml_dir, "artifacts", "baseline_distribution.json")

# Standard PSI benchmark thresholds
DEFAULT_MIN_SAMPLES = 30
DEFAULT_PSI_WARNING = 0.10
DEFAULT_PSI_CRITICAL = 0.25
EPSILON = 1e-5  # Smoothing factor to prevent log(0) and division by zero


def calculate_psi(expected_dist: Dict[str, float], actual_counts: Dict[str, int]) -> Tuple[float, Dict[str, Any]]:
    """
    Computes Population Stability Index (PSI) between expected proportions and actual counts.
    Formula: PSI = sum( (Actual_i - Expected_i) * ln(Actual_i / Expected_i) )
    Returns (total_psi, per_bin_details).
    """
    total_actual = sum(actual_counts.values())
    if total_actual == 0:
        return 0.0, {}

    all_keys = sorted(list(set(expected_dist.keys()) | set(actual_counts.keys())))
    total_psi = 0.0
    details = {}

    for k in all_keys:
        expected_prop = expected_dist.get(k, 0.0)
        actual_cnt = actual_counts.get(k, 0)
        actual_prop = actual_cnt / total_actual

        # Apply epsilon smoothing for numerical stability
        e_smooth = max(expected_prop, EPSILON)
        a_smooth = max(actual_prop, EPSILON)

        bin_psi = (a_smooth - e_smooth) * math.log(a_smooth / e_smooth)
        total_psi += bin_psi

        details[k] = {
            "expected_proportion": round(expected_prop, 4),
            "actual_count": actual_cnt,
            "actual_proportion": round(actual_prop, 4),
            "delta_proportion": round(actual_prop - expected_prop, 4),
            "contribution_to_psi": round(bin_psi, 5),
        }

    return round(total_psi, 4), details


def calculate_jensen_shannon_divergence(p_dist: Dict[str, float], q_dist: Dict[str, float]) -> float:
    """
    Computes symmetric Jensen-Shannon divergence between two discrete probability distributions.
    Bounded between 0 (identical) and 1 (completely disjoint).
    """
    keys = set(p_dist.keys()) | set(q_dist.keys())
    # Normalize
    sum_p = sum(p_dist.values()) or 1.0
    sum_q = sum(q_dist.values()) or 1.0

    p_norm = {k: p_dist.get(k, 0.0) / sum_p for k in keys}
    q_norm = {k: q_dist.get(k, 0.0) / sum_q for k in keys}

    # Midpoint distribution M = 0.5 * (P + Q)
    m = {k: 0.5 * (p_norm[k] + q_norm[k]) for k in keys}

    def kl_div(a, b):
        div = 0.0
        for k in keys:
            if a[k] > 0 and b[k] > 0:
                div += a[k] * math.log(a[k] / b[k], 2)
        return div

    jsd = 0.5 * kl_div(p_norm, m) + 0.5 * kl_div(q_norm, m)
    return round(math.sqrt(max(0.0, jsd)), 4)


class DriftDetector:
    def __init__(
        self,
        baseline_path: str = DEFAULT_BASELINE_PATH,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        psi_warning: float = DEFAULT_PSI_WARNING,
        psi_critical: float = DEFAULT_PSI_CRITICAL,
    ):
        self.baseline_path = baseline_path
        self.min_samples = min_samples
        self.psi_warning = psi_warning
        self.psi_critical = psi_critical
        self.baseline = self._load_baseline()

    def _load_baseline(self) -> Dict[str, Any]:
        """Loads documented baseline distribution."""
        if not os.path.exists(self.baseline_path):
            raise FileNotFoundError(
                f"Documented baseline not found at {self.baseline_path}. Run baseline setup first."
            )
        with open(self.baseline_path, "r") as f:
            return json.load(f)

    def evaluate_drift(
        self,
        observed_predictions: Dict[str, int],
        confidence_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates drift of observed predictions against documented baseline.
        """
        total_samples = sum(observed_predictions.values())
        baseline_classes = self.baseline.get("class_proportions", {})
        baseline_crops = self.baseline.get("crop_proportions", {})

        # Aggregated observed crops
        observed_crops = {}
        for cls_name, cnt in observed_predictions.items():
            crop = cls_name.split("___")[0]
            observed_crops[crop] = observed_crops.get(crop, 0) + cnt

        # ----------------------------------------------------
        # Gate: Sample Sufficiency Check
        # ----------------------------------------------------
        if total_samples < self.min_samples:
            return {
                "status": "INSUFFICIENT_DATA",
                "sample_count": total_samples,
                "min_sample_size": self.min_samples,
                "drift_detected": False,
                "psi_score": None,
                "js_divergence": None,
                "message": (
                    f"Sample count ({total_samples}) is below minimum threshold ({self.min_samples}). "
                    "Drift analysis skipped to prevent noisy alerts."
                ),
                "timestamp": self.baseline.get("metadata", {}).get("created_at"),
            }

        # ----------------------------------------------------
        # Statistical Drift Calculation
        # ----------------------------------------------------
        class_psi, class_details = calculate_psi(baseline_classes, observed_predictions)
        crop_psi, crop_details = calculate_psi(baseline_crops, observed_crops)

        actual_class_props = {k: v / total_samples for k, v in observed_predictions.items()}
        js_div = calculate_jensen_shannon_divergence(baseline_classes, actual_class_props)

        # Determine drift status category
        if class_psi >= self.psi_critical:
            status = "SIGNIFICANT_DRIFT"
            drift_detected = True
            action_recommendation = (
                f"Significant distribution shift observed (PSI={class_psi} >= {self.psi_critical}). "
                "Investigate foliar sample sources, season/crop prevalence, or sensor/lighting shifts. "
                "Verify with a labeled offline validation split before considering fine-tuning."
            )
        elif class_psi >= self.psi_warning:
            status = "MODERATE_DRIFT"
            drift_detected = True
            action_recommendation = (
                f"Moderate distribution shift observed (PSI={class_psi}). "
                "Monitor incoming crop distribution. No immediate intervention required."
            )
        else:
            status = "STABLE"
            drift_detected = False
            action_recommendation = "Prediction distribution is aligned with baseline. No drift detected."

        # Find top shifted classes
        sorted_shifts = sorted(
            class_details.items(),
            key=lambda x: abs(x[1]["delta_proportion"]),
            reverse=True,
        )
        top_shifted_classes = [
            {"class": k, **v} for k, v in sorted_shifts[:5] if abs(v["delta_proportion"]) > 0.01
        ]

        # Confidence analysis if provided
        confidence_summary = {}
        if confidence_data:
            low_conf_count = confidence_data.get("low_confidence_count", 0)
            low_conf_rate = low_conf_count / total_samples if total_samples > 0 else 0.0
            confidence_summary = {
                "low_confidence_count": low_conf_count,
                "low_confidence_rate": round(low_conf_rate, 4),
                "low_confidence_warning": low_conf_rate > 0.15,
            }

        return {
            "status": status,
            "drift_detected": drift_detected,
            "sample_count": total_samples,
            "min_sample_size": self.min_samples,
            "metrics": {
                "class_psi": class_psi,
                "crop_psi": crop_psi,
                "jensen_shannon_divergence": js_div,
                "psi_thresholds": {
                    "warning": self.psi_warning,
                    "critical": self.psi_critical,
                },
            },
            "crop_details": crop_details,
            "top_shifted_classes": top_shifted_classes,
            "confidence_analysis": confidence_summary,
            "recommendation": action_recommendation,
        }


def main():
    parser = argparse.ArgumentParser(description="AgriScan ML Drift Monitor")
    parser.add_argument("--predictions", help="Path to JSON file containing prediction counts")
    parser.add_argument("--baseline", default=DEFAULT_BASELINE_PATH, help="Path to baseline distribution JSON")
    parser.add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES, help="Minimum sample count threshold")
    parser.add_argument("--psi-threshold", type=float, default=DEFAULT_PSI_CRITICAL, help="Critical PSI threshold")
    parser.add_argument("--output", help="Optional output JSON path for the report")

    args = parser.parse_args()

    detector = DriftDetector(
        baseline_path=args.baseline,
        min_samples=args.min_samples,
        psi_critical=args.psi_threshold,
    )

    if not args.predictions or not os.path.exists(args.predictions):
        print(f"Error: Predictions file not found: {args.predictions}")
        sys.exit(1)

    with open(args.predictions, "r") as f:
        data = json.load(f)

    # Support either direct counts dict or nested {predictionsByDisease: {...}}
    predictions = data.get("predictionsByDisease", data.get("predictions", data))
    conf_data = data.get("confidence", None)

    report = detector.evaluate_drift(predictions, confidence_data=conf_data)

    print("=" * 70)
    print("                 AGRISCAN ML DRIFT ANALYSIS REPORT")
    print("=" * 70)
    print(f"Status:          {report['status']}")
    print(f"Sample Count:    {report['sample_count']} (Min Required: {report['min_sample_size']})")
    if report.get("metrics"):
        print(f"Class PSI:       {report['metrics']['class_psi']} (Critical Threshold: {report['metrics']['psi_thresholds']['critical']})")
        print(f"Crop PSI:        {report['metrics']['crop_psi']}")
        print(f"JS Divergence:   {report['metrics']['jensen_shannon_divergence']}")
    print(f"Recommendation:  {report['recommendation']}")
    print("=" * 70)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {args.output}")

    if report["status"] == "SIGNIFICANT_DRIFT":
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
