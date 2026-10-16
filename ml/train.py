import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

# Add ml folder and project root to sys.path
_ml_dir = str(Path(__file__).resolve().parent)
_proj_root = str(Path(__file__).resolve().parent.parent)
for p in [_ml_dir, _proj_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable
from sklearn.metrics import precision_recall_fscore_support

from ml.dataset import (
    PlantLeafDataset,
    get_data_transforms,
    create_stratified_splits,
    NORMALIZE_MEAN,
    NORMALIZE_STD,
    DEFAULT_DATA_DIR,
)
from ml.model import get_model
from ml.evaluate import evaluate_model

DEFAULT_CHECKPOINTS_DIR = os.path.join(_ml_dir, "checkpoints")
DEFAULT_ARTIFACTS_DIR = os.path.join(_ml_dir, "artifacts")


def train_one_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in tqdm(dataloader, desc="Training", leave=False):
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, preds = torch.max(outputs, 1)
        correct += torch.sum(preds == labels.data).item()
        total += labels.size(0)

    epoch_loss = running_loss / max(1, total)
    epoch_acc = (correct / max(1, total)) * 100.0
    return epoch_loss, epoch_acc


def validate_epoch(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in tqdm(dataloader, desc="Validating", leave=False):
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    total = len(all_labels)
    val_loss = running_loss / max(1, total)
    val_acc = (sum(p == l for p, l in zip(all_preds, all_labels)) / max(1, total)) * 100.0
    _, _, val_f1, _ = precision_recall_fscore_support(
        all_labels, all_preds, average='macro', zero_division=0
    )
    return val_loss, val_acc, float(val_f1 * 100.0)


def train_pipeline(
    data_dir: str = DEFAULT_DATA_DIR,
    output_dir: str = DEFAULT_CHECKPOINTS_DIR,
    artifacts_dir: str = DEFAULT_ARTIFACTS_DIR,
    model_variant: str = "efficientnet_b0",
    epochs_stage1: int = 2,
    epochs_stage2: int = 4,
    batch_size: int = 32,
    lr_stage1: float = 1e-3,
    lr_stage2: float = 2e-4,
    weight_decay: float = 1e-4,
    max_samples_per_class: Optional[int] = None,
    patience: int = 3,
    device_str: Optional[str] = None,
    run_test_eval: bool = True,
) -> Dict[str, Any]:
    """
    Fine-tunes EfficientNet-B0 on real PlantVillage dataset using a 2-stage transfer learning pipeline:
      Stage 1: Frozen backbone, trains classification head
      Stage 2: Unfrozen backbone, fine-tunes with Cosine Annealing LR and class-weight balanced loss
    """
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(artifacts_dir, exist_ok=True)

    if device_str is None:
        device_str = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(device_str)
    print(f"[{time.strftime('%X')}] Using execution device: {device}")

    # Load real PlantVillage dataset
    print(f"[Dataset] Loading real PlantVillage dataset from: {data_dir}")
    full_ds = PlantLeafDataset(
        root_dir=data_dir,
        max_samples_per_class=max_samples_per_class,
        seed=42
    )

    num_classes = len(full_ds.classes)
    total_samples = len(full_ds)
    print(f"[Dataset] Total samples: {total_samples} across {num_classes} discovered classes.")

    # Save stable class mapping
    class_mapping_path = os.path.join(artifacts_dir, "classes.json")
    full_ds.save_class_mapping(class_mapping_path)
    print(f"[Dataset] Class mapping saved to: {class_mapping_path}")

    # Compute class weights for imbalanced classes
    class_weights = full_ds.get_class_weights().to(device)

    # Data transforms and stratified splits
    train_transform, val_test_transform = get_data_transforms()
    train_dataset, val_dataset, test_dataset = create_stratified_splits(
        full_ds,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
        train_transform=train_transform,
        val_test_transform=val_test_transform,
    )
    print(f"[Splits] Train: {len(train_dataset)} | Val: {len(val_dataset)} | Test: {len(test_dataset)}")

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # Initialize model
    print(f"\n[Model] Initializing pretrained {model_variant} with {num_classes} outputs...")
    model = get_model(num_classes=num_classes, model_variant=model_variant, pretrained=True)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights)

    best_val_f1 = 0.0
    best_val_acc = 0.0
    best_checkpoint_path = os.path.join(output_dir, "best_leaf_model.pth")
    efficientnet_checkpoint_path = os.path.join(output_dir, "best_efficientnet_model.pth")

    history = {
        "stage1": [],
        "stage2": [],
        "best_val_acc": 0.0,
        "best_val_f1": 0.0,
    }

    # =============================================================
    # STAGE 1: Feature Extraction (Classifier Head)
    # =============================================================
    if epochs_stage1 > 0:
        print("\n" + "="*60)
        print(f" STAGE 1: Training Classifier Head ({epochs_stage1} Epochs)")
        print("="*60)
        model.freeze_backbone()

        optimizer = optim.AdamW(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=lr_stage1,
            weight_decay=weight_decay,
        )

        for epoch in range(1, epochs_stage1 + 1):
            ep_start = time.time()
            train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
            val_loss, val_acc, val_f1 = validate_epoch(model, val_loader, criterion, device)
            ep_time = time.time() - ep_start

            print(
                f"Epoch {epoch:02d}/{epochs_stage1:02d} | "
                f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | "
                f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}% | Val F1: {val_f1:.2f}% | "
                f"Time: {ep_time:.1f}s"
            )

            history["stage1"].append({
                "epoch": epoch,
                "train_loss": round(train_loss, 4),
                "train_acc": round(train_acc, 2),
                "val_loss": round(val_loss, 4),
                "val_acc": round(val_acc, 2),
                "val_f1": round(val_f1, 2),
            })

            if val_f1 > best_val_f1 or val_acc > best_val_acc:
                best_val_f1 = max(best_val_f1, val_f1)
                best_val_acc = max(best_val_acc, val_acc)
                ckpt_data = {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_acc": val_acc,
                    "val_f1": val_f1,
                    "val_loss": val_loss,
                    "classes": full_ds.classes,
                    "class_to_idx": full_ds.class_to_idx,
                    "idx_to_class": full_ds.idx_to_class,
                    "model_variant": model_variant,
                    "normalize_mean": NORMALIZE_MEAN,
                    "normalize_std": NORMALIZE_STD,
                }
                torch.save(ckpt_data, best_checkpoint_path)
                torch.save(ckpt_data, efficientnet_checkpoint_path)
                print(f"  --> [Saved Best Checkpoint] Val Acc: {val_acc:.2f}%, Val F1: {val_f1:.2f}%")

    # =============================================================
    # STAGE 2: End-to-End Fine-Tuning
    # =============================================================
    if epochs_stage2 > 0:
        print("\n" + "="*60)
        print(f" STAGE 2: Fine-Tuning Backbone Layers ({epochs_stage2} Epochs)")
        print("="*60)
        model.unfreeze_backbone()

        optimizer = optim.AdamW(
            model.parameters(),
            lr=lr_stage2,
            weight_decay=weight_decay,
        )
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=epochs_stage2, eta_min=1e-6
        )

        stagnant_epochs = 0
        for epoch in range(1, epochs_stage2 + 1):
            ep_start = time.time()
            train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
            val_loss, val_acc, val_f1 = validate_epoch(model, val_loader, criterion, device)
            scheduler.step()
            ep_time = time.time() - ep_start

            print(
                f"Epoch {epoch:02d}/{epochs_stage2:02d} | "
                f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | "
                f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}% | Val F1: {val_f1:.2f}% | "
                f"LR: {scheduler.get_last_lr()[0]:.6f} | Time: {ep_time:.1f}s"
            )

            history["stage2"].append({
                "epoch": epoch + epochs_stage1,
                "train_loss": round(train_loss, 4),
                "train_acc": round(train_acc, 2),
                "val_loss": round(val_loss, 4),
                "val_acc": round(val_acc, 2),
                "val_f1": round(val_f1, 2),
                "lr": scheduler.get_last_lr()[0],
            })

            if val_f1 > best_val_f1 or val_acc > best_val_acc:
                best_val_f1 = max(best_val_f1, val_f1)
                best_val_acc = max(best_val_acc, val_acc)
                stagnant_epochs = 0
                ckpt_data = {
                    "epoch": epoch + epochs_stage1,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_acc": val_acc,
                    "val_f1": val_f1,
                    "val_loss": val_loss,
                    "classes": full_ds.classes,
                    "class_to_idx": full_ds.class_to_idx,
                    "idx_to_class": full_ds.idx_to_class,
                    "model_variant": model_variant,
                    "normalize_mean": NORMALIZE_MEAN,
                    "normalize_std": NORMALIZE_STD,
                }
                torch.save(ckpt_data, best_checkpoint_path)
                torch.save(ckpt_data, efficientnet_checkpoint_path)
                print(f"  --> [Saved Best Checkpoint] Val Acc: {val_acc:.2f}%, Val F1: {val_f1:.2f}%")
            else:
                stagnant_epochs += 1
                if stagnant_epochs >= patience:
                    print(f"\n[Early Stopping] No improvement in validation for {patience} epochs. Stopping.")
                    break

    history["best_val_acc"] = round(best_val_acc, 2)
    history["best_val_f1"] = round(best_val_f1, 2)
    history["duration_seconds"] = round(time.time() - start_time, 2)
    history["num_classes"] = num_classes
    history["total_samples"] = total_samples

    metadata_path = os.path.join(artifacts_dir, "training_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(history, f, indent=2)

    print("\n" + "="*60)
    print(f" TRAINING COMPLETE! Best Val Acc: {best_val_acc:.2f}%, Best Val F1: {best_val_f1:.2f}%")
    print(f" Model saved at: {best_checkpoint_path}")
    print(f" Training metadata saved at: {metadata_path}")
    print("="*60)

    # Automatically run test set evaluation on held-out test split
    test_metrics = None
    if run_test_eval:
        print("\n[Evaluation] Evaluating best model on held-out test set...")
        test_metrics = evaluate_model(
            checkpoint_path=best_checkpoint_path,
            data_dir=data_dir,
            output_dir=artifacts_dir,
            batch_size=batch_size,
            device_str=device_str,
            test_dataset=test_dataset,
            classes=full_ds.classes,
        )

    return {
        "checkpoint_path": best_checkpoint_path,
        "classes": full_ds.classes,
        "history": history,
        "test_metrics": test_metrics,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune EfficientNet-B0 on Real PlantVillage Dataset")
    parser.add_argument("--data_dir", type=str, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output_dir", type=str, default=DEFAULT_CHECKPOINTS_DIR)
    parser.add_argument("--artifacts_dir", type=str, default=DEFAULT_ARTIFACTS_DIR)
    parser.add_argument("--variant", type=str, default="efficientnet_b0")
    parser.add_argument("--epochs_stage1", type=int, default=2)
    parser.add_argument("--epochs_stage2", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr_stage1", type=float, default=1e-3)
    parser.add_argument("--lr_stage2", type=float, default=2e-4)
    parser.add_argument("--max_samples_per_class", type=int, default=None)
    args = parser.parse_args()

    train_pipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        artifacts_dir=args.artifacts_dir,
        model_variant=args.variant,
        epochs_stage1=args.epochs_stage1,
        epochs_stage2=args.epochs_stage2,
        batch_size=args.batch_size,
        lr_stage1=args.lr_stage1,
        lr_stage2=args.lr_stage2,
        max_samples_per_class=args.max_samples_per_class,
    )
