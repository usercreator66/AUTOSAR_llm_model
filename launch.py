"""Launch the local AUTOSAR model environment and start the GUI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = str(ROOT)


def _resolve_model_path() -> str:
    from local_engine import resolve_model_path

    env_path = os.environ.get("LOCAL_MODEL_PATH")
    if env_path:
        default_path = ROOT / "models" / "Qwen3.5-9B"
        return resolve_model_path(env_path, str(default_path))
    default_path = ROOT / "models" / "Qwen3.5-9B"
    return str(default_path)


def _resolve_adapter_path() -> str | None:
    if "LOCAL_ADAPTER_PATH" in os.environ:
        return os.environ["LOCAL_ADAPTER_PATH"] or None
    return None


def initialize_environment() -> tuple[str, str | None]:
    """Initialize model settings before the launcher preloads the model."""
    model_path = _resolve_model_path()
    adapter_path = _resolve_adapter_path()

    os.environ["LOCAL_MODEL_PATH"] = model_path
    if adapter_path:
        os.environ["LOCAL_ADAPTER_PATH"] = adapter_path
    else:
        os.environ.pop("LOCAL_ADAPTER_PATH", None)

    print(f"[*] Model path: {model_path}")
    if adapter_path:
        print(f"[*] Adapter path: {adapter_path}")
    else:
        print("[*] No adapter selected; generation will use the base model only.")

    # Keep the GPU free until generation actually starts.
    print("[*] Environment initialized. GPU will be loaded only when generation begins.")
    return model_path, adapter_path


def load_gpu_for_generation() -> None:
    """Load the local model into GPU VRAM immediately before generation starts."""
    from local_engine import load_local_model
    model_path = _resolve_model_path()
    adapter_path = _resolve_adapter_path()
    print("[*] Loading model into GPU VRAM for generation...")
    load_local_model(model_path=model_path, adapter_path=adapter_path)


def shutdown_generation() -> None:
    """Release the GPU model after generation is complete or cancelled."""
    try:
        from local_engine import release_local_model
        release_local_model()
    except Exception:
        pass


def run_gui() -> None:
    """Start the local browser-based AUTOSAR configuration GUI."""
    print("[*] Starting AUTOSAR configuration GUI...")
    import autosar_cfg_gui

    autosar_cfg_gui.main()


def main() -> None:
    os.chdir(PROJECT_ROOT)
    sys.path.insert(0, PROJECT_ROOT)
    initialize_environment()
    load_gpu_for_generation()
    run_gui()


if __name__ == "__main__":
    main()
