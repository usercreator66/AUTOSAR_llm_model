# `main.py`

[Open source](../main.py)

## Purpose

Verifies that the local model can be loaded and answer a short prompt. It is a diagnostic entry point, not the AUTOSAR GUI launcher or code generator.

## Main flow

`main()` loads environment configuration, creates an `LLMClient`, reports the resolved model path and CUDA/CPU status, then makes a small inference request. Import/configuration and inference failures are printed and exit with a nonzero status.

## Run

```powershell
python main.py
```