#!/usr/bin/env python3
"""
AgriScan ML Pipeline Unit & Parity Test Suite
Validates model artifacts, class mappings, PyTorch architecture,
ONNX Runtime inference, and numerical parity without requiring the full dataset.
"""

import os
import sys
import json
import hashlib
import unittest
from pathlib import Path

# Add project root and ml directory to sys.path
_ml_dir = Path(__file__).resolve().parent
_proj_root = _ml_dir.parent
for p in [str(_ml_dir), str(_proj_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import numpy as np
from PIL import Image
from torchvision import transforms
import onnxruntime as ort

from ml.model import get_model, LeafDiseaseClassifier
from ml.dataset import NORMALIZE_MEAN, NORMALIZE_STD

CHECKPOINT_PATH = _ml_dir / "checkpoints" / "best_leaf_model.pth"
BACKEND_ONNX_PATH = _proj_root / "backend" / "ml_models" / "leaf_disease_model.onnx"
FRONTEND_ONNX_PATH = _proj_root / "frontend" / "public" / "models" / "leaf_disease_model.onnx"
BACKEND_CLASSES_JSON = _proj_root / "backend" / "ml_models" / "disease_classes.json"
FRONTEND_CLASSES_JSON = _proj_root / "frontend" / "public" / "models" / "disease_classes.json"
ARTIFACTS_CLASSES_JSON = _ml_dir / "artifacts" / "classes.json"
SAMPLE_LEAF_PATH = _proj_root / "leaf.JPG"


def sha256_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TestModelArtifacts(unittest.TestCase):
    """Verifies physical presence and checksum parity of all model files."""

    def test_artifacts_exist(self):
        self.assertTrue(CHECKPOINT_PATH.exists(), f"PyTorch checkpoint missing at {CHECKPOINT_PATH}")
        self.assertTrue(BACKEND_ONNX_PATH.exists(), f"Backend ONNX missing at {BACKEND_ONNX_PATH}")
        self.assertTrue(FRONTEND_ONNX_PATH.exists(), f"Frontend ONNX missing at {FRONTEND_ONNX_PATH}")
        self.assertTrue(BACKEND_CLASSES_JSON.exists(), f"Backend classes JSON missing at {BACKEND_CLASSES_JSON}")
        self.assertTrue(FRONTEND_CLASSES_JSON.exists(), f"Frontend classes JSON missing at {FRONTEND_CLASSES_JSON}")
        self.assertTrue(ARTIFACTS_CLASSES_JSON.exists(), f"Artifacts classes JSON missing at {ARTIFACTS_CLASSES_JSON}")
        self.assertTrue(SAMPLE_LEAF_PATH.exists(), f"Sample leaf image missing at {SAMPLE_LEAF_PATH}")

    def test_onnx_checksum_parity(self):
        backend_hash = sha256_file(BACKEND_ONNX_PATH)
        frontend_hash = sha256_file(FRONTEND_ONNX_PATH)
        self.assertEqual(
            backend_hash,
            frontend_hash,
            "Backend and Frontend ONNX models must have identical SHA256 checksums."
        )

    def test_disease_classes_checksum_parity(self):
        backend_hash = sha256_file(BACKEND_CLASSES_JSON)
        frontend_hash = sha256_file(FRONTEND_CLASSES_JSON)
        self.assertEqual(
            backend_hash,
            frontend_hash,
            "Backend and Frontend disease_classes.json must have identical SHA256 checksums."
        )


class TestClassMappings(unittest.TestCase):
    """Verifies strict 38-class parity and order consistency across all targets."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
        except TypeError:
            cls.checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu")
        with open(BACKEND_CLASSES_JSON, "r") as f:
            cls.backend_meta = json.load(f)
        with open(ARTIFACTS_CLASSES_JSON, "r") as f:
            cls.artifacts_classes = json.load(f)

    def test_class_count(self):
        ckpt_classes = self.checkpoint.get("classes", [])
        meta_classes = self.backend_meta.get("classes", [])
        art_classes = self.artifacts_classes.get("classes", [])

        self.assertEqual(len(ckpt_classes), 38, "Checkpoint must contain exactly 38 classes")
        self.assertEqual(len(meta_classes), 38, "Backend metadata must contain exactly 38 classes")
        self.assertEqual(len(art_classes), 38, "Artifacts classes.json must contain exactly 38 classes")

    def test_exact_class_order(self):
        ckpt_classes = self.checkpoint.get("classes", [])
        meta_classes = [c["rawClass"] for c in self.backend_meta.get("classes", [])]
        art_classes = self.artifacts_classes.get("classes", [])

        self.assertEqual(ckpt_classes, meta_classes, "Checkpoint and disease_classes.json class order must match")
        self.assertEqual(ckpt_classes, art_classes, "Checkpoint and classes.json class order must match")

    def test_index_continuity(self):
        for idx, item in enumerate(self.backend_meta["classes"]):
            self.assertEqual(item["index"], idx, f"Index discontinuity at {idx}: found {item['index']}")
            self.assertIn("crop", item)
            self.assertIn("disease", item)
            self.assertIn("severity", item)


class TestModelArchitecture(unittest.TestCase):
    """Verifies PyTorch EfficientNet-B0 instantiation, checkpoint loading, and forward pass."""

    def test_instantiation_and_shape(self):
        model = get_model(num_classes=38, model_variant="efficientnet_b0", pretrained=False)
        self.assertIsInstance(model, LeafDiseaseClassifier)
        dummy_input = torch.randn(1, 3, 224, 224)
        output = model(dummy_input)
        self.assertEqual(output.shape, (1, 38), "Model forward pass must output tensor of shape (1, 38)")

    def test_checkpoint_state_dict_loading(self):
        try:
            checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
        except TypeError:
            checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu")
        model = get_model(num_classes=38, model_variant="efficientnet_b0", pretrained=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()

        dummy = torch.randn(2, 3, 224, 224)
        with torch.no_grad():
            out = model(dummy)
        self.assertEqual(out.shape, (2, 38))
        self.assertFalse(torch.isnan(out).any(), "Model logits must not contain NaN")


class TestONNXInference(unittest.TestCase):
    """Verifies ONNX Runtime session execution, tensor shapes, and inference accuracy."""

    @classmethod
    def setUpClass(cls):
        cls.session = ort.InferenceSession(str(BACKEND_ONNX_PATH))
        cls.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD),
        ])
        with open(BACKEND_CLASSES_JSON, "r") as f:
            cls.meta = json.load(f)
        cls.classes = [c["rawClass"] for c in cls.meta["classes"]]

    def test_onnx_io_contracts(self):
        inputs = self.session.get_inputs()
        outputs = self.session.get_outputs()
        self.assertEqual(len(inputs), 1, "Expected 1 input tensor")
        self.assertEqual(inputs[0].name, "input_image")
        self.assertEqual(len(outputs), 1, "Expected 1 output tensor")
        self.assertEqual(outputs[0].shape[-1], 38, "Expected 38 output classes")

    def test_onnx_leaf_prediction(self):
        img = Image.open(SAMPLE_LEAF_PATH).convert("RGB")
        tensor = self.transform(img).unsqueeze(0).numpy()
        onnx_out = self.session.run(None, {"input_image": tensor})[0][0]

        probs = torch.softmax(torch.from_numpy(onnx_out), dim=0).numpy()
        pred_idx = int(np.argmax(probs))
        pred_class = self.classes[pred_idx]
        conf = float(probs[pred_idx])

        self.assertEqual(pred_class, "Apple___Apple_scab", f"Expected Apple___Apple_scab, got {pred_class}")
        self.assertGreater(conf, 0.85, f"Expected confidence > 85%, got {conf * 100:.2f}%")


class TestPyTorchONNXParity(unittest.TestCase):
    """Verifies numerical equivalence between PyTorch checkpoint and ONNX export."""

    def test_parity_on_real_image(self):
        try:
            checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
        except TypeError:
            checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu")
        pt_model = get_model(num_classes=38, model_variant="efficientnet_b0", pretrained=False)
        pt_model.load_state_dict(checkpoint["model_state_dict"])
        pt_model.eval()

        session = ort.InferenceSession(str(BACKEND_ONNX_PATH))

        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD),
        ])

        img = Image.open(SAMPLE_LEAF_PATH).convert("RGB")
        tensor = transform(img).unsqueeze(0)

        # PyTorch forward
        with torch.no_grad():
            pt_logits = pt_model(tensor).numpy()[0]
            pt_probs = torch.softmax(torch.from_numpy(pt_logits), dim=0).numpy()

        # ONNX forward
        onnx_out = session.run(None, {"input_image": tensor.numpy()})[0][0]
        onnx_probs = torch.softmax(torch.from_numpy(onnx_out), dim=0).numpy()

        max_prob_diff = float(np.max(np.abs(pt_probs - onnx_probs)))
        self.assertLess(
            max_prob_diff,
            1e-3,
            f"PyTorch and ONNX predictions differ by {max_prob_diff:.6f} (> 0.001)"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
