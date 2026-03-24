import torch
from src.config.settings import BASE_DIR
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor


class MyModel:
    def __init__(self, threshold: float = 0.6, dpi: int = 120):
        self.threshold = threshold
        self.dpi = dpi

        model_path = BASE_DIR / "models" / "docling-project--docling-layout-heron"

        self.device_name = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(self.device_name)

        self.processor = RTDetrImageProcessor.from_pretrained(model_path)
        self.model = RTDetrV2ForObjectDetection.from_pretrained(model_path)
        self.model = self.model.to(self.device)  # type: ignore
        self.model.eval()

    def predict(self, image):
        inputs = self.processor(images=[image], return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
        results = self.processor.post_process_object_detection(
            outputs,
            target_sizes=[(image.size[1], image.size[0])],
            threshold=self.threshold,
        )
        return results

_model = None

def get_model(threshold: float = 0.6, dpi: int = 120):
    global _model
    if _model is None:
        _model = MyModel(threshold=threshold, dpi=dpi)
    return _model
