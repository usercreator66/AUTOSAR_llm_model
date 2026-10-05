"""
local_engine.py - Direct In-Process Local LLM Runner (GPU / VRAM Prioritized)

Loads and runs Qwen directly in GPU VRAM with live streaming output to the terminal.
"""

import gc
import os
import shutil
import tempfile
from threading import Event, Lock, Thread
from typing import Callable, Optional

_MODEL_CACHE = None
_PROCESSOR_CACHE = None
_LOADED_MODEL_PATH = None
_OFFLOAD_DIR = None
_MODEL_LOAD_LOCK = Lock()
_GENERATION_LOCK = Lock()
_MAX_CHUNK_TOKENS = 8192
_MAX_GPU_MEMORY_GIB = 14
MAX_OUTPUT_BYTES = 32768


def _estimate_token_count(text: str) -> int:
    """Conservative token estimate for prompt budgeting on Windows local models."""
    if not text:
        return 0
    byte_length = len(text.encode("utf-8"))
    word_count = len(text.split())
    return max(1, max(word_count * 3, byte_length // 2))


def _truncate_prompt_for_context(
    prompt: str,
    context_size: int = 8192,
    max_new_tokens: int = 256,
    safety_margin: int = 64,
) -> str:
    """Trim oversized prompts so the full request stays under the model context."""
    if not prompt:
        return prompt

    context_size = max(int(context_size), 2048)
    max_new_tokens = max(int(max_new_tokens), 1)
    available_tokens = max(context_size - max_new_tokens - max(safety_margin, 256), 128)
    estimated_tokens = _estimate_token_count(prompt)
    if estimated_tokens <= available_tokens:
        return prompt

    ratio = available_tokens / max(estimated_tokens, 1)
    budget_chars = max(int(len(prompt) * ratio), 1)
    truncated = prompt[:budget_chars].rstrip()
    if len(truncated) < len(prompt):
        truncated = truncated.rstrip() + " ..."
    return truncated


def _truncate_messages_for_context(
    messages: list[dict],
    context_size: int = 8192,
    max_new_tokens: int = 256,
    safety_margin: int = 64,
) -> list[dict]:
    """Keep system instructions and trim the user payload to fit within the model context."""
    if not messages:
        return messages

    context_size = max(int(context_size), 2048)
    max_new_tokens = max(int(max_new_tokens), 1)
    available_tokens = max(context_size - max_new_tokens - max(safety_margin, 256), 128)

    total_tokens = sum(
        _estimate_token_count(str(message.get("content", "")))
        for message in messages
        if message.get("content")
    )
    if total_tokens <= available_tokens:
        return messages

    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if message.get("role") != "user":
            continue
        content = str(message.get("content") or "")
        if not content:
            continue

        system_tokens = sum(
            _estimate_token_count(str(other.get("content", "")))
            for other in messages
            if other.get("role") == "system" and other.get("content")
        )
        remaining_for_user = max(available_tokens - system_tokens, 128)
        if _estimate_token_count(content) <= remaining_for_user:
            return messages

        safe_content = _truncate_prompt_for_context(
            content,
            context_size=max(remaining_for_user + max_new_tokens + safety_margin, 2048),
            max_new_tokens=max_new_tokens,
            safety_margin=safety_margin,
        )
        message["content"] = safe_content
        return messages

    return messages


def _cleanup_offload_dir() -> None:
    global _OFFLOAD_DIR
    if _OFFLOAD_DIR:
        shutil.rmtree(_OFFLOAD_DIR, ignore_errors=True)
        _OFFLOAD_DIR = None


def release_local_model() -> None:
    """Release the cached Transformers model to free GPU/RAM memory."""
    global _MODEL_CACHE, _PROCESSOR_CACHE, _LOADED_MODEL_PATH
    if _MODEL_CACHE is None and _OFFLOAD_DIR is None:
        return
    if _MODEL_CACHE is not None:
        print("[*] Releasing cached model from GPU/RAM.")
    close = getattr(_MODEL_CACHE, "close", None)
    if callable(close):
        close()
    _MODEL_CACHE = None
    _PROCESSOR_CACHE = None
    _LOADED_MODEL_PATH = None
    gc.collect()
    _cleanup_offload_dir()


def _resolve_model_file(model_path: str) -> str:
    if not os.path.isabs(model_path):
        model_path = os.path.join(os.path.dirname(__file__), model_path)
    resolved_path = os.path.realpath(os.path.abspath(model_path))

    if os.path.isdir(resolved_path) and os.path.isfile(os.path.join(resolved_path, "config.json")):
        return resolved_path

    # Support case-insensitive and underscore/hyphen variations (e.g. qwen3.5_9B vs Qwen3.5-9B)
    parent_dir = os.path.dirname(resolved_path)
    target_name = os.path.basename(resolved_path).lower().replace("_", "-")
    if os.path.isdir(parent_dir):
        for entry in os.listdir(parent_dir):
            candidate_path = os.path.join(parent_dir, entry)
            if os.path.isdir(candidate_path) and entry.lower().replace("_", "-") == target_name:
                if os.path.isfile(os.path.join(candidate_path, "config.json")):
                    return os.path.realpath(candidate_path)

    if os.path.isdir(resolved_path):
        raise FileNotFoundError(
            f"No config.json found in model directory: '{resolved_path}'"
        )
    raise FileNotFoundError(f"Local model path not found: '{resolved_path}'")


def _resolve_adapter_path(adapter_path: Optional[str]) -> Optional[str]:
    if not adapter_path:
        return None
    if not os.path.isabs(adapter_path):
        adapter_path = os.path.join(os.path.dirname(__file__), adapter_path)
    resolved_path = os.path.realpath(os.path.abspath(adapter_path))
    if os.path.isdir(resolved_path):
        if not os.path.isfile(os.path.join(resolved_path, "adapter_config.json")):
            raise ValueError(f"PEFT adapter config not found in: '{resolved_path}'")
        return resolved_path
    raise FileNotFoundError(f"LoRA adapter directory not found: '{resolved_path}'")


def _normalize_no_split_modules(model) -> None:
    module_names = getattr(model, "_no_split_modules", None)
    if module_names is None:
        return

    def flatten(values):
        if isinstance(values, str):
            return [values]
        flattened = []
        for value in values:
            if isinstance(value, (list, tuple, set, frozenset)):
                flattened.extend(flatten(value))
            else:
                flattened.append(value)
        return flattened

    model._no_split_modules = list(dict.fromkeys(flatten(module_names)))


def _format_transformers_messages(messages: list[dict]) -> list[dict]:
    formatted = []
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        formatted.append({**message, "content": content})
    return formatted


def _get_model_input_device(model):
    import torch

    embeddings = model.get_input_embeddings()
    hook = getattr(embeddings, "_hf_hook", None)
    execution_device = getattr(hook, "execution_device", None)
    if execution_device is not None:
        device = torch.device(execution_device)
        if device.type != "meta":
            return device

    device = embeddings.weight.device
    if device.type != "meta":
        return device

    device_map = getattr(model, "hf_device_map", {})
    for mapped_device in device_map.values():
        if mapped_device in {"disk", "meta"}:
            continue
        if isinstance(mapped_device, int):
            mapped_device = f"cuda:{mapped_device}"
        return torch.device(mapped_device)
    return torch.device("cuda:0")


def _load_transformers_model(model_path: str, adapter_path: Optional[str]):
    global _OFFLOAD_DIR
    try:
        import torch
        from transformers import (
            AutoModelForImageTextToText,
            AutoProcessor,
            BitsAndBytesConfig,
        )
    except ImportError as exc:
        raise ImportError(
            "Qwen3.5 requires a recent Transformers install with Qwen3.5 support."
        ) from exc

    if not torch.cuda.is_available():
        raise RuntimeError("Qwen3.5 GPU inference requires a CUDA-enabled PyTorch build.")
    if adapter_path and not os.path.isdir(adapter_path):
        raise ValueError("Qwen3.5 requires a Hugging Face PEFT adapter directory.")

    total_vram_bytes = torch.cuda.get_device_properties(0).total_memory
    memory_fraction = min(
        (_MAX_GPU_MEMORY_GIB * 1024**3) / total_vram_bytes,
        0.9,
    )
    torch.cuda.set_per_process_memory_fraction(memory_fraction, device=0)

    processor = AutoProcessor.from_pretrained(model_path)
    model = AutoModelForImageTextToText.from_pretrained(
        model_path,
        dtype=torch.bfloat16,
        device_map={"": 0},
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        ),
        low_cpu_mem_usage=True,
    )
    print(
        "[*] 4-bit NF4 model loaded on CUDA; "
        f"allocated {torch.cuda.memory_allocated(0) / (1024**3):.2f} GiB."
    )
    if adapter_path:
        _normalize_no_split_modules(model)
        try:
            from peft import PeftModel
        except ImportError as exc:
            raise ImportError("Install peft to load the selected LoRA adapter.") from exc
        _OFFLOAD_DIR = tempfile.mkdtemp(prefix="autosar-agent-offload-")
        try:
            model = PeftModel.from_pretrained(
                model,
                adapter_path,
                is_trainable=False,
                offload_dir=_OFFLOAD_DIR,
            )
        except Exception:
            _cleanup_offload_dir()
            raise
    model.eval()
    return model, processor


def _stream_transformers_response(
    model,
    processor,
    messages: list[dict],
    max_new_tokens: int,
    temperature: float,
    repetition_penalty: float,
    stop_event: Optional[Event],
    enable_thinking: bool = False,
):
    from transformers import StoppingCriteria, StoppingCriteriaList, TextIteratorStreamer

    class StopOnEvent(StoppingCriteria):
        def __call__(self, input_ids, scores, **kwargs):
            return bool(
                (stop_event and stop_event.is_set()) or cancel_event.is_set()
            )

    if stop_event and stop_event.is_set():
        return

    chat_template_kwargs = {
        "tokenize": True,
        "add_generation_prompt": True,
        "return_dict": True,
        "return_tensors": "pt",
    }
    try:
        inputs = processor.apply_chat_template(
            _format_transformers_messages(messages),
            enable_thinking=enable_thinking,
            **chat_template_kwargs,
        )
    except TypeError:
        inputs = processor.apply_chat_template(
            _format_transformers_messages(messages),
            **chat_template_kwargs,
        )

    inputs = inputs.to(_get_model_input_device(model))
    tokenizer = getattr(processor, "tokenizer", processor)
    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )
    cancel_event = Event()
    generation_errors = []

    # Ensure all EOS tokens are registered so generation stops properly
    eos_token_ids = []
    default_eos = getattr(tokenizer, "eos_token_id", None)
    if default_eos is not None:
        if isinstance(default_eos, (list, tuple, set)):
            eos_token_ids.extend(default_eos)
        else:
            eos_token_ids.append(default_eos)
    for special_name in ("<|im_end|>", "<|endoftext|>"):
        token_id = tokenizer.convert_tokens_to_ids(special_name)
        if isinstance(token_id, int) and token_id > 0 and token_id not in eos_token_ids:
            eos_token_ids.append(token_id)

    pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else (eos_token_ids[0] if eos_token_ids else None)

    def generate() -> None:
        try:
            generation_kwargs = {
                **inputs,
                "streamer": streamer,
                "max_new_tokens": max_new_tokens,
                "do_sample": temperature > 0,
                "repetition_penalty": repetition_penalty,
                "pad_token_id": pad_token_id,
                "eos_token_id": eos_token_ids or None,
                "stopping_criteria": StoppingCriteriaList([StopOnEvent()]),
            }
            if temperature > 0:
                generation_kwargs["temperature"] = temperature
            model.generate(**generation_kwargs)
        except Exception as exc:
            generation_errors.append(exc)
            streamer.end()

    generation_thread = Thread(target=generate, daemon=True)
    generation_thread.start()
    try:
        for text in streamer:
            if text and not (stop_event and stop_event.is_set()):
                yield text
    finally:
        if generation_thread.is_alive():
            cancel_event.set()
            generation_thread.join()
    if generation_errors:
        raise RuntimeError(f"Qwen3.5 generation failed: {generation_errors[0]}") from generation_errors[0]


def resolve_model_path(
    model_path: str, fallback_path: Optional[str] = None
) -> str:
    try:
        return _resolve_model_file(model_path)
    except (FileNotFoundError, ValueError):
        if fallback_path is None:
            raise
        print(
            f"[WARNING] Model path '{model_path}' not found; "
            f"using fallback '{fallback_path}'."
        )
        return _resolve_model_file(fallback_path)


def load_local_model(
    model_path: str = "./models/Qwen3.5-9B",
    adapter_path: Optional[str] = None,
):
    """Load and cache a local Qwen Transformers model."""
    global _MODEL_CACHE, _PROCESSOR_CACHE, _LOADED_MODEL_PATH
    resolved_path = _resolve_model_file(model_path)
    resolved_adapter = _resolve_adapter_path(adapter_path)
    cache_key = (resolved_path, resolved_adapter)

    with _MODEL_LOAD_LOCK:
        if _MODEL_CACHE is not None and _LOADED_MODEL_PATH == cache_key:
            print("[*] Reusing model already loaded in memory.")
            return _MODEL_CACHE, _PROCESSOR_CACHE

        if _MODEL_CACHE is not None:
            print("[*] Releasing previous model before loading new selection.")
            close = getattr(_MODEL_CACHE, "close", None)
            if callable(close):
                close()
            _MODEL_CACHE = None
            _PROCESSOR_CACHE = None
            gc.collect()
            _cleanup_offload_dir()

        print(f"[*] Loading Transformers model: {resolved_path}")
        if resolved_adapter:
            print(f"[*] Applying PEFT LoRA adapter: {resolved_adapter}")
        model, processor = _load_transformers_model(resolved_path, resolved_adapter)

        _MODEL_CACHE = model
        _PROCESSOR_CACHE = processor
        _LOADED_MODEL_PATH = cache_key
        print("[*] Model ready! Starting generation...\n")
        return _MODEL_CACHE, _PROCESSOR_CACHE


def generate_local_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    model_path: str = "./models/Qwen3.5-9B",
    adapter_path: Optional[str] = None,
    max_new_tokens: int = 256,
    temperature: float = 0.1,
    stop_event: Optional[Event] = None,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
    repetition_penalty: float = 1.12,
    stream_callback: Optional[Callable[[str], None]] = None,
    enable_thinking: bool = False,
) -> str:
    """Generate and stream a response from the local model."""
    output_byte_limit = max(int(max_output_bytes), 1)
    with _GENERATION_LOCK:
        model, processor = load_local_model(model_path, adapter_path=adapter_path)
        chunk_limit = min(max(int(max_new_tokens), 1), _MAX_CHUNK_TOKENS)
        print("[*] Generating response (streaming live tokens):\n")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        context_size = max(int(os.environ.get("LOCAL_CONTEXT_SIZE", str(_MAX_CHUNK_TOKENS))), 2048)
        original_messages = [dict(message) for message in messages]
        safe_messages = _truncate_messages_for_context(
            messages,
            context_size=context_size,
            max_new_tokens=chunk_limit,
        )
        if safe_messages != original_messages:
            print(
                f"[*] Prompt exceeded the local context window ({context_size} tokens); "
                f"truncating to keep generation valid."
            )
        messages = safe_messages

        if stop_event:
            print("[*] Abort is available from the GUI.")
        stream = _stream_transformers_response(
            model,
            processor,
            messages,
            chunk_limit,
            max(float(temperature), 0.0),
            max(float(repetition_penalty), 1.0),
            stop_event,
            enable_thinking=enable_thinking,
        )
        response_parts = []
        output_bytes = 0
        try:
            for text in stream:
                if stop_event and stop_event.is_set():
                    break
                if not text:
                    continue
                remaining_bytes = output_byte_limit - output_bytes
                encoded = text.encode("utf-8")
                if len(encoded) > remaining_bytes:
                    text = encoded[:remaining_bytes].decode("utf-8", errors="ignore")
                if text:
                    response_parts.append(text)
                    output_bytes += len(text.encode("utf-8"))
                    print(text, end="", flush=True)
                    if stream_callback:
                        stream_callback(text)
                if output_bytes >= output_byte_limit:
                    print(f"\n[*] Output limited to {output_byte_limit} bytes.")
                    break
        finally:
            close = getattr(stream, "close", None)
            if callable(close):
                close()
        print()
        return "".join(response_parts).strip()
