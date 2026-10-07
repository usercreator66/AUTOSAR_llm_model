# `launch.py`

[Open source](../launch.py)

## Purpose

Coordinates model configuration and startup of the browser-based AUTOSAR GUI.

## Main flow

`initialize_environment()` resolves the local model and optional adapter paths and sets environment variables. `load_gpu_for_generation()` loads the selected model. `run_gui()` starts `autosar_cfg_gui.main()`. `shutdown_generation()` releases cached model resources when called by generation lifecycle code. `main()` changes to the project root and runs the launcher sequence.

## Run

```powershell
python launch.py
```

The default model path is `models/Qwen3.5-9B`; `LOCAL_MODEL_PATH` and `LOCAL_ADAPTER_PATH` can override model and adapter selection.