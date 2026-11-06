# Models Directory

This directory stores deep learning model weights used by the RCIS pipeline.

## Pretrained Weights
- By default, RCIS uses YOLO pretrained weights (e.g., `yolo11n.pt` or `yolo11s.pt`).
- Ultralytics automatically downloads pretrained weights on the first run if they are not already present locally.
- In accordance with our security and repository hygiene guidelines, large weight binaries (`*.pt`, `*.onnx`, `*.engine`) are excluded from Git via `.gitignore`.

## Local Storage
- Place custom fine-tuned weights or exported CoreML/ONNX models in this folder.
- Ensure model files are backed up to secure local storage or internal model registries, never committed directly to public repositories.
