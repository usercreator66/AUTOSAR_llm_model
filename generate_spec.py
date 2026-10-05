"""
generate_spec.py - Natural Language to Structured AUTOSAR SWC Specification

Extracts structured AUTOSAR Software Component (SWC) specifications
and saves them as a specification file on disk.
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from llm_client import query_llm

load_dotenv()

DEFAULT_REQUIREMENT = (
    "Create a component that monitors vehicle speed "
    "and sets an output when speed exceeds 100 km/h."
)


def generate_swc_spec(
    requirement: str,
    output_file: str = "output/swc_spec.txt",
    max_tokens: int = 512,
) -> str:
    """
    Extracts structured SWC specification and saves it to a file.
    """
    system_prompt = "You are an AUTOSAR systems engineer."
    prompt = f"""Transform the following natural language automotive requirement into a structured AUTOSAR Software Component (SWC) specification.

Requirement:
"{requirement}"

Format your response strictly following this structure:

SWC: <SWC_Name>

Input:
  <Input_Signal_1>
  <Input_Signal_2> (if any)

Output:
  <Output_Signal_1>
  <Output_Signal_2> (if any)

Runnable:
  <Runnable_Name>

Logic:
  if <Condition>
      <Action>
  else
      <Action>
"""

    response = query_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
    )

    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(output_dir, exist_ok=True)

    # Write specification to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(response.strip() + "\n")

    abs_path = os.path.abspath(output_file)
    print("\n" + "=" * 60)
    print(f"[SUCCESS] AUTOSAR Specification saved to:")
    print(f"  --> {abs_path}")
    print("=" * 60)

    return response


def main():
    parser = argparse.ArgumentParser(
        description="Extract AUTOSAR SWC specification and save to disk"
    )
    parser.add_argument(
        "requirement",
        nargs="*",
        default=[DEFAULT_REQUIREMENT],
        help="Natural language automotive requirement string",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output/swc_spec.txt",
        help="Output specification file path (default: output/swc_spec.txt)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens to generate (default: 512)",
    )
    args = parser.parse_args()

    requirement_text = (
        " ".join(args.requirement)
        if isinstance(args.requirement, list)
        else args.requirement
    )

    print("=" * 60)
    print("AUTOSAR_LLM - Requirement to SWC Specification (Local Qwen)")
    print("=" * 60)
    print(f"Input Requirement:\n  \"{requirement_text}\"\n")
    print(f"Target Output: {args.output}\n")

    try:
        generate_swc_spec(
            requirement=requirement_text,
            output_file=args.output,
            max_tokens=args.max_tokens,
        )
    except Exception as exc:
        print(f"\n[ERROR] Specification generation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
