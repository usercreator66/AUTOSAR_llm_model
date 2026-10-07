# `local_engine.py`

[Open source](../local_engine.py)

## Purpose

Owns local model loading and inference, including caching model state, streaming generated text, context budgeting, adapter handling, and cleanup of GPU/CPU/offload resources.

## Main API

- `resolve_model_path(...)` accepts supported local model locations.
- `load_local_model(...)` loads and caches a model for repeated inference.
- `generate_local_response(...)` applies prompt/generation safeguards and produces the response, optionally streaming tokens.
- `release_local_model()` releases cached model/processor state and temporary offload files.
- Internal helpers truncate prompts/messages and prepare Transformers inputs for the model context.

## Runtime notes

The module controls process-wide model caches and uses locks around loading and generation. Inference needs the installed model backend and the configured local model files; CUDA availability affects device placement and memory use.