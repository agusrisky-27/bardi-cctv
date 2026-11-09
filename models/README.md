# Models Directory

This directory stores deep learning model weights used by the RCIS pipeline.

## Pretrained Weights
- By default, RCIS uses YOLO pretrained weights (e.g., `yolo11n.pt` or `yolo11s.pt`).
- Ultralytics automatically downloads pretrained weights on the first run if they are not already present locally.
- In accordance with our security and repository hygiene guidelines, large weight binaries (`*.pt`, `*.onnx`, `*.engine`) are excluded from Git via `.gitignore`.

## Local Storage
- Place custom fine-tuned weights or exported CoreML/ONNX models in this folder.
- Ensure model files are backed up to secure local storage or internal model registries, never committed directly to public repositories.

## Files used by the pipeline
- `yolo11n.pt` / `yolo11s.pt`: person detector (choose in `configs/detection.yaml`).
- `gender_classifier.pt`: YOLO11n-cls trained in `colab/train_gender_classifier.ipynb` on PA-100K (classes `female`, `male`, imgsz 96). Optional: without it, gender shows "Tidak diketahui".
- `yolo11s.mlpackage`: the same `yolo11s.pt` converted to Apple CoreML (960 px, FP16) so it runs on the Neural Engine. **This is the one in use.** GPU use drops from ~92% to ~16%, CPU rises from ~25% to ~53% of one core, detections are the same (sample video, 2026-11-09).
  - Back to the GPU: delete `yolo11s.mlpackage`. The pipeline then loads `yolo11s.pt` automatically (or set `model_path` to it).
  - Re-export (only after changing `detection.input_size` or the model). The project's torch is too new for coremltools, so use a throwaway venv:
    ```bash
    python3.12 -m venv /tmp/cml && /tmp/cml/bin/pip install "torch==2.7.0" "torchvision==0.22.0" "coremltools==9.0" "ultralytics==8.4.203" "numpy<2"
    cd models && YOLO_AUTOINSTALL=False /tmp/cml/bin/python -c "from ultralytics import YOLO; YOLO('yolo11s.pt').export(format='coreml', imgsz=960, half=True)"
    ```
