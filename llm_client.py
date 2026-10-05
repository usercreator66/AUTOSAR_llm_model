"""
llm_client.py - Local LLM Client for AUTOSAR_LLM

Pure local inference engine powered by Qwen running directly on GPU VRAM.
"""

import os
from threading import Event
from typing import Callable, Optional
from dotenv import load_dotenv
from local_engine import generate_local_response, resolve_model_path

load_dotenv()

MAX_GENERATION_TOKENS = 8192
MAX_OUTPUT_BYTES = 32367
DEFAULT_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "models", "Qwen3.5-9B")
)


class LLMClient:
    """Client for local Qwen model execution."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        adapter_path: Optional[str] = None,
    ):
        configured_model_path = model_path or os.environ.get("LOCAL_MODEL_PATH")
        self.model_path = (
            resolve_model_path(configured_model_path, DEFAULT_MODEL_PATH)
            if configured_model_path and model_path is None
            else configured_model_path or DEFAULT_MODEL_PATH
        )
        self.adapter_path = (
            adapter_path
            if adapter_path is not None
            else os.environ.get("LOCAL_ADAPTER_PATH") or None
        )

    def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 65536,
        temperature: float = 0.2,
        stop_event: Optional[Event] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        enable_thinking: bool = False,
    ) -> str:
        """Runs generation directly on the local Qwen model in GPU VRAM."""
        generation_kwargs = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "model_path": self.model_path,
            "adapter_path": self.adapter_path,
            "max_new_tokens": min(max(int(max_tokens), 1), MAX_GENERATION_TOKENS),
            "temperature": temperature,
            "stop_event": stop_event,
            "stream_callback": stream_callback,
            "max_output_bytes": MAX_OUTPUT_BYTES,
            "repetition_penalty": 1.12,
            "enable_thinking": enable_thinking,
        }
        return generate_local_response(**generation_kwargs)


# Global default client
default_client = LLMClient()


def query_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 8192,
    temperature: float = 0.2,
    enable_thinking: bool = False,
) -> str:
    """Convenience helper to query the local Qwen model."""
    return default_client.query(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        enable_thinking=enable_thinking,
    )
