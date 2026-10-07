# `generate_c.py`

[Open source](../generate_c.py)

## Purpose

Standalone natural-language-to-C generator. It retrieves relevant AUTOSAR specification context, sends the requirement and evidence to the local model, extracts C code, and writes a `.c` output file.

## Main API

- `generate_c_code(requirement, output_file, max_tokens)` performs retrieval, inference, code cleanup, and file output.
- `extract_and_clean_c_code(raw_text)` removes model reasoning/Markdown wrappers and keeps recognizable C source.
- `main()` exposes the command-line interface.

## Run

```powershell
python generate_c.py "Create a safe CAN frame queue"
python generate_c.py --help
```

This generic C entry point is separate from `generate_spec.py`, which chooses C or C++ based on the AUTOSAR platform.