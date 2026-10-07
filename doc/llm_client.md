# `llm_client.py`

[Open source](../llm_client.py)

## Purpose

Provides the stable application-facing interface to local model inference.

## Main API

- `LLMClient` resolves the model path and optional adapter path at construction.
- `LLMClient.query(...)` applies generation limits and delegates to `local_engine.generate_local_response()`.
- `query_llm(...)` forwards common prompt arguments through the shared default client for command-line generators.

## Configuration

`LOCAL_MODEL_PATH` selects the model; `LOCAL_ADAPTER_PATH` selects a LoRA adapter. Without an adapter setting, the base model is used. The client also constrains generation token/output size and supports optional streaming callbacks through the class API.