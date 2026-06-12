# tflite-runtime compatibility stub

This local package exists only to satisfy `openwakeword`'s Linux dependency on
`tflite-runtime` when no upstream wheel is available for the target Python
version. `openwakeword` already falls back to `onnxruntime` when importing
`tflite_runtime` fails, so this stub keeps `pip install -r requirements.txt`
working without changing runtime behavior.
