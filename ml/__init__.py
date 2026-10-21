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
_VALIDATOR_EXPORTS = {
    "DatasetValidator",
    "validate_dataset",
    "create_leakage_free_splits",
    "inspect_baseline_provenance",
}
_TRAINING_EXPORTS = {
    "train_candidate",
    "load_manifest_split_dataset",
}
_EVALUATE_EXPORTS = {
    "evaluate_candidate",
    "CandidateQualityGates",
    "export_candidate_onnx",
    "verify_onnx_parity",
}
_ATOMIC_WRITE_EXPORTS = {
    "atomic_write_bytes",
    "atomic_write_text",
    "atomic_write_json",
    "atomic_copy_file",
}
_PROMOTION_EXPORTS = {
    "ModelPromoter",
    "ModelRollback",
    "ReleaseBundleConfig",
    "PromotionLock",
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

    if name in _VALIDATOR_EXPORTS:
        try:
            from . import dataset_validator
        except ImportError:
            import dataset_validator
        val = getattr(dataset_validator, name)
        globals()[name] = val
        return val

    if name in _TRAINING_EXPORTS:
        try:
            from . import ct_train
        except ImportError:
            import ct_train
        val = getattr(ct_train, name)
        globals()[name] = val
        return val

    if name in _EVALUATE_EXPORTS:
        try:
            from . import ct_evaluate
        except ImportError:
            import ct_evaluate
        val = getattr(ct_evaluate, name)
        globals()[name] = val
        return val

    if name in _ATOMIC_WRITE_EXPORTS:
        try:
            from . import atomic_write
        except ImportError:
            import atomic_write
        val = getattr(atomic_write, name)
        globals()[name] = val
        return val

    if name in _PROMOTION_EXPORTS:
        try:
            from . import promotion
        except ImportError:
            import promotion
        val = getattr(promotion, name)
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
    "DatasetValidator",
    "validate_dataset",
    "create_leakage_free_splits",
    "inspect_baseline_provenance",
    "train_candidate",
    "load_manifest_split_dataset",
    "evaluate_candidate",
    "CandidateQualityGates",
    "export_candidate_onnx",
    "verify_onnx_parity",
    "atomic_write_bytes",
    "atomic_write_text",
    "atomic_write_json",
    "atomic_copy_file",
    "ModelPromoter",
    "ModelRollback",
    "ReleaseBundleConfig",
    "PromotionLock",
]
