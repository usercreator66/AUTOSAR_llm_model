# `autosar_cfg_gui.py`

[Open source](../autosar_cfg_gui.py)

## Purpose

Runs the local browser-based AUTOSAR configuration and code-generation interface. The GUI collects a requirement, platform/version settings, expected output contracts, and optional uploaded context before requesting generation.

## Main flow

`main()` starts the local HTTP server. `Handler` serves the interface and handles requests. The `generate()` function selects C, header, or ARXML prompt rules, adds matching AUTOSAR specification evidence, invokes `LLMClient`, and cleans or validates the generated artifact. File extraction helpers support plain text, archives, and common office document formats.

## Run

Start the GUI without the model preloader using `python autosar_cfg_gui.py`. For the launcher workflow that initializes model settings and manages model loading, use `python launch.py`.

## Dependencies and notes

Uses Python's local HTTP server and standard parsing libraries, plus `llm_client` and `autosar_spec_engine` when generation is requested. C/header output is cleaned as source text; ARXML output is parsed to ensure it is well-formed XML.