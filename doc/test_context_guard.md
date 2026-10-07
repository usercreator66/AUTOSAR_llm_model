# `tests/test_context_guard.py`

[Open source](../tests/test_context_guard.py)

Checks safeguards and helper behavior in `local_engine.py`: prompt/message truncation preserves system instructions and generation headroom, model and adapter paths resolve correctly, Transformers messages and module lists are normalized, and input-device/offload setup handles mocked models.

Some cases replace Torch, Transformers, and PEFT with test doubles. Run with `python -m pytest tests/test_context_guard.py` when pytest is installed.