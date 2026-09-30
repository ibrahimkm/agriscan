import torch
from PIL import Image
from torchvision import transforms
from ml.model import get_model

c = torch.load(
    "ml/checkpoints/best_leaf_model.pth",
    map_location="cpu"
)

classes = c["classes"]

model = get_model(
    num_classes=len(classes),
    model_variant=c.get("model_variant", "small"),
    pretrained=False
)

model.load_state_dict(c["model_state_dict"])
model.eval()

img = Image.open("leaf.JPG").convert("RGB")

normalize = transforms.Normalize(
    [0.485, 0.456, 0.406],
    [0.229, 0.224, 0.225]
)

tests = {
    "Original": transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        normalize
    ]),

    "Horizontal Flip": transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=1.0),
        transforms.ToTensor(),
        normalize
    ]),

    "Slight Crop": transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.CenterCrop((224, 224)),
        transforms.ToTensor(),
        normalize
    ]),

    "Slightly Bright": transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ColorJitter(brightness=0.15),
        transforms.ToTensor(),
        normalize
    ]),
}

print()
print("========================================")
print("       MODEL STABILITY TEST")
print("========================================")

for name, transform in tests.items():

    x = transform(img).unsqueeze(0)

    with torch.no_grad():
        probabilities = torch.softmax(model(x), dim=1)[0]

    top = torch.topk(probabilities, 3)

    print()
    print(name)
    print("----------------------------------------")

    for rank, (idx, value) in enumerate(
        zip(top.indices, top.values), 1
    ):
        print(
            f"{rank}. {classes[idx.item()]} "
            f"-> {value.item() * 100:.2f}%"
        )

print()
print("========================================")
