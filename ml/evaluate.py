import os
import sys
import argparse
from pathlib import Path

# Add ml folder and project root to sys.path to support execution from any directory
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
from torch.utils.data import DataLoader, random_split

try:
    from ml.dataset import PlantLeafDataset, get_data_transforms, LEAF_DISEASE_CLASSES, DEFAULT_DATA_DIR
except ImportError:
    from dataset import PlantLeafDataset, get_data_transforms, LEAF_DISEASE_CLASSES, DEFAULT_DATA_DIR

try:
    from ml.model import get_model
except ImportError:
    from model import get_model

DEFAULT_CHECKPOINT_PATH = os.path.join(_ml_dir, "checkpoints", "best_leaf_model.pth")
DEFAULT_ARTIFACTS_DIR = os.path.join(_ml_dir, "artifacts")

def evaluate_model(
    checkpoint_path=None,
    data_dir=None,
    output_dir=None,
    batch_size=32,
    device_str="mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
):
    if checkpoint_path is None:
        checkpoint_path = DEFAULT_CHECKPOINT_PATH
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    if output_dir is None:
        output_dir = DEFAULT_ARTIFACTS_DIR
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device(device_str)
    
    # Load checkpoint
    print(f"[Evaluation] Loading model checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)
    classes = checkpoint.get('classes', LEAF_DISEASE_CLASSES)
    model_variant = checkpoint.get('model_variant', 'small')
    
    model = get_model(num_classes=len(classes), model_variant=model_variant, pretrained=False)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()
    
    # Load dataset
    _, test_transform = get_data_transforms()
    full_dataset = PlantLeafDataset(data_dir, class_list=classes, transform=test_transform)
    
    total_size = len(full_dataset)
    train_size = int(0.70 * total_size)
    val_size = int(0.15 * total_size)
    test_size = total_size - train_size - val_size
    
    _, _, test_dataset = random_split(
        full_dataset,
        [train_size, val_size, test_size],
        generator=torch.Generator().manual_seed(42)
    )
    
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    all_preds = []
    all_labels = []
    all_probs = []
    
    print("[Evaluation] Running inference over test set...")
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
    all_probs = np.array(all_probs)
    
    # Metrics
    test_acc = np.mean(all_preds == all_labels) * 100.0
    precision, recall, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average='macro', zero_division=0)
    
    print("\n" + "="*55)
    print("           MODEL TEST EVALUATION RESULTS")
    print("="*55)
    print(f" Test Accuracy:      {test_acc:.2f}%")
    print(f" Macro Precision:    {precision * 100:.2f}%")
    print(f" Macro Recall:       {recall * 100:.2f}%")
    print(f" Macro F1-Score:     {f1 * 100:.2f}%")
    print("="*55)
    
    # Unique labels in test set
    unique_labels = sorted(list(set(all_labels).union(set(all_preds))))
    target_names = [classes[i] for i in unique_labels]
    
    report = classification_report(all_labels, all_preds, target_names=target_names, zero_division=0)
    print("\nDetailed Classification Report:")
    print(report)
    
    # Save Report text
    report_file = os.path.join(output_dir, "classification_report.txt")
    with open(report_file, "w") as f:
        f.write(f"Test Accuracy: {test_acc:.2f}%\n")
        f.write(f"Macro F1-Score: {f1 * 100:.2f}%\n\n")
        f.write(str(report))
        
    # Plot Confusion Matrix
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(12, 10))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Greens)
    plt.title(f'Leaf Disease Confusion Matrix (Acc: {test_acc:.1f}%)', fontsize=14, pad=15)
    plt.colorbar()
    
    if len(target_names) <= 15:
        tick_marks = np.arange(len(target_names))
        plt.xticks(tick_marks, target_names, rotation=90, fontsize=8)
        plt.yticks(tick_marks, target_names, fontsize=8)
        
    plt.ylabel('Ground Truth Class', fontsize=11)
    plt.xlabel('Predicted Class', fontsize=11)
    plt.tight_layout()
    
    cm_path = os.path.join(output_dir, "confusion_matrix.png")
    plt.savefig(cm_path, dpi=200)
    plt.close()
    
    print(f"[Evaluation] Artifacts saved:")
    print(f"  - Report: {report_file}")
    print(f"  - Confusion Matrix: {cm_path}")
    
    return {
        "accuracy": test_acc,
        "f1_score": f1,
        "precision": precision,
        "recall": recall
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Fine-tuned Leaf Disease Model")
    parser.add_argument("--checkpoint", type=str, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--data_dir", type=str, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output_dir", type=str, default=DEFAULT_ARTIFACTS_DIR)
    args = parser.parse_args()
    
    evaluate_model(
        checkpoint_path=args.checkpoint,
        data_dir=args.data_dir,
        output_dir=args.output_dir
    )
