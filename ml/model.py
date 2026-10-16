import torch
import torch.nn as nn
from torchvision.models import (
    efficientnet_b0,
    EfficientNet_B0_Weights,
    mobilenet_v3_small,
    MobileNet_V3_Small_Weights,
    mobilenet_v3_large,
    MobileNet_V3_Large_Weights,
)

class LeafDiseaseClassifier(nn.Module):
    """
    AgriScan Vision Model: Transfer Learning Architecture for Plant Leaf Disease Classification.
    Primary Architecture: EfficientNet-B0 fine-tuned on real PlantVillage images.
    Provides state-of-the-art accuracy, lightweight footprint (~18MB), and fast edge inference.
    """
    def __init__(
        self,
        num_classes: int = 38,
        model_variant: str = "efficientnet_b0",
        pretrained: bool = True,
        dropout: float = 0.3,
    ):
        super(LeafDiseaseClassifier, self).__init__()
        self.num_classes = num_classes
        self.model_variant = model_variant.lower()
        self.pretrained = pretrained

        if self.model_variant in ["efficientnet_b0", "efficientnet"]:
            weights = EfficientNet_B0_Weights.DEFAULT if pretrained else None
            self.backbone = efficientnet_b0(weights=weights)
            in_features = self.backbone.classifier[1].in_features
            
            # Custom robust classification head
            self.backbone.classifier = nn.Sequential(
                nn.Dropout(p=dropout, inplace=True),
                nn.Linear(in_features, num_classes)
            )
        elif self.model_variant == "large" or self.model_variant == "mobilenet_v3_large":
            weights = MobileNet_V3_Large_Weights.DEFAULT if pretrained else None
            self.backbone = mobilenet_v3_large(weights=weights)
            in_features = self.backbone.classifier[0].in_features
            self.backbone.classifier = nn.Sequential(
                nn.Linear(in_features, 512),
                nn.Hardswish(inplace=True),
                nn.Dropout(p=dropout, inplace=True),
                nn.Linear(512, num_classes)
            )
        else: # small / mobilenet_v3_small
            weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
            self.backbone = mobilenet_v3_small(weights=weights)
            in_features = self.backbone.classifier[0].in_features
            self.backbone.classifier = nn.Sequential(
                nn.Linear(in_features, 256),
                nn.Hardswish(inplace=True),
                nn.Dropout(p=dropout, inplace=True),
                nn.Linear(256, num_classes)
            )

    def freeze_backbone(self):
        """Freezes backbone feature layers for stage 1 classifier training."""
        for param in self.backbone.features.parameters():
            param.requires_grad = False

    def unfreeze_backbone(self, unfreeze_last_n_blocks: int = None):
        """
        Unfreezes backbone features for end-to-end fine-tuning.
        If unfreeze_last_n_blocks is specified, only unfreezes the top N blocks.
        """
        if unfreeze_last_n_blocks is None:
            for param in self.backbone.features.parameters():
                param.requires_grad = True
        else:
            total_blocks = len(self.backbone.features)
            for i, child in enumerate(self.backbone.features):
                requires = (i >= total_blocks - unfreeze_last_n_blocks)
                for param in child.parameters():
                    param.requires_grad = requires

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)


def get_model(
    num_classes: int = 38,
    model_variant: str = "efficientnet_b0",
    pretrained: bool = True,
    dropout: float = 0.3,
) -> LeafDiseaseClassifier:
    """Factory helper to instantiate LeafDiseaseClassifier."""
    return LeafDiseaseClassifier(
        num_classes=num_classes,
        model_variant=model_variant,
        pretrained=pretrained,
        dropout=dropout,
    )
