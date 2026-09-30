import torch
import torch.nn as nn
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights, mobilenet_v3_large, MobileNet_V3_Large_Weights

class LeafDiseaseClassifier(nn.Module):
    """
    Fine-tunable Transfer Learning Architecture for Plant Leaf Disease Classification.
    Uses MobileNetV3-Small or MobileNetV3-Large as backbone for high-accuracy, ultra-fast,
    sub-10MB offline client-side edge and browser inference.
    """
    def __init__(self, num_classes=29, model_variant="small", pretrained=True, dropout=0.3):
        super(LeafDiseaseClassifier, self).__init__()
        
        self.num_classes = num_classes
        self.model_variant = model_variant
        
        if model_variant == "large":
            weights = MobileNet_V3_Large_Weights.DEFAULT if pretrained else None
            self.backbone = mobilenet_v3_large(weights=weights)
            first_layer = self.backbone.classifier[0]
            assert isinstance(first_layer, nn.Linear)
            in_features = first_layer.in_features
            
            # Custom high-performance classifier head
            self.backbone.classifier = nn.Sequential(
                nn.Linear(in_features, 512),
                nn.Hardswish(inplace=True),
                nn.Dropout(p=dropout, inplace=True),
                nn.Linear(512, num_classes)
            )
        else:
            weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
            self.backbone = mobilenet_v3_small(weights=weights)
            first_layer = self.backbone.classifier[0]
            assert isinstance(first_layer, nn.Linear)
            in_features = first_layer.in_features
            
            # Custom lightweight classifier head
            self.backbone.classifier = nn.Sequential(
                nn.Linear(in_features, 256),
                nn.Hardswish(inplace=True),
                nn.Dropout(p=dropout, inplace=True),
                nn.Linear(256, num_classes)
            )

    def freeze_backbone(self):
        """Freezes backbone weights for initial feature extraction training phase."""
        for param in self.backbone.features.parameters():
            param.requires_grad = False

    def unfreeze_backbone(self, unfreeze_last_n_layers=None):
        """Unfreezes backbone features for end-to-end fine-tuning."""
        if unfreeze_last_n_layers is None:
            for param in self.backbone.features.parameters():
                param.requires_grad = True
        else:
            # Unfreeze only the last N feature blocks
            total_blocks = len(self.backbone.features)
            for i, child in enumerate(self.backbone.features):
                if i >= total_blocks - unfreeze_last_n_layers:
                    for param in child.parameters():
                        param.requires_grad = True
                else:
                    for param in child.parameters():
                        param.requires_grad = False

    def forward(self, x):
        return self.backbone(x)

def get_model(num_classes=29, model_variant="small", pretrained=True):
    return LeafDiseaseClassifier(num_classes=num_classes, model_variant=model_variant, pretrained=pretrained)
