import os
import sys
import time
import argparse
from pathlib import Path

# Add ml folder and project root to sys.path to support execution from any directory
_ml_dir = str(Path(__file__).resolve().parent)
_proj_root = str(Path(__file__).resolve().parent.parent)
for p in [_ml_dir, _proj_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from tqdm import tqdm

try:
    from ml.dataset import (
        PlantLeafDataset,
        get_data_transforms,
        create_synthetic_leaf_dataset,
        LEAF_DISEASE_CLASSES,
        DEFAULT_DATA_DIR
    )
except ImportError:
    from dataset import (
        PlantLeafDataset,
        get_data_transforms,
        create_synthetic_leaf_dataset,
        LEAF_DISEASE_CLASSES,
        DEFAULT_DATA_DIR
    )

try:
    from ml.model import get_model
except ImportError:
    from model import get_model

DEFAULT_OUTPUT_DIR = os.path.join(_ml_dir, "checkpoints")

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
        
    epoch_loss = running_loss / total
    epoch_acc = (correct / total) * 100.0
    return epoch_loss, epoch_acc

def evaluate(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for images, labels in tqdm(dataloader, desc="Validating", leave=False):
            images = images.to(device)
            labels = labels.to(device)
            
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += torch.sum(preds == labels.data).item()
            total += labels.size(0)
            
    val_loss = running_loss / total
    val_acc = (correct / total) * 100.0
    return val_loss, val_acc

def train_pipeline(
    data_dir=None,
    output_dir=None,
    epochs_stage1=5,
    epochs_stage2=10,
    batch_size=32,
    lr_stage1=1e-3,
    lr_stage2=1e-4,
    model_variant="small",
    device_str="mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
):
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device(device_str)
    print(f"[{time.strftime('%X')}] Using execution device: {device}")
    
    # Check if dataset exists, if not generate it
    if not os.path.exists(data_dir) or len(os.listdir(data_dir)) == 0:
        print("[Dataset] No dataset found. Generating high-quality leaf dataset...")
        create_synthetic_leaf_dataset(output_dir=data_dir, samples_per_class=40)
    
    train_transform, val_transform = get_data_transforms()
    
    # Load train and validation datasets with proper transforms
    train_full = PlantLeafDataset(data_dir, class_list=LEAF_DISEASE_CLASSES, transform=train_transform)
    val_full = PlantLeafDataset(data_dir, class_list=LEAF_DISEASE_CLASSES, transform=val_transform)
    
    num_classes = len(train_full.classes)
    total_size = len(train_full)
    print(f"[Dataset] Total samples: {total_size} across {num_classes} classes.")
    
    # Train / Val / Test split (70% / 15% / 15%)
    indices = torch.randperm(total_size, generator=torch.Generator().manual_seed(42)).tolist()
    train_size = int(0.70 * total_size)
    val_size = int(0.15 * total_size)
    
    train_indices = indices[:train_size]
    val_indices = indices[train_size:train_size + val_size]
    test_indices = indices[train_size + val_size:]
    
    train_dataset = torch.utils.data.Subset(train_full, train_indices)
    val_dataset = torch.utils.data.Subset(val_full, val_indices)
    test_dataset = torch.utils.data.Subset(val_full, test_indices)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    # Initialize Pretrained MobileNetV3 Model
    print(f"[Model] Initializing pretrained MobileNetV3-{model_variant.capitalize()} with {num_classes} classes...")
    model = get_model(num_classes=num_classes, model_variant=model_variant, pretrained=True)
    model = model.to(device)
    
    criterion = nn.CrossEntropyLoss()
    
    best_val_acc = 0.0
    best_checkpoint_path = os.path.join(output_dir, "best_leaf_model.pth")
    
    # -------------------------------------------------------------
    # STAGE 1: Train Classifier Head (Feature Extraction)
    # -------------------------------------------------------------
    print("\n" + "="*50)
    print(f" STAGE 1: Training Classifier Head ({epochs_stage1} Epochs)")
    print("="*50)
    model.freeze_backbone()
    
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr_stage1,
        weight_decay=1e-4
    )
    
    for epoch in range(1, epochs_stage1 + 1):
        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        
        print(f"Epoch {epoch:02d}/{epochs_stage1:02d} | Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%")
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'classes': train_full.classes,
                'model_variant': model_variant
            }, best_checkpoint_path)
            
    # -------------------------------------------------------------
    # STAGE 2: Fine-Tuning Backbone + Head
    # -------------------------------------------------------------
    print("\n" + "="*50)
    print(f" STAGE 2: Fine-Tuning Backbone Layers ({epochs_stage2} Epochs)")
    print("="*50)
    model.unfreeze_backbone(unfreeze_last_n_layers=6)
    
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr_stage2,
        weight_decay=1e-4
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs_stage2, eta_min=1e-6)
    
    for epoch in range(1, epochs_stage2 + 1):
        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        
        print(f"Epoch {epoch:02d}/{epochs_stage2:02d} | Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}% | LR: {scheduler.get_last_lr()[0]:.6f}")
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                'epoch': epoch + epochs_stage1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'classes': train_full.classes,
                'model_variant': model_variant
            }, best_checkpoint_path)
            print(f"  --> [Saved Best Model Checkpoint] Validation Accuracy: {best_val_acc:.2f}%")
            
    print("\n" + "="*50)
    print(f" TRAINING COMPLETE! Best Validation Accuracy: {best_val_acc:.2f}%")
    print(f" Model saved at: {best_checkpoint_path}")
    print("="*50)
    
    return best_checkpoint_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune MobileNetV3 on Leaf Disease Dataset")
    parser.add_argument("--data_dir", type=str, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output_dir", type=str, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--epochs_stage1", type=int, default=3)
    parser.add_argument("--epochs_stage2", type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--variant", type=str, default="small", choices=["small", "large"])
    args = parser.parse_args()
    
    train_pipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs_stage1=args.epochs_stage1,
        epochs_stage2=args.epochs_stage2,
        batch_size=args.batch_size,
        model_variant=args.variant
    )
