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

### 4. Extract Structured AUTOSAR SWC Specifications

Transform natural language automotive requirements into structured AUTOSAR specifications:

```powershell
# Default requirement (Vehicle speed monitor)
python generate_spec.py

# Custom requirement
python generate_spec.py "Create an ECU component that monitors battery voltage and triggers a shutdown flag if voltage drops below 9V for more than 500ms"
```

Example structured output:
```text
SWC: SpeedMonitor_SWC

Input:
  VehicleSpeed

Output:
  SpeedExceededWarning

Runnable:
  re_MonitorVehicleSpeed

Logic:
  if VehicleSpeed > 100
      SpeedExceededWarning = TRUE
  else
      SpeedExceededWarning = FALSE
```
