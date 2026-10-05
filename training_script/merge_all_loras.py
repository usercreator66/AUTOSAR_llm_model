"""Merge all saved AUTOSAR LoRA adapters into one final adapter directory."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_MODEL_PATH = ROOT / "models" / "Qwen3.5-9B"
LORA_ROOT = ROOT / "saves" / "Qwen3.5-9B-Thinking" / "lora"
MERGED_OUTPUT = LORA_ROOT / "merged_autosar_lora"


def discover_adapters() -> list[Path]:
    if not LORA_ROOT.exists():
        raise FileNotFoundError(f"LoRA directory not found: {LORA_ROOT}")

    adapters = [
        path
        for path in sorted(LORA_ROOT.iterdir())
        if path.is_dir() and (path / "adapter_config.json").exists()
    ]
    adapters = [path for path in adapters if path.name != MERGED_OUTPUT.name]
    if not adapters:
        raise FileNotFoundError(f"No trained LoRA adapters found under: {LORA_ROOT}")
    return adapters


def merge_all_loras(base_model_path: Path = BASE_MODEL_PATH, output_dir: Path = MERGED_OUTPUT) -> Path:
    """Merge all discovered adapters into a single final adapter folder."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig

    adapter_dirs = discover_adapters()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Base model: {base_model_path}")
    print(f"[*] Merging {len(adapter_dirs)} adapters into: {output_dir}")

    quantization_config = None
    if torch.cuda.is_available():
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    model = AutoModelForCausalLM.from_pretrained(
        str(base_model_path),
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        device_map="auto",
        quantization_config=quantization_config,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    )

    current_model = model
    for index, adapter_dir in enumerate(adapter_dirs, 1):
        print(f"[*] [{index}/{len(adapter_dirs)}] Merging {adapter_dir.name}")
        peft_model = PeftModel.from_pretrained(
            current_model,
            str(adapter_dir),
            is_trainable=False,
        )
        current_model = peft_model.merge_and_unload()

    current_model.save_pretrained(str(output_dir), safe_serialization=True)

    first_adapter_config = next(
        (adapter_dir / "adapter_config.json" for adapter_dir in adapter_dirs if (adapter_dir / "adapter_config.json").exists()),
        None,
    )
    if first_adapter_config is not None:
        shutil.copy2(first_adapter_config, output_dir / "adapter_config.json")

    print(f"[*] Final merged adapter saved to: {output_dir}")
    return output_dir


if __name__ == "__main__":
    merge_all_loras()
