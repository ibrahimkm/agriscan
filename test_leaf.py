import torch
from PIL import Image
from torchvision import transforms
from ml.model import get_model

# Load checkpoint
c = torch.load(
    "ml/checkpoints/best_leaf_model.pth",
    map_location="cpu"
)

classes = c["classes"]

# Recreate the trained model
model = get_model(
    num_classes=len(classes),
    model_variant=c.get("model_variant", "small"),
    pretrained=False
)

model.load_state_dict(c["model_state_dict"])
model.eval()

# Same preprocessing used by the model
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225]
    )
])

# Load your real-world image
img = Image.open("leaf.JPG").convert("RGB")
x = transform(img).unsqueeze(0)

# Run inference
with torch.no_grad():
    logits = model(x)
    probabilities = torch.softmax(logits, dim=1)[0]

# Get top 5
top = torch.topk(probabilities, 5)

print()
print("========================================")
print("       REAL LEAF MODEL INFERENCE")
print("========================================")
print()
print("Image: leaf.JPG")
print("Model: best_leaf_model.pth")
print("Classes:", len(classes))
print()

print("TOP PREDICTION")
print("----------------------------------------")
print("Disease:", classes[top.indices[0].item()])
print("Confidence:", f"{top.values[0].item() * 100:.2f}%")
print()

print("TOP 5 PREDICTIONS")
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
