"""
Image Classification Inference using EfficientNet

Provides real-time classification of camera frames for production verification
"""

import torch
import torch.nn as nn
import timm
from torchvision import transforms
from PIL import Image
import numpy as np
from typing import Tuple, Optional


class ProductClassifier:
    """
    EfficientNet-based classifier for product verification

    Loads trained weights and provides inference on camera frames
    """

    def __init__(self, model_path: str = "efficient-net.pth", num_classes: int = 6):
        """
        Initialize classifier

        Args:
            model_path: Path to trained model weights
            num_classes: Number of output classes
        """
        self.model_path = model_path
        self.num_classes = num_classes

        # Device selection
        self.device = torch.device("cpu")
        if torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")

        print(f"🔮 Classifier using device: {self.device}")

        # Build model
        self.model = self._build_model()

        # Load weights
        self._load_weights()

        # Inference transform (no augmentation)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225]),
        ])

        # Class names (should match training data folder structure)
        # Customize this based on your actual classes
        self.class_names = [
            "AGR-400",
            "Defective",
            "IOT-200",
            "MED-300",
            "PCB-IND-100",
            "PCB-PWR-500"
        ]

        print(f"✓ Classifier loaded with {self.num_classes} classes")
        print(f"  Classes: {', '.join(self.class_names)}")

    def _build_model(self) -> nn.Module:
        """Build EfficientNet model architecture"""
        model = timm.create_model(
            "efficientnet_b0",
            pretrained=False,  # We'll load our trained weights
            num_classes=self.num_classes,
        )
        return model.to(self.device)

    def _load_weights(self):
        """Load trained model weights"""
        try:
            state_dict = torch.load(self.model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.eval()  # Set to evaluation mode
            print(f"✓ Loaded weights from: {self.model_path}")
        except Exception as e:
            print(f"✗ Failed to load model weights: {e}")
            raise

    @torch.no_grad()
    def classify_frame(self, frame: np.ndarray) -> Tuple[str, float, dict]:
        """
        Classify a single camera frame

        Args:
            frame: OpenCV frame (BGR numpy array)

        Returns:
            Tuple of:
            - predicted_class: Class name (str)
            - confidence: Confidence score 0-1 (float)
            - all_probs: Dictionary of {class_name: probability}
        """
        # Convert BGR (OpenCV) to RGB (PIL)
        frame_rgb = frame[:, :, ::-1]

        # Convert to PIL Image
        pil_image = Image.fromarray(frame_rgb)

        # Apply transforms
        input_tensor = self.transform(pil_image).unsqueeze(0)  # Add batch dimension
        input_tensor = input_tensor.to(self.device)

        # Forward pass
        outputs = self.model(input_tensor)

        # Get probabilities using softmax
        probs = torch.nn.functional.softmax(outputs, dim=1)[0]

        # Get predicted class
        predicted_idx = probs.argmax().item()
        predicted_class = self.class_names[predicted_idx]
        confidence = probs[predicted_idx].item()

        # Get all class probabilities
        all_probs = {
            self.class_names[i]: probs[i].item()
            for i in range(self.num_classes)
        }

        return predicted_class, confidence, all_probs

    def format_prediction(self, predicted_class: str, confidence: float,
                         all_probs: dict, top_k: int = 3) -> str:
        """
        Format classification results as human-readable string

        Args:
            predicted_class: Predicted class name
            confidence: Confidence score 0-1
            all_probs: Dictionary of all class probabilities
            top_k: Number of top predictions to include

        Returns:
            Formatted string
        """
        lines = []
        lines.append(f"🔍 *Classification Result*")
        lines.append("")
        lines.append(f"*Predicted:* {predicted_class}")
        lines.append(f"*Confidence:* {confidence:.1%}")
        lines.append("")

        # Sort by probability
        sorted_probs = sorted(all_probs.items(), key=lambda x: x[1], reverse=True)

        lines.append(f"*Top {top_k} Predictions:*")
        for i, (class_name, prob) in enumerate(sorted_probs[:top_k], 1):
            marker = "✓" if class_name == predicted_class else " "
            lines.append(f"{marker} {i}. {class_name}: {prob:.1%}")

        return "\n".join(lines)

    def verify_product(self, frame: np.ndarray, expected_product: str,
                      threshold: float = 0.7) -> Tuple[bool, str, float]:
        """
        Verify if frame matches expected product

        Args:
            frame: OpenCV frame
            expected_product: Expected product class name
            threshold: Confidence threshold for verification

        Returns:
            Tuple of:
            - is_match: True if predicted class matches expected and confidence > threshold
            - predicted_class: Predicted class name
            - confidence: Confidence score
        """
        predicted_class, confidence, _ = self.classify_frame(frame)

        # Check if prediction matches expected
        is_match = (predicted_class == expected_product) and (confidence >= threshold)

        return is_match, predicted_class, confidence
