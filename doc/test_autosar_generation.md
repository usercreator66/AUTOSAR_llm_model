# `tests/test_autosar_generation.py`

[Open source](../tests/test_autosar_generation.py)

Checks the generator integration without loading the real model or PDF database. Mocks retrieval and inference to verify that evidence reaches prompts, Classic uses C and Classic evidence, Adaptive uses C++ and Adaptive evidence, extracted code is saved under a component-prefixed filename, unsupported platforms are rejected, and the other generation routes still include retrieval context.

The tests use `unittest.TestCase` and mocks and can be run with `python -m unittest tests.test_autosar_generation -v` or pytest.