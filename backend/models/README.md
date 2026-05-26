# Model Files

Model weights are intentionally not committed to the public repository.

Place trained model files here when running the backend locally, for example:

- `best.onnx`
- `best.pt`

The default backend configuration reads:

```env
YOLO_MODEL_PATH=./models/best.onnx
YOLO_PT_MODEL_PATH=./models/best.pt
```

If no model is available, the backend falls back to its rule-based detection path.
