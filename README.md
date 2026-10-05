# AUTOSAR_LLM

A local, private AI-assisted engineering toolkit designed to integrate Large Language Models with automotive software engineering workflows based on the **AUTOSAR** (Automotive Open System ARchitecture) standard.

`AUTOSAR_LLM` runs **100% locally and offline** using the **Qwen** model loaded directly into GPU VRAM (NVIDIA CUDA acceleration).

---

## Project Structure

```
AUTOSAR_LLM/
├── models/
│   └── qwen2.5_7B_coder/  # Q4_K_M GGUF model
├── .env                # Local model path configuration
├── .gitignore          # Git ignore rules
├── requirements.txt    # Project dependencies
├── local_engine.py     # In-process GPU VRAM model loader & streamer
├── llm_client.py       # Local LLM client
├── main.py             # Model verification script
├── generate_c.py       # C code generator
├── generate_spec.py    # Requirement to AUTOSAR SWC specification extractor
└── README.md           # Documentation
```

The launcher uses `qwen2.5-coder-7b-instruct-q4_k_m.gguf` from that directory.
The GGUF backend is `llama-cpp-python`; set `LOCAL_GPU_LAYERS=-1` (the default)
to offload all available model layers to the GPU. On Windows, GPU acceleration
requires a CUDA-enabled llama-cpp-python build and the CUDA Toolkit. For example,
with the CUDA Toolkit and CMake installed:

```powershell
$env:CMAKE_ARGS = "-DGGML_CUDA=on"
$env:FORCE_CMAKE = "1"
python -m pip install --force-reinstall --no-cache-dir llama-cpp-python
```

---

## Getting Started

### 1. Activate Virtual Environment in VS Code

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### 2. Verify Local Model in VRAM

Test loading the local model into GPU memory:

```powershell
python main.py
```

---

### 3. Generate Safe Automotive C Code

Generate production-quality C code with safety checks and explanations:

```powershell
# Default requirement (Safe uint8_t addition with saturation)
python generate_c.py

# Custom requirement
python generate_c.py "Create a safe MISRA-C circular buffer queue for CAN message frames"
```

---

### 4. Generate Platform-Specific AUTOSAR Source

Generate C for AUTOSAR Classic or C++ for AUTOSAR Adaptive. Retrieved specification passages are filtered to the selected platform and included in the model prompt:

```powershell
# Classic Platform C (default)
python generate_spec.py

# Adaptive Platform C++
python generate_spec.py --platform adaptive "Implement a service that monitors battery voltage"
```

Generated filenames use the AUTOSAR component as a prefix, for example `output/CanIf_classic.c` or `output/AdaptiveService_adaptive.cpp`. Component names are inferred from CamelCase names in the requirement; set `--component` when the name is ambiguous. Custom `--output` paths also receive the component prefix if it is missing. The default requirement names its component `VehicleSpeedMonitor`.

The earlier text-only SWC specification helper remains available to Python callers as `generate_swc_spec()`.

```powershell
python generate_spec.py --platform classic --component SpeedMonitor --output output/SpeedMonitor.c "Implement a speed monitor SWC: input VehicleSpeed, output SpeedExceededWarning, set the output when speed exceeds 100 km/h"
```

    ## AUTOSAR Specification Retrieval

    Generation uses retrieval-augmented inference, not model fine-tuning. Before a
    generation request, the engine searches extracted specification passages and
    adds the best matches to the model prompt. The GUI C/header/ARXML generator,
    the standalone C generator, and the SWC specification generator all use this
    context.

    The local SQLite FTS5 index is stored at
    `autosar_spec/.autosar_spec_index.sqlite3`. It is built from PDFs under
    `autosar_spec/classic_autosar_R25_11` and
    `autosar_spec/adaptive_autosar_R25_11`; new or changed PDFs are indexed
    incrementally. To search the index manually or force a full reindex:

    ```powershell
    python autosar_spec_engine.py "CanIf controller" --platform classic
    python autosar_spec_engine.py "CanIf controller" --reindex
    ```

    Retrieved passages include source and page details. If no relevant passage is
    found, the prompt directs the model not to invent normative AUTOSAR requirements.
