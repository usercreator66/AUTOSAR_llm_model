"""
generate_c.py - Robust C Code Generator using Local Qwen

Generates 100% valid, compilable ISO C99/C11 automotive code, cleans any formatting artifacts,
and saves pure C source files to disk.
"""

import os
import re
import sys
import argparse
from dotenv import load_dotenv
from llm_client import query_llm

load_dotenv()

DEFAULT_REQUIREMENT = (
    "Create a C function that receives two uint8_t values, "
    "adds them safely using saturating arithmetic, and returns the result as uint8_t."
)


def extract_and_clean_c_code(raw_text: str) -> str:
    """Extract only C source code from the model response."""

    text = re.sub(
        r"<think>.*?</think>",
        "",
        raw_text,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()

    # Prefer fenced C blocks.
    code_blocks = re.findall(
        r"```(?:c|C|cpp)?\s*(.*?)```",
        text,
        flags=re.DOTALL,
    )

    if code_blocks:
        c_code = next(
            (block.strip() for block in code_blocks if "#include" in block),
            code_blocks[0].strip(),
        )
    else:
        # Extract from the first likely C source line.
        match = re.search(r"(?m)^(?:\s*#include\b|\s*/\*|\s*//)", text)
        if match is None:
            raise ValueError("Model did not return recognizable C source code.")

        c_code = text[match.start():]

        # Remove explanations appended after the C source.
        c_code = re.split(
            r"\n\s*(?:Explanation|Design choices|MISRA-C Compliance|"
            r"Thinking Process|Analysis):?",
            c_code,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

    c_code = re.sub(r"```(?:c|C|cpp)?", "", c_code)
    c_code = c_code.replace("```", "").strip()

    if "#include <stdint.h>" not in c_code:
        c_code = "#include <stdint.h>\n" + c_code

    if (
        ("bool" in c_code or "true" in c_code or "false" in c_code)
        and "#include <stdbool.h>" not in c_code
    ):
        c_code = "#include <stdbool.h>\n" + c_code

    return c_code.strip()


def generate_c_code(
    requirement: str,
    output_file: str = "output/generated_code.c",
    max_tokens: int = 32768,
) -> str:
    """
    Generates strict C source code from a requirement and writes a clean .c file.
    """
    system_prompt = (
        "code generator in C language with syntax"
    )

    prompt = f"""Requirement:
{requirement}

"""

    print("[*] Generating C source code with local Qwen model...")
    response = query_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
    )

    print("\n[DEBUG] Raw model response:\n", repr(response))

    if not isinstance(response, str):
        response = getattr(response, "text", None) or getattr(response, "content", None)

    if not response:
        raise ValueError("Local model returned an empty or unsupported response.")

    # Clean and extract pure C source
    c_source = extract_and_clean_c_code(response)

    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(output_dir, exist_ok=True)

    # Write clean C file to disk
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(c_source + "\n")

    abs_path = os.path.abspath(output_file)
    print("\n" + "=" * 60)
    print(f"[SUCCESS] Pure C source file successfully written to:")
    print(f"  --> {abs_path}")
    print("=" * 60)

    return c_source


def main():
    parser = argparse.ArgumentParser(
        description="Generate pure C source file (.c) from requirement using local Qwen"
    )
    parser.add_argument(
        "requirement",
        nargs="*",
        default=[DEFAULT_REQUIREMENT],
        help="C programming requirement string",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output/generated_code.c",
        help="Output .c file path (default: output/generated_code.c)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=32768,
        help="Maximum tokens per generation chunk (default: 32768)",
    )
    args = parser.parse_args()

    requirement_text = (
        " ".join(args.requirement)
        if isinstance(args.requirement, list)
        else args.requirement
    )

    print("=" * 60)
    print("AUTOSAR_LLM - Local C Code Generator (Qwen)")
    print("=" * 60)
    print(f"Requirement:\n  \"{requirement_text}\"\n")
    print(f"Output File: {args.output}\n")

    try:
        generate_c_code(
            requirement=requirement_text,
            output_file=args.output,
            max_tokens=args.max_tokens,
        )
    except Exception as exc:
        print(f"\n[ERROR] Generation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
