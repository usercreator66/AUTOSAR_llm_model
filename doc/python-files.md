# Python File Guide

This guide covers the 17 Python files maintained in this repository. It excludes `.venv` and other installed third-party packages. Files are grouped by purpose; the entry for every repository `.py` file appears below.

For an index with one detailed page per file, see [index.md](index.md).

## Application and Runtime

### [`autosar_cfg_gui.py`](../autosar_cfg_gui.py)
Implements the local browser-based AUTOSAR configuration and code-generation UI. It handles uploaded context files, prompt construction, generation requests, and C/header/ARXML output cleanup. It can be started directly with `python autosar_cfg_gui.py`, or through `launch.py`.

### [`autosar_spec_engine.py`](../autosar_spec_engine.py)
Indexes local AUTOSAR PDF specifications into the SQLite FTS5 database under `autosar_spec/.autosar_spec_index.sqlite3`, then retrieves ranked passages with document and page citations. `AutosarSpecEngine.index_documents()` updates changed or missing PDFs; `search()` and `build_context()` provide evidence for generation prompts.

Search the index from the command line:

```powershell
python autosar_spec_engine.py "CanIf controller" --platform classic
python autosar_spec_engine.py "CanIf controller" --reindex
```

### [`generate_c.py`](../generate_c.py)
Standalone requirement-to-C generator. It retrieves relevant AUTOSAR context, sends the prompt through `llm_client.query_llm()`, extracts and cleans C source, and writes the requested output file. Run `python generate_c.py --help` for options.

### [`generate_spec.py`](../generate_spec.py)
Platform-specific AUTOSAR source generator. It retrieves evidence filtered to Classic or Adaptive, asks the model for a complete implementation, extracts the source block, and writes a component-prefixed `.c` file for Classic or `.cpp` file for Adaptive. Component names can be inferred from CamelCase identifiers or supplied with `--component`.

```powershell
python generate_spec.py --platform classic --component CanIf "Implement the CanIf component..."
python generate_spec.py --platform adaptive --component AdaptiveService "Implement the service..."
```

The Python helper `generate_swc_spec()` remains available when a text-only SWC specification is needed; the CLI generates source code.

### [`launch.py`](../launch.py)
Initializes model and adapter environment settings, loads the model for generation, and starts the browser GUI. Use `python launch.py` for the combined launcher workflow. It also exposes helpers for model loading and releasing GPU resources.

### [`llm_client.py`](../llm_client.py)
Provides the `LLMClient` interface used by application code. It resolves model and optional adapter paths, sets generation parameters, and delegates inference to `local_engine.generate_local_response()`. `query_llm()` is the convenience wrapper used by the standalone generators.

### [`local_engine.py`](../local_engine.py)
Owns local model inference and lifecycle: model loading/caching, adapter resolution, prompt/context length management, token streaming, output limits, and model release. The GUI launcher and `LLMClient` use this module rather than loading model weights independently.

### [`main.py`](../main.py)
Small model verification entry point. It checks the local PyTorch/Transformers setup and sends a short prompt through `LLMClient`. Run `python main.py` to verify inference configuration.

### [`_verify_extract.py`](../_verify_extract.py)
Currently an empty placeholder. It defines no functions or executable behavior.

## Dataset and Training Utilities

### [`training_script/build_ar_r2511_dataset.py`](../training_script/build_ar_r2511_dataset.py)
Builds source-grounded Alpaca-style examples from AUTOSAR Classic Platform R25-11 ECUC ARXML definitions and, by default, related specification PDFs. It records parameters, constraints, references, containers, hierarchy, and PDF evidence. The default output is `data/AR_R2511_train.json`; `--no-pdfs` skips PDF extraction. Run `python training_script/build_ar_r2511_dataset.py --help` for source and output overrides.

### [`training_script/prepare_c_dataset.py`](../training_script/prepare_c_dataset.py)
Packages files from a directory into a single LLaMA-Factory Alpaca-style JSON record. The record includes each file's relative path and text in its input, with an empty output field; it does not create input/output training pairs by itself.

```powershell
python training_script/prepare_c_dataset.py --input path/to/source --output-file data/custom_dataset.json
```

### [`training_script/merge_all_loras.py`](../training_script/merge_all_loras.py)
Finds saved LoRA adapters under the configured `saves/Qwen3.5-9B-Thinking/lora` directory and merges them successively onto the configured base model. It writes `merged_autosar_lora` under that directory. **Caution:** an existing output directory is deleted before the merge begins. Review the paths and back up any needed output before running `python training_script/merge_all_loras.py`.

## Tests

Tests use pytest-style functions and fixtures; `test_autosar_generation.py` also uses `unittest.TestCase`. Run the suite with `python -m pytest tests` when pytest is installed.

### [`tests/test_adapter_link.py`](../tests/test_adapter_link.py)
Checks that adapter selection defaults to disabled, that `LOCAL_ADAPTER_PATH` is honored, and that the GUI model/adapter choices include the expected Qwen configuration.

### [`tests/test_autosar_generation.py`](../tests/test_autosar_generation.py)
Checks that retrieved context reaches generation prompts, that Classic and Adaptive requests use platform-specific retrieval, and that C/C++ source is extracted and written to the correct component-prefixed filename.

### [`tests/test_autosar_spec_engine.py`](../tests/test_autosar_spec_engine.py)
Uses a fake PDF reader and temporary directories to check indexing, full-text search, platform filtering, release/page citations, context formatting, and unchanged-file handling without depending on the production PDF collection.

### [`tests/test_context_guard.py`](../tests/test_context_guard.py)
Checks prompt/context truncation, model and adapter path resolution, Transformers message formatting, device selection, module normalization, and temporary offload setup using test doubles.

## Generated Output Artifact

### [`output/generated_code_generatortab.py`](../output/generated_code_generatortab.py)
A standalone Tkinter code-generator template that is not part of the AUTOSAR GUI or model inference workflow. It currently contains an invalid f-string and does not parse as valid Python; treat it as an archived generated artifact rather than an executable entry point.
