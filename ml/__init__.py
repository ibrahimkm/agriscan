"""
ML package for AgriScan Plant Leaf Disease Detection and Classification.
"""

import os
import sys
from pathlib import Path

# Ensure ml package directory is in sys.path
_current_dir = str(Path(__file__).resolve().parent)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

try:
    from .model import LeafDiseaseClassifier, get_model
    from .dataset import (
        PlantLeafDataset,
        get_data_transforms,
        create_synthetic_leaf_dataset,
        LEAF_DISEASE_CLASSES,
        NORMALIZE_MEAN,
        NORMALIZE_STD,
    )
except ImportError:
    from model import LeafDiseaseClassifier, get_model
    from dataset import (
        PlantLeafDataset,
        get_data_transforms,
        create_synthetic_leaf_dataset,
        LEAF_DISEASE_CLASSES,
        NORMALIZE_MEAN,
        NORMALIZE_STD,
    )

__all__ = [
    "LeafDiseaseClassifier",
    "get_model",
    "PlantLeafDataset",
    "get_data_transforms",
    "create_synthetic_leaf_dataset",
    "LEAF_DISEASE_CLASSES",
    "NORMALIZE_MEAN",
    "NORMALIZE_STD",
]
