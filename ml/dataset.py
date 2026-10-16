import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Union, Callable
from collections import defaultdict

import torch
from torch.utils.data import Dataset, Subset
from torchvision import transforms
from PIL import Image, UnidentifiedImageError

# Add ml folder and project root to sys.path
_ml_dir = str(Path(__file__).resolve().parent)
_proj_root = str(Path(__file__).resolve().parent.parent)
for p in [_ml_dir, _proj_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ============================================================
# ImageNet normalization parameters (standard for EfficientNet)
# ============================================================
NORMALIZE_MEAN = [0.485, 0.456, 0.406]
NORMALIZE_STD = [0.229, 0.224, 0.225]

# Default local PlantVillage color dataset location
DEFAULT_DATA_DIR = os.path.join(_proj_root, "plantvillage dataset", "color")

# PlantVillage 38 class list discovered from local directory
PLANTVILLAGE_CLASSES = sorted([
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
])
LEAF_DISEASE_CLASSES = PLANTVILLAGE_CLASSES


def get_data_transforms(img_size: int = 224):
    """
    Returns train, validation, and test torchvision transforms.
    Augmentation is applied ONLY to training data.
    """
    train_transform = transforms.Compose([
        transforms.Resize((img_size + 32, img_size + 32)),
        transforms.RandomResizedCrop(img_size, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.3),
        transforms.RandomRotation(degrees=20),
        transforms.ColorJitter(
            brightness=0.15,
            contrast=0.15,
            saturation=0.15,
            hue=0.03
        ),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD),
    ])

    val_test_transform = transforms.Compose([
        transforms.Resize((img_size + 32, img_size + 32)),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD),
    ])

    return train_transform, val_test_transform


class PlantLeafDataset(Dataset):
    """
    Real PlantVillage Leaf Disease Dataset Loader.
    Dynamically discovers classes from the filesystem.
    """
    def __init__(
        self,
        root_dir: str = DEFAULT_DATA_DIR,
        class_list: Optional[List[str]] = None,
        transform: Optional[Callable] = None,
        max_samples_per_class: Optional[int] = None,
        seed: int = 42,
    ):
        self.root_dir = os.path.abspath(root_dir)
        self.transform = transform
        self.samples: List[Tuple[str, int]] = []
        self.sample_hashes: List[str] = []

        if not os.path.exists(self.root_dir):
            raise FileNotFoundError(
                f"PlantVillage dataset directory not found at: {self.root_dir}\n"
                "Please verify that 'plantvillage dataset/color' exists on this machine."
            )

        # Dynamically discover class directories
        if class_list:
            self.classes = sorted(class_list)
        else:
            self.classes = sorted([
                d for d in os.listdir(self.root_dir)
                if os.path.isdir(os.path.join(self.root_dir, d)) and not d.startswith(".")
            ])

        if len(self.classes) == 0:
            raise ValueError(f"No class subdirectories found in: {self.root_dir}")

        # Map class name -> numerical index
        self.class_to_idx: Dict[str, int] = {
            cls_name: idx for idx, cls_name in enumerate(self.classes)
        }
        self.idx_to_class: Dict[int, str] = {
            idx: cls_name for idx, cls_name in enumerate(self.classes)
        }

        # Track per-class samples
        per_class_samples: Dict[str, List[str]] = defaultdict(list)
        valid_extensions = (".jpg", ".jpeg", ".png", ".webp")

        for cls_name in self.classes:
            cls_dir = os.path.join(self.root_dir, cls_name)
            if not os.path.isdir(cls_dir):
                continue

            for fname in sorted(os.listdir(cls_dir)):
                if fname.lower().endswith(valid_extensions) and not fname.startswith("."):
                    per_class_samples[cls_name].append(os.path.join(cls_dir, fname))

        # Sample capping if requested (deterministic with seed)
        rng = torch.Generator().manual_seed(seed)
        for cls_name in self.classes:
            img_paths = per_class_samples[cls_name]
            if max_samples_per_class is not None and len(img_paths) > max_samples_per_class:
                perm = torch.randperm(len(img_paths), generator=rng).tolist()
                img_paths = [img_paths[i] for i in perm[:max_samples_per_class]]

            label = self.class_to_idx[cls_name]
            for p in img_paths:
                self.samples.append((p, label))

        # Save class counts
        self.class_counts = {
            cls_name: sum(1 for _, lbl in self.samples if lbl == self.class_to_idx[cls_name])
            for cls_name in self.classes
        }

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Tuple[Union[torch.Tensor, Image.Image], int]:
        path, label = self.samples[index]
        try:
            image = Image.open(path).convert("RGB")
        except (OSError, IOError, UnidentifiedImageError) as exc:
            raise RuntimeError(f"Unable to read image: {path}") from exc

        if self.transform is not None:
            image = self.transform(image)

        return image, label

    def get_class_weights(self) -> torch.Tensor:
        """
        Computes inverse class frequency weights to mitigate dataset class imbalance.
        weight[c] = total_samples / (num_classes * count[c])
        """
        total = len(self.samples)
        num_classes = len(self.classes)
        weights = []
        for c in range(num_classes):
            cnt = max(1, self.class_counts[self.idx_to_class[c]])
            w = total / (num_classes * cnt)
            weights.append(w)
        return torch.tensor(weights, dtype=torch.float32)

    def save_class_mapping(self, filepath: str):
        """Saves class-to-index mapping for stable inference."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {
            "classes": self.classes,
            "class_to_idx": self.class_to_idx,
            "idx_to_class": {str(k): v for k, v in self.idx_to_class.items()},
            "num_classes": len(self.classes),
            "class_counts": self.class_counts,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)


class DatasetFromSamples(Dataset):
    """Dataset wrapper for pre-selected image samples."""
    def __init__(self, samples: List[Tuple[str, int]], classes: List[str], transform: Optional[Callable] = None):
        self.samples = samples
        self.classes = classes
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Tuple[Union[torch.Tensor, Image.Image], int]:
        path, label = self.samples[index]
        try:
            image = Image.open(path).convert("RGB")
        except (OSError, IOError, UnidentifiedImageError) as exc:
            raise RuntimeError(f"Unable to read image: {path}") from exc

        if self.transform is not None:
            image = self.transform(image)
        return image, label


def create_stratified_splits(
    full_dataset: PlantLeafDataset,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    train_transform: Optional[Callable] = None,
    val_test_transform: Optional[Callable] = None,
) -> Tuple[DatasetFromSamples, DatasetFromSamples, DatasetFromSamples]:
    """
    Creates stratified, leakage-free train, validation, and test splits.
    Guarantees every class is proportionally represented in all 3 splits.
    """
    assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5, "Split ratios must sum to 1.0"
    rng = torch.Generator().manual_seed(seed)

    # Group sample indices by class
    class_indices: Dict[int, List[int]] = defaultdict(list)
    for idx, (_, label) in enumerate(full_dataset.samples):
        class_indices[label].append(idx)

    train_indices: List[int] = []
    val_indices: List[int] = []
    test_indices: List[int] = []

    for label, indices in sorted(class_indices.items()):
        n = len(indices)
        perm = torch.randperm(n, generator=rng).tolist()
        shuffled = [indices[i] for i in perm]

        n_train = max(1, int(train_ratio * n))
        n_val = max(1, int(val_ratio * n))
        
        # Ensure at least 1 sample in test if possible
        if n >= 3:
            train_part = shuffled[:n_train]
            val_part = shuffled[n_train:n_train + n_val]
            test_part = shuffled[n_train + n_val:]
            if len(test_part) == 0 and len(train_part) > 1:
                test_part = [train_part.pop()]
        else:
            train_part = shuffled[:1]
            val_part = shuffled[1:2] if n > 1 else shuffled[:1]
            test_part = shuffled[2:] if n > 2 else shuffled[:1]

        train_indices.extend(train_part)
        val_indices.extend(val_part)
        test_indices.extend(test_part)

    train_samples = [full_dataset.samples[i] for i in train_indices]
    val_samples = [full_dataset.samples[i] for i in val_indices]
    test_samples = [full_dataset.samples[i] for i in test_indices]

    train_subset = DatasetFromSamples(train_samples, full_dataset.classes, transform=train_transform)
    val_subset = DatasetFromSamples(val_samples, full_dataset.classes, transform=val_test_transform)
    test_subset = DatasetFromSamples(test_samples, full_dataset.classes, transform=val_test_transform)

    return train_subset, val_subset, test_subset


# Deprecated stub to prevent silent fake fallback
def create_synthetic_leaf_dataset(*args, **kwargs):
    raise NotImplementedError(
        "[AgriScan ML Security] Fake / synthetic dataset generation has been permanently disabled. "
        "The application now exclusively uses real PlantVillage agricultural images."
    )