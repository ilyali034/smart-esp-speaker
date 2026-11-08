import numpy as np


def parse_models(models):
    """Split a comma-separated model specification into model names or ONNX paths."""
    if isinstance(models, str):
        models = models.split(",")
    parsed = [model.strip() for model in models if model.strip()]
    if not parsed:
        raise ValueError("at least one wake-word model is required")
    return parsed


class WakeWord:
    def __init__(self, model="hey_jarvis", threshold=0.5):
        from openwakeword.model import Model
        self.threshold = threshold
        self.models = parse_models(model)
        self.model = Model(wakeword_models=self.models, inference_framework="onnx")

    def detect(self, frame: np.ndarray) -> float:
        scores = self.model.predict(frame)
        return max(scores.values()) if scores else 0.0

    def reset(self):
        if hasattr(self.model, "reset"):
            self.model.reset()
