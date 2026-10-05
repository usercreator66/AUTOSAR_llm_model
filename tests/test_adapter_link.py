import os

from llm_client import LLMClient
from autosar_cfg_gui import _choices


def test_no_adapter_is_default_without_environment_override(monkeypatch):
    monkeypatch.delenv("LOCAL_ADAPTER_PATH", raising=False)
    client = LLMClient()
    assert client.adapter_path is None


def test_environment_can_select_adapter(monkeypatch):
    client = LLMClient()
    monkeypatch.setenv("LOCAL_ADAPTER_PATH", "custom-adapter")
    assert LLMClient().adapter_path == "custom-adapter"


def test_gui_defaults_to_no_lora_and_lists_qwen35_adapter():
    models, adapters = _choices()
    model_names = {label for label, _ in models}
    adapter_paths = {os.path.normcase(path) for _, path in adapters}

    assert "Qwen3.5 9B (Transformers)" in model_names
    assert adapters[0] == ("No LoRA adapter", "")
    assert any("train_2026-09-30-17-48-45" in path for path in adapter_paths)
