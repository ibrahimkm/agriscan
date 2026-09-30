"""
Data module for AgriScan ML pipeline.
Provides access to dataset loaders, transforms, class definitions, and synthetic generator.
"""

import os
import sys
from pathlib import Path

# Ensure ml directory is on sys.path for direct submodule access
_ml_dir = str(Path(__file__).resolve().parent.parent)
if _ml_dir not in sys.path:
    sys.path.insert(0, _ml_dir)

try:
    from ml.dataset import (
        PlantLeafDataset,
        get_data_transforms,
        create_synthetic_leaf_dataset,
        LEAF_DISEASE_CLASSES,
        NORMALIZE_MEAN,
        NORMALIZE_STD,
    )
except ImportError:
    from dataset import (
        PlantLeafDataset,
        get_data_transforms,
        create_synthetic_leaf_dataset,
        LEAF_DISEASE_CLASSES,
        NORMALIZE_MEAN,
        NORMALIZE_STD,
    )

__all__ = [
    "PlantLeafDataset",
    "get_data_transforms",
    "create_synthetic_leaf_dataset",
    "LEAF_DISEASE_CLASSES",
    "NORMALIZE_MEAN",
    "NORMALIZE_STD",
]
