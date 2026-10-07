# Python Documentation Index

This index links each repository-maintained Python file to its individual documentation page. The `.venv` directory and installed third-party Python files are intentionally excluded.

## Application and Runtime

| Source file | Documentation | Summary |
| --- | --- | --- |
| [autosar_cfg_gui.py](../autosar_cfg_gui.py) | [autosar_cfg_gui.md](autosar_cfg_gui.md) | Local browser UI for AUTOSAR code/configuration generation |
| [autosar_spec_engine.py](../autosar_spec_engine.py) | [autosar_spec_engine.md](autosar_spec_engine.md) | PDF indexing, SQLite FTS5 search, and cited context |
| [generate_c.py](../generate_c.py) | [generate_c.md](generate_c.md) | Standalone requirement-to-C generator |
| [generate_spec.py](../generate_spec.py) | [generate_spec.md](generate_spec.md) | Retrieval-backed Classic C / Adaptive C++ generation |
| [launch.py](../launch.py) | [launch.md](launch.md) | Environment setup and GUI launcher |
| [llm_client.py](../llm_client.py) | [llm_client.md](llm_client.md) | Application-facing local model client |
| [local_engine.py](../local_engine.py) | [local_engine.md](local_engine.md) | Local model loading, inference, streaming, and cleanup |
| [main.py](../main.py) | [main.md](main.md) | Local model verification entry point |
| [_verify_extract.py](../_verify_extract.py) | [_verify_extract.md](_verify_extract.md) | Empty placeholder |

## Dataset and Training Utilities

| Source file | Documentation | Summary |
| --- | --- | --- |
| [build_ar_r2511_dataset.py](../training_script/build_ar_r2511_dataset.py) | [training_build_ar_r2511_dataset.md](training_build_ar_r2511_dataset.md) | Builds ECUC and specification-evidence examples |
| [prepare_c_dataset.py](../training_script/prepare_c_dataset.py) | [training_prepare_c_dataset.md](training_prepare_c_dataset.md) | Packages a source folder into one Alpaca JSON record |
| [merge_all_loras.py](../training_script/merge_all_loras.py) | [training_merge_all_loras.md](training_merge_all_loras.md) | Merges saved AUTOSAR LoRA adapters |

## Tests

| Source file | Documentation | Summary |
| --- | --- | --- |
| [test_adapter_link.py](../tests/test_adapter_link.py) | [test_adapter_link.md](test_adapter_link.md) | Model and adapter selection defaults |
| [test_autosar_generation.py](../tests/test_autosar_generation.py) | [test_autosar_generation.md](test_autosar_generation.md) | Retrieved prompts and platform-specific source output |
| [test_autosar_spec_engine.py](../tests/test_autosar_spec_engine.py) | [test_autosar_spec_engine.md](test_autosar_spec_engine.md) | PDF indexing, search, and citations |
| [test_context_guard.py](../tests/test_context_guard.py) | [test_context_guard.md](test_context_guard.md) | Prompt budgeting and model-loading safeguards |

## Generated Output

| Source file | Documentation | Summary |
| --- | --- | --- |
| [generated_code_generatortab.py](../output/generated_code_generatortab.py) | [generated_code_generatortab.md](generated_code_generatortab.md) | Standalone Tkinter template artifact; currently invalid Python |

Run the pytest suite with `python -m pytest tests` when pytest is installed. See [python-files.md](python-files.md) for a grouped project overview and common commands.