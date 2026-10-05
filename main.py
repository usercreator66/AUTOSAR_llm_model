"""
AUTOSAR_LLM - Entry Point & Local Model Verification

Tests loading and execution of the local Qwen model in GPU VRAM.
"""

import sys
import os
import torch
from dotenv import load_dotenv
from llm_client import LLMClient

load_dotenv()


def main():
    print("=" * 60)
    print("AUTOSAR_LLM - Local Qwen Model Verification")
    print("=" * 60)

    client = LLMClient()
    print(f"[1/3] Local Model Path: {client.model_path}")

    # Check PyTorch & CUDA GPU
    try:
        import transformers

        device = "CUDA GPU" if torch.cuda.is_available() else "CPU"
        print(f"[2/3] PyTorch & Transformers active (Compute Device: {device}).")
    except ImportError:
        print("\n[ERROR] Required packages 'torch' or 'transformers' are not installed.")
        print("Please run: pip install torch transformers accelerate")
        sys.exit(1)

    test_prompt = (
        "You are an assistant for the AUTOSAR_LLM project. "
        "Please confirm connectivity by responding with: "
        "'AUTOSAR_LLM local Qwen model loaded!' followed by a 1-sentence "
        "description of what AUTOSAR is."
    )

    print("[3/3] Generating test response using local Qwen model in VRAM...\n")
    try:
        response_text = client.query(prompt=test_prompt, max_tokens=512, enable_thinking=False)
        print("\n" + "=" * 60)
        print("Final Response:")
        print("=" * 60)
        print(response_text)
        print("=" * 60)
        print("\n[SUCCESS] Local Qwen model is fully verified and ready!")
    except Exception as exc:
        print(f"\n[ERROR] Local model generation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
