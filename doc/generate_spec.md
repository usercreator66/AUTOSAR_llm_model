# `generate_spec.py`

[Open source](../generator/generate_spec.py)

## Purpose

Generates a component source package from a requirement and component suffix. It selects the strongest available component evidence, in priority order: RS+SWS together, SWS, RS, TPS/TR, then EXP reference-only. Retrieved passages come from `autosar_spec/.autosar_spec_index.sqlite3` and are limited to the selected source files in `input_<platform>_spec.txt`. EXP is explanatory, not normative. An optional project folder supplies existing C/C++ headers/source and ARXML as prompt context. Adaptive prompts preserve `ara::com` for communication and `ara::diag` for diagnostics when relevant, while using concrete APIs from the supplied project or retrieved evidence.

## Main API

- `generate_component_package(...)` performs EXP analysis, retrieves the highest-priority available component evidence from SQLite, then writes related source files under `output/<component>/`.
- Classic packages contain `<component>_app.c`, `<component>_app.h`, `<component>_cfg.c`, and `<component>_cfg.h`.
- Adaptive packages contain `<component>.cpp` and `<component>.hpp`.
- Every generated source includes comments citing the affected AUTOSAR documents.
- `generate_autosar_code(...)` remains the single-file generation API; the CLI selects it with `--single-file`.
- `generate_source_to_file(...)` requests bounded output chunks, appends them to a `.partial` file, and promotes the file only after the completion marker and source validation succeed. Incomplete output is preserved as `.partial` instead of replacing the final file.
- `select_component_spec_files(...)` matches the requested component (with or without a `.pdf` suffix) against `_EXP_`, `_RS_`, `_SWS_`, `_TPS_`, and `_TR_` filenames, then applies the evidence priority order. If a platform list is absent, it scans that platform's spec folder.
- `load_project_context(project_path, requirement, ...)` reads a bounded, relevance-ranked set of project source files. It skips `.venv`, build, and common dependency folders, as well as the generated `aradiag_adaptive.cpp` sample so that output cannot bias later generation.
- `infer_component_name(requirement)` recognizes explicit component/module/SWC names and common CamelCase identifiers.
- `_resolve_output_path(...)` applies the component prefix while preserving the requested directory and extension.
- `extract_source_code(response, language)` selects source from a fenced response or plain source text.
- `generate_swc_spec(...)` remains a Python helper for text-only SWC specifications; the CLI calls `generate_autosar_code()`.

## Run

```powershell
python generate_spec.py --platform classic --component CanIf "Implement the CanIf component..."
python generate_spec.py --platform adaptive --component CommunicationManagement --project-path path/to/component "Implement service discovery..."
```

The package parent defaults to `output/` and can be changed with `--output-dir`. `--project-dir` aliases `--project-path`. For package generation, `--output` is not used; pass `--single-file` to use `--output` and the legacy single-file workflow. When EXP is the only available tier, the prompt marks it reference-only and requires assumptions or placeholders rather than treating it as a normative requirement.

Long generated files are continued in chunks of up to 4,096 tokens per model call, with a bounded source tail supplied to each continuation. The writer allows up to 100 chunks and does not treat a size-limited response as a complete file.

Run the continuation tests with:

```powershell
python -m unittest generator.test_generate_spec -v
```