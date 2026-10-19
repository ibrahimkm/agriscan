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

_MODEL_EXPORTS = {"LeafDiseaseClassifier", "get_model"}
_DATASET_EXPORTS = {
    "PlantLeafDataset",
    "get_data_transforms",
    "create_stratified_splits",
    "PLANTVILLAGE_CLASSES",
    "LEAF_DISEASE_CLASSES",
    "NORMALIZE_MEAN",
    "NORMALIZE_STD",
    "DEFAULT_DATA_DIR",
}


def __getattr__(name: str):
    """
    Lazy module attribute loader (PEP 562).
    Eagerly importing PyTorch models in __init__.py breaks lightweight,
    dependency-free workflows (e.g. drift monitoring and health probes)
    when running in environments without torch.
    Attributes are resolved and cached upon first access.
    """
    if name in _MODEL_EXPORTS:
        try:
            from . import model
        except ImportError:
            import model
        val = getattr(model, name)
        globals()[name] = val
        return val

    if name in _DATASET_EXPORTS:
        try:
            from . import dataset
        except ImportError:
            import dataset
        val = getattr(dataset, name)
        globals()[name] = val
        return val

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return sorted(list(globals().keys()) + __all__)


__all__ = [
    "LeafDiseaseClassifier",
    "get_model",
    "PlantLeafDataset",
    "get_data_transforms",
    "create_stratified_splits",
    "PLANTVILLAGE_CLASSES",
    "LEAF_DISEASE_CLASSES",
    "NORMALIZE_MEAN",
    "NORMALIZE_STD",
    "DEFAULT_DATA_DIR",
]
