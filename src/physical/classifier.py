import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms
import timm 

DATA_DIR = "data"
SAVE_PATH = "efficient-net.pth"
NUM_CLASSES = 8
TARGET_CLASS = ["DEF1", "DEF2"]       # Only used for inference

EPOCHS = 8
BATCH_SIZE = 64
LEARNING_RATE = 5e-4
VAL_SPLIT = 0.2

# Enable training on Apple Silicon / GPU. CPU as a fallback
DEVICE = torch.device("cpu")
if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")

# --------------------------------------------------------
# Transforms
# --------------------------------------------------------

# Added a bit of augmentations
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

# --------------------------------------------------------------
# Dataset
# --------------------------------------------------------------

def build_dataloaders(data_dir: str):
    full_dataset = datasets.ImageFolder(data_dir, transform=train_transform)

    print(f"Found {len(full_dataset)} images across {len(full_dataset.classes)} classes:")
    for idx, name in enumerate(full_dataset.classes):
        count = sum(1 for _, label in full_dataset.samples if label == idx)
        marker = " ← TARGET" if idx == TARGET_CLASS else ""
        print(f"  [{idx}] {name}: {count} images{marker}")

    val_size = int(len(full_dataset) * VAL_SPLIT)
    train_size = len(full_dataset) - val_size
    train_set, val_set = random_split(full_dataset, [train_size, val_size])

    # Val set uses val_transform (no augmentation)
    val_set.dataset = datasets.ImageFolder(data_dir, transform=val_transform)

    train_loader = DataLoader(
        train_set, batch_size=BATCH_SIZE, shuffle=True, pin_memory=False,
    )
    val_loader = DataLoader(
        val_set, batch_size=BATCH_SIZE, shuffle=False, pin_memory=False,
    )
    return train_loader, val_loader, full_dataset.classes

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def build_model(num_classes: int) -> nn.Module:
    model = timm.create_model(
        "efficientnet_b0",
        pretrained=True,       # pulls imagenet weights from HuggingFace
        num_classes=num_classes,
    )
    return model.to(DEVICE)

def train_one_epoch(model, loader, optimizer, criterion):
    model.train()
    total_loss, correct, total = 0.0, 0, 0

    for images, labels in loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * images.size(0)
        correct += (outputs.argmax(dim=1) == labels).sum().item()
        total += images.size(0)

    return total_loss / total, correct / total


@torch.no_grad()
def evaluate(model, loader, criterion):
    model.eval()
    total_loss, correct, total = 0.0, 0, 0

    for images, labels in loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        outputs = model(images)
        loss = criterion(outputs, labels)

        total_loss += loss.item() * images.size(0)
        correct += (outputs.argmax(dim=1) == labels).sum().item()
        total += images.size(0)

    return total_loss / total, correct / total

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Using device: {DEVICE}\n")

    train_loader, val_loader, class_names = build_dataloaders(DATA_DIR)
    model = build_model(NUM_CLASSES)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val_acc = 0.0

    print(f"\nTraining for {EPOCHS} epochs ...\n")
    for epoch in range(1, EPOCHS + 1):
        t0 = time.perf_counter()

        train_loss, train_acc = train_one_epoch(model, train_loader, optimizer, criterion)
        val_loss, val_acc = evaluate(model, val_loader, criterion)
        scheduler.step()

        elapsed = time.perf_counter() - t0
        print(
            f"Epoch {epoch:>3}/{EPOCHS} | "
            f"train loss {train_loss:.4f} acc {train_acc:.2%} | "
            f"val loss {val_loss:.4f} acc {val_acc:.2%} | "
            f"{elapsed:.1f}s"
        )

        # Save best checkpoint
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), SAVE_PATH)
            print(f"  ✓ Saved best model (val acc {val_acc:.2%})")

    print(f"\nDone. Best val accuracy: {best_val_acc:.2%}")
    print(f"Weights saved to '{SAVE_PATH}'")


if __name__ == "__main__":
    main()