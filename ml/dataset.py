import os
import sys
import random
from pathlib import Path
from typing import Optional, TypedDict

import torch
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image, ImageDraw, ImageFilter, UnidentifiedImageError


# Add ml folder to sys.path to support execution from any directory
_ml_dir = str(Path(__file__).resolve().parent)

if _ml_dir not in sys.path:
    sys.path.insert(0, _ml_dir)


# ============================================================
# ImageNet normalization parameters
# ============================================================

NORMALIZE_MEAN = [0.485, 0.456, 0.406]
NORMALIZE_STD = [0.229, 0.224, 0.225]


# ============================================================
# Leaf disease classes
# ============================================================

LEAF_DISEASE_CLASSES = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",

    "Corn___Cercospora_leaf_spot",
    "Corn___Common_rust",
    "Corn___Northern_Leaf_Blight",
    "Corn___healthy",

    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight",
    "Grape___healthy",

    "Pepper_bell___Bacterial_spot",
    "Pepper_bell___healthy",

    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",

    "Rice___Brown_Spot",
    "Rice___Leaf_Blast",
    "Rice___healthy",

    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites",
    "Tomato___Target_Spot",
    "Tomato___Yellow_Leaf_Curl_Virus",
    "Tomato___healthy",
]


# ============================================================
# Type definition for synthetic disease palettes
# ============================================================

class DiseasePalette(TypedDict):
    leaf_base: tuple[int, int, int]
    spots: Optional[tuple[int, int, int]]
    halo: Optional[tuple[int, int, int]]


# ============================================================
# Image transforms
# ============================================================

def get_data_transforms(img_size: int = 224):
    """
    Returns train, validation, and test torchvision transforms
    with robust augmentation.
    """

    train_transform = transforms.Compose([
        transforms.Resize((img_size + 32, img_size + 32)),
        transforms.RandomResizedCrop(
            img_size,
            scale=(0.8, 1.0)
        ),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.3),
        transforms.RandomRotation(degrees=25),
        transforms.ColorJitter(
            brightness=0.2,
            contrast=0.2,
            saturation=0.2,
            hue=0.05
        ),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=NORMALIZE_MEAN,
            std=NORMALIZE_STD
        ),
    ])

    val_test_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=NORMALIZE_MEAN,
            std=NORMALIZE_STD
        ),
    ])

    return train_transform, val_test_transform


# ============================================================
# Plant Leaf Dataset
# ============================================================

class PlantLeafDataset(Dataset):
    """
    Custom Dataset for Plant Leaf Disease Classification.

    Expected directory structure:

        root_dir/
            class_name/
                image1.jpg
                image2.jpg
                ...

    Example:

        data/dataset/
            Tomato___Early_blight/
                sample_001.jpg
                sample_002.jpg
    """

    def __init__(
        self,
        root_dir: str,
        class_list: Optional[list[str]] = None,
        transform=None,
    ):
        self.root_dir = root_dir
        self.transform = transform
        self.samples: list[tuple[str, int]] = []

        # --------------------------------------------------------
        # Determine class list
        # --------------------------------------------------------

        if class_list:
            self.classes = sorted(class_list)

        elif os.path.exists(root_dir):
            self.classes = sorted([
                directory
                for directory in os.listdir(root_dir)
                if os.path.isdir(
                    os.path.join(root_dir, directory)
                )
            ])

        else:
            self.classes = sorted(LEAF_DISEASE_CLASSES)

        # Map class name -> numerical index
        self.class_to_idx = {
            cls_name: index
            for index, cls_name in enumerate(self.classes)
        }

        # --------------------------------------------------------
        # Load image paths
        # --------------------------------------------------------

        if os.path.exists(root_dir):

            for cls_name in self.classes:

                cls_dir = os.path.join(
                    root_dir,
                    cls_name
                )

                if not os.path.isdir(cls_dir):
                    continue

                # SORT filenames for deterministic dataset ordering
                for fname in sorted(os.listdir(cls_dir)):

                    if fname.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".webp")
                    ):
                        image_path = os.path.join(
                            cls_dir,
                            fname
                        )

                        label = self.class_to_idx[cls_name]

                        self.samples.append(
                            (image_path, label)
                        )

    def __len__(self) -> int:
        """
        Return total number of images.
        """
        return len(self.samples)

    def __getitem__(self, index: int):
        """
        Load and return one image and its label.

        The parameter is intentionally named `index` because this
        overrides torch.utils.data.Dataset.__getitem__.
        """

        path, label = self.samples[index]

        try:
            image = Image.open(path).convert("RGB")

        except (
            OSError,
            IOError,
            UnidentifiedImageError,
        ) as exc:

            raise RuntimeError(
                f"Unable to read image: {path}"
            ) from exc

        if self.transform is not None:
            image = self.transform(image)

        return image, label


# ============================================================
# Default dataset directory
# ============================================================

DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "dataset",
)


# ============================================================
# Synthetic Dataset Generator
# ============================================================

def create_synthetic_leaf_dataset(
    output_dir: Optional[str] = None,
    samples_per_class: int = 40,
    img_size: int = 224,
):
    """
    Creates synthetic benchmark leaf images for all classes.

    NOTE:
    This synthetic dataset is intended for pipeline testing.
    For final model quality, use real plant-disease images.
    """

    if output_dir is None:
        output_dir = DEFAULT_DATA_DIR

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    # ========================================================
    # Characteristic color palettes
    # ========================================================

    disease_palettes: dict[str, DiseasePalette] = {

        "healthy": {
            "leaf_base": (46, 139, 87),
            "spots": None,
            "halo": None,
        },

        "Early_blight": {
            "leaf_base": (70, 130, 50),
            "spots": (101, 67, 33),
            "halo": (218, 165, 32),
        },

        "Late_blight": {
            "leaf_base": (60, 110, 45),
            "spots": (47, 30, 20),
            "halo": (128, 128, 0),
        },

        "scab": {
            "leaf_base": (55, 120, 50),
            "spots": (40, 50, 30),
            "halo": (150, 140, 40),
        },

        "rot": {
            "leaf_base": (60, 100, 40),
            "spots": (20, 20, 20),
            "halo": (100, 60, 20),
        },

        "rust": {
            "leaf_base": (85, 140, 45),
            "spots": (180, 80, 20),
            "halo": (200, 150, 30),
        },

        "spot": {
            "leaf_base": (75, 135, 55),
            "spots": (80, 50, 30),
            "halo": (220, 200, 50),
        },

        "Blast": {
            "leaf_base": (90, 150, 60),
            "spots": (110, 75, 45),
            "halo": (190, 180, 70),
        },

        "Mold": {
            "leaf_base": (80, 130, 50),
            "spots": (160, 150, 100),
            "halo": (210, 200, 90),
        },

        "Virus": {
            "leaf_base": (140, 160, 50),
            "spots": (220, 210, 40),
            "halo": (240, 230, 80),
        },

        "mites": {
            "leaf_base": (100, 140, 60),
            "spots": (190, 190, 150),
            "halo": (160, 150, 80),
        },
    }

    print(
        "[Dataset Generator] "
        f"Generating synthetic dataset across "
        f"{len(LEAF_DISEASE_CLASSES)} classes..."
    )

    # ========================================================
    # Generate each class
    # ========================================================

    for cls_name in LEAF_DISEASE_CLASSES:

        cls_dir = os.path.join(
            output_dir,
            cls_name
        )

        os.makedirs(
            cls_dir,
            exist_ok=True
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # Always start with a valid healthy palette.
        # This prevents `palette` from ever being None.
        # ----------------------------------------------------

        palette: DiseasePalette = disease_palettes["healthy"]

        # Search for a disease-specific palette
        for key, candidate_palette in disease_palettes.items():

            if (
                key != "healthy"
                and key.lower() in cls_name.lower()
            ):
                palette = candidate_palette
                break

        # ----------------------------------------------------
        # Generate images
        # ----------------------------------------------------

        for i in range(samples_per_class):

            img_path = os.path.join(
                cls_dir,
                f"sample_{i:03d}.jpg"
            )

            # Don't regenerate existing images
            if os.path.exists(img_path):
                continue

            # ------------------------------------------------
            # Create base image
            # ------------------------------------------------

            img = Image.new(
                "RGB",
                (img_size, img_size),
                color=(240, 240, 235),
            )

            draw = ImageDraw.Draw(img)

            # ------------------------------------------------
            # Draw leaf background with random variation
            # ------------------------------------------------

            base_r, base_g, base_b = palette["leaf_base"]

            dr = random.randint(-15, 15)
            dg = random.randint(-15, 15)
            db = random.randint(-15, 15)

            leaf_color = (
                max(0, min(255, base_r + dr)),
                max(0, min(255, base_g + dg)),
                max(0, min(255, base_b + db)),
            )

            margin = random.randint(15, 30)

            leaf_box = [
                margin,
                margin,
                img_size - margin,
                img_size - margin,
            ]

            draw.ellipse(
                leaf_box,
                fill=leaf_color
            )

            # ------------------------------------------------
            # Central vein
            # ------------------------------------------------

            vein_color = (
                max(0, leaf_color[0] - 20),
                min(255, leaf_color[1] + 20),
                max(0, leaf_color[2] - 20),
            )

            draw.line(
                [
                    (img_size // 2, margin),
                    (
                        img_size // 2,
                        img_size - margin
                    ),
                ],
                fill=vein_color,
                width=3,
            )

            # ------------------------------------------------
            # Diseased leaf spots
            # ------------------------------------------------

            spots = palette["spots"]

            if spots is not None:

                num_spots = random.randint(3, 8)

                for _ in range(num_spots):

                    sx = random.randint(
                        margin + 20,
                        img_size - margin - 20,
                    )

                    sy = random.randint(
                        margin + 20,
                        img_size - margin - 20,
                    )

                    spot_radius = random.randint(
                        8,
                        22
                    )

                    # ----------------------------------------
                    # Halo around lesion
                    # ----------------------------------------

                    halo = palette["halo"]

                    if halo is not None:

                        halo_radius = (
                            spot_radius
                            + random.randint(4, 10)
                        )

                        draw.ellipse(
                            [
                                sx - halo_radius,
                                sy - halo_radius,
                                sx + halo_radius,
                                sy + halo_radius,
                            ],
                            fill=halo,
                        )

                    # ----------------------------------------
                    # Core lesion
                    # ----------------------------------------

                    draw.ellipse(
                        [
                            sx - spot_radius,
                            sy - spot_radius,
                            sx + spot_radius,
                            sy + spot_radius,
                        ],
                        fill=spots,
                    )

            # ------------------------------------------------
            # Slight blur for camera-like appearance
            # ------------------------------------------------

            img = img.filter(
                ImageFilter.GaussianBlur(radius=0.5)
            )

            # ------------------------------------------------
            # Save image
            # ------------------------------------------------

            img.save(
                img_path,
                quality=90
            )

    print(
        "[Dataset Generator] "
        f"Successfully prepared dataset at {output_dir}"
    )


# ============================================================
# Command-line execution
# ============================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="Generate synthetic leaf dataset"
    )

    parser.add_argument(
        "--output_dir",
        type=str,
        default=DEFAULT_DATA_DIR,
        help="Target directory for dataset",
    )

    parser.add_argument(
        "--samples_per_class",
        type=int,
        default=40,
        help="Number of synthetic samples per class",
    )

    parser.add_argument(
        "--img_size",
        type=int,
        default=224,
        help="Square image dimension",
    )

    args = parser.parse_args()

    create_synthetic_leaf_dataset(
        output_dir=args.output_dir,
        samples_per_class=args.samples_per_class,
        img_size=args.img_size,
    )

    # ========================================================
    # Verify dataset loading
    # ========================================================

    train_tf, _ = get_data_transforms()

    ds = PlantLeafDataset(
        args.output_dir,
        transform=train_tf,
    )

    print(
        "[Verification] "
        f"Successfully loaded {len(ds)} images "
        f"across {len(ds.classes)} classes."
    )