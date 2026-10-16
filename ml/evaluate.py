import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# Add ml folder and project root to sys.path
_ml_dir = str(Path(__file__).resolve().parent)
_proj_root = str(Path(__file__).resolve().parent.parent)
for p in [_ml_dir, _proj_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from torch.utils.data import DataLoader

from ml.dataset import (
    PlantLeafDataset,
    get_data_transforms,
    create_stratified_splits,
    DEFAULT_DATA_DIR,
)
from ml.model import get_model

DEFAULT_CHECKPOINT_PATH = os.path.join(_ml_dir, "checkpoints", "best_leaf_model.pth")
DEFAULT_ARTIFACTS_DIR = os.path.join(_ml_dir, "artifacts")


def evaluate_model(
    checkpoint_path: str = DEFAULT_CHECKPOINT_PATH,
    data_dir: str = DEFAULT_DATA_DIR,
    output_dir: str = DEFAULT_ARTIFACTS_DIR,
    batch_size: int = 32,
    device_str: str = None,
    test_dataset=None,
    classes=None,
) -> Dict[str, Any]:
    """
    Evaluates fine-tuned model checkpoint on the real held-out test set.
    Computes genuine, non-fabricated metrics: accuracy, precision, recall, F1,
    per-class classification report, and confusion matrix.
    """
    if device_str is None:
        device_str = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(device_str)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[Evaluation] Loading model checkpoint: {checkpoint_path}")
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")

    try:
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    except TypeError:
        checkpoint = torch.load(checkpoint_path, map_location=device)
    if classes is None:
        classes = checkpoint.get("classes")
    model_variant = checkpoint.get("model_variant", "efficientnet_b0")

    if classes is None:
        raise ValueError("Checkpoint does not contain classes metadata.")

    # Recreate model
    model = get_model(num_classes=len(classes), model_variant=model_variant, pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    # Load test split if not directly provided
    if test_dataset is None:
        train_tf, val_test_tf = get_data_transforms()
        full_ds = PlantLeafDataset(root_dir=data_dir, class_list=classes)
        _, _, test_dataset = create_stratified_splits(
            full_ds,
            train_transform=train_tf,
            val_test_transform=val_test_tf,
            seed=42,
        )

    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    print(f"[Evaluation] Evaluating {len(test_dataset)} real test images across {len(classes)} classes...")

    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)
            _, preds = torch.max(outputs, 1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    # Compute genuine metrics
    test_acc = float(np.mean(all_preds == all_labels) * 100.0)
    precision, recall, f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average='macro', zero_division=0
    )

    print("\n" + "="*60)
    print("           REAL PLANTVILLAGE TEST EVALUATION RESULTS")
    print("="*60)
    print(f" Model Architecture: {model_variant}")
    print(f" Test Set Size:      {len(all_labels)} images")
    print(f" Test Accuracy:      {test_acc:.2f}%")
    print(f" Macro Precision:    {precision * 100:.2f}%")
    print(f" Macro Recall:       {recall * 100:.2f}%")
    print(f" Macro F1-Score:     {f1 * 100:.2f}%")
    print("="*60)

    # Classification report
    unique_present = sorted(list(set(all_labels).union(set(all_preds))))
    target_names = [classes[i] for i in unique_present]
    report_dict = classification_report(all_labels, all_preds, target_names=target_names, zero_division=0, output_dict=True)
    report_text = classification_report(all_labels, all_preds, target_names=target_names, zero_division=0)

    report_file = os.path.join(output_dir, "classification_report.txt")
    with open(report_file, "w") as f:
        f.write("AGRISCAN REAL PLANTVILLAGE CLASSIFICATION REPORT\n")
        f.write(f"Model Variant: {model_variant}\n")
        f.write(f"Test Accuracy: {test_acc:.2f}%\n")
        f.write(f"Macro F1-Score: {f1 * 100:.2f}%\n")
        f.write(f"Macro Precision: {precision * 100:.2f}%\n")
        f.write(f"Macro Recall: {recall * 100:.2f}%\n\n")
        f.write(report_text)

    # Confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(14, 12))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Greens)
    plt.title(f'PlantVillage EfficientNet Confusion Matrix (Acc: {test_acc:.2f}%)', fontsize=14, pad=15)
    plt.colorbar()
    
    tick_marks = np.arange(len(target_names))
    plt.xticks(tick_marks, target_names, rotation=90, fontsize=6)
    plt.yticks(tick_marks, target_names, fontsize=6)
    plt.ylabel('True Class', fontsize=10)
    plt.xlabel('Predicted Class', fontsize=10)
    plt.tight_layout()

    cm_path = os.path.join(output_dir, "confusion_matrix.png")
    plt.savefig(cm_path, dpi=200)
    plt.close()

    # Save metrics JSON
    metrics_summary = {
        "model_variant": model_variant,
        "checkpoint": str(checkpoint_path),
        "total_test_samples": int(len(all_labels)),
        "num_classes": len(classes),
        "test_accuracy": round(test_acc, 2),
        "macro_precision": round(float(precision * 100), 2),
        "macro_recall": round(float(recall * 100), 2),
        "macro_f1": round(float(f1 * 100), 2),
        "report_summary": {k: v for k, v in report_dict.items() if k in ["accuracy", "macro avg", "weighted avg"]},
        "note": "PlantVillage images feature clean, controlled laboratory backgrounds. Real field conditions may show domain shift.",
    }
    metrics_json_path = os.path.join(output_dir, "test_metrics.json")
    with open(metrics_json_path, "w") as f:
        json.dump(metrics_summary, f, indent=2)

    print(f"\n[Evaluation] Saved artifacts:")
    print(f"  - Report: {report_file}")
    print(f"  - Confusion Matrix: {cm_path}")
    print(f"  - Metrics JSON: {metrics_json_path}")

    return metrics_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Fine-tuned Leaf Disease Model on Real PlantVillage")
    parser.add_argument("--checkpoint", type=str, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--data_dir", type=str, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output_dir", type=str, default=DEFAULT_ARTIFACTS_DIR)
    parser.add_argument("--batch_size", type=int, default=32)
    args = parser.parse_args()

    evaluate_model(
        checkpoint_path=args.checkpoint,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
    )
