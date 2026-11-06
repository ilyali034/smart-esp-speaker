import numpy as np


class WakeWord:
    def __init__(self, model="hey_jarvis", threshold=0.5):
        from openwakeword.model import Model
        self.threshold = threshold
        self.model = Model(wakeword_models=[model], inference_framework="onnx")

    def detect(self, frame: np.ndarray) -> float:
        scores = self.model.predict(frame)
        return max(scores.values()) if scores else 0.0

    def reset(self):
        if hasattr(self.model, "reset"):
            self.model.reset()
