import os
import sys
from types import SimpleNamespace

from local_engine import (
    _format_transformers_messages,
    _get_model_input_device,
    _load_transformers_model,
    _normalize_no_split_modules,
    _resolve_adapter_path,
    _truncate_messages_for_context,
    _truncate_prompt_for_context,
    resolve_model_path,
    release_local_model,
)


def test_truncate_prompt_for_context_preserves_headroom():
    text = "word " * 6000
    result = _truncate_prompt_for_context(text, context_size=8192, max_new_tokens=256)
    assert len(result) < len(text)
    assert "..." in result


def test_truncate_prompt_for_context_keeps_short_prompt():
    text = "short prompt"
    result = _truncate_prompt_for_context(text, context_size=8192, max_new_tokens=256)
    assert result == text


def test_truncate_messages_for_context_keeps_system_prompt_and_trims_user():
    system_prompt = "You are a helpful AUTOSAR engineer. " * 200
    user_prompt = "word " * 6000
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    result = _truncate_messages_for_context(messages, context_size=8192, max_new_tokens=256)

    assert result[0]["content"] == system_prompt
    assert len(result[1]["content"]) < len(user_prompt)
    assert "..." in result[1]["content"]


def test_resolve_model_path_accepts_transformers_checkpoint(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")

    assert resolve_model_path(str(tmp_path)) == str(tmp_path.resolve())


def test_resolve_adapter_path_accepts_peft_directory(tmp_path):
    (tmp_path / "adapter_config.json").write_text("{}", encoding="utf-8")

    assert _resolve_adapter_path(str(tmp_path)) == str(tmp_path.resolve())


def test_normalize_no_split_modules_flattens_nested_sets():
    class Model:
        _no_split_modules = [{"DecoderLayer", "VisionBlock"}, "DecoderLayer"]

    model = Model()
    _normalize_no_split_modules(model)

    assert set(model._no_split_modules) == {"DecoderLayer", "VisionBlock"}


def test_format_transformers_messages_wraps_plain_text_content():
    message = {"role": "user", "content": "Hello"}

    result = _format_transformers_messages([message])

    assert result == [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]
    assert message["content"] == "Hello"


def test_model_input_device_uses_execution_device_for_meta_embedding():
    import torch

    class Embeddings:
        weight = SimpleNamespace(device=torch.device("meta"))
        _hf_hook = SimpleNamespace(execution_device=torch.device("cuda:1"))

    class Model:
        def get_input_embeddings(self):
            return Embeddings()

    assert _get_model_input_device(Model()) == torch.device("cuda:1")


def test_peft_loading_receives_temporary_offload_directory(tmp_path, monkeypatch):
    adapter_path = tmp_path / "adapter"
    adapter_path.mkdir()
    (adapter_path / "adapter_config.json").write_text("{}", encoding="utf-8")
    loaded = {}

    class Model:
        _no_split_modules = [{"DecoderLayer", "VisionBlock"}]

        def eval(self):
            return self

    class FakePeftModel:
        @staticmethod
        def from_pretrained(model, path, **kwargs):
            loaded["no_split_modules"] = model._no_split_modules
            loaded["offload_dir"] = kwargs["offload_dir"]
            return model

    class FakeAutoModel:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            loaded["model_kwargs"] = kwargs
            return Model()

    class FakeBitsAndBytesConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeProcessor:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            return object()

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(
        bfloat16="bfloat16",
        cuda=SimpleNamespace(
            is_available=lambda: True,
            get_device_properties=lambda _: SimpleNamespace(total_memory=16 * 1024**3),
            set_per_process_memory_fraction=lambda *args, **kwargs: None,
            memory_allocated=lambda _: 0,
        ),
    ))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoModelForImageTextToText=FakeAutoModel,
        AutoProcessor=FakeProcessor,
        BitsAndBytesConfig=FakeBitsAndBytesConfig,
    ))
    monkeypatch.setitem(sys.modules, "peft", SimpleNamespace(PeftModel=FakePeftModel))

    try:
        _load_transformers_model("model", str(adapter_path))

        assert set(loaded["no_split_modules"]) == {"DecoderLayer", "VisionBlock"}
        assert os.path.isdir(loaded["offload_dir"])
        assert loaded["model_kwargs"]["device_map"] == {"": 0}
        quantization = loaded["model_kwargs"]["quantization_config"]
        assert quantization.load_in_4bit is True
        assert quantization.bnb_4bit_quant_type == "nf4"
    finally:
        release_local_model()
