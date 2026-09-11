ARG TEI_IMAGE=ghcr.io/huggingface/text-embeddings-inference:cpu-1.8.1
FROM ${TEI_IMAGE}

# Runtime arguments are supplied by compose so the same image can serve
# FP32, optimized, or validated INT8 ONNX artifacts.
EXPOSE 80
