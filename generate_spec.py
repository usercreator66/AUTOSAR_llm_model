"""Generate AUTOSAR C or C++ source from requirements and retrieved evidence."""

import os
import re
import sys
import argparse
from dotenv import load_dotenv
from llm_client import query_llm
from autosar_spec_engine import AutosarSpecEngine

load_dotenv()

DEFAULT_REQUIREMENT = (
    "Create a component named VehicleSpeedMonitor that monitors vehicle speed "
    "and sets an output when speed exceeds 100 km/h."
)
PLATFORMS = {
    "classic": ("C", ".c", "Classic"),
    "adaptive": ("C++", ".cpp", "Adaptive"),
}


def extract_source_code(response: str, language: str) -> str:
    """Extract a model's fenced C/C++ source block, or accept plain source."""
    text = re.sub(r"<think>.*?</think>", "", response.strip(), flags=re.DOTALL | re.IGNORECASE).strip()
    code_blocks = re.findall(
        r"```(?:c\+\+|cpp|c)?\s*(.*?)```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if code_blocks:
        source = code_blocks[0].strip()
    else:
        source = text
        source_start = re.search(
            r"(?m)^(?:\s*#include\b|\s*#pragma\b|\s*(?:template|namespace|class|struct|enum|typedef|using|extern|static|const|void|int|bool|auto|uint\d+_t)\b)",
            source,
        )
        if source_start:
            source = source[source_start.start():].strip()

    if not source or not re.search(r"[{};]", source):
        raise ValueError(f"Model did not return recognizable {language} source code.")
    return source


def infer_component_name(requirement: str) -> str:
    """Infer a component prefix from common AUTOSAR CamelCase identifiers."""
    named_component = re.search(
        r"\b(?:component|module)\s*(?::|named|called)\s*([A-Za-z][A-Za-z0-9_]*)",
        requirement,
        flags=re.IGNORECASE,
    )
    if named_component:
        return named_component.group(1)
    swc_name = re.search(r"\bSWC\s*:\s*([A-Z][A-Za-z0-9_]+)", requirement)
    if swc_name:
        return swc_name.group(1)

    candidates = re.findall(
        r"\b[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+(?:_[A-Za-z0-9]+)*\b",
        requirement,
    )
    excluded = {"AUTOSAR", "Classic", "Adaptive", "SWC"}
    return next((name for name in candidates if name not in excluded), "AutosarComponent")


def _resolve_output_path(
    requirement: str,
    platform: str,
    output_file: str | None,
    component: str | None,
) -> tuple[str, str]:
    component_name = re.sub(r"[^A-Za-z0-9_]+", "", (component or infer_component_name(requirement)).strip())
    if not component_name:
        raise ValueError("component must contain at least one letter, digit, or underscore")

    _, extension, _ = PLATFORMS[platform]
    if output_file:
        requested_path = os.path.abspath(output_file)
        directory, filename = os.path.split(requested_path)
        stem, requested_extension = os.path.splitext(filename)
        requested_extension = requested_extension or extension
        if stem.casefold().startswith(f"{component_name}_".casefold()):
            filename = f"{stem}{requested_extension}"
        elif stem.casefold() == component_name.casefold():
            filename = f"{component_name}_{platform}{requested_extension}"
        else:
            filename = f"{component_name}_{stem}{requested_extension}"
        return os.path.join(directory, filename), component_name

    return os.path.join("output", f"{component_name}_{platform}{extension}"), component_name


def generate_swc_spec(
    requirement: str,
    output_file: str = "output/swc_spec.txt",
    max_tokens: int = 512,
) -> str:
    """
    Extracts structured SWC specification and saves it to a file.
    """
    system_prompt = "You are an AUTOSAR systems engineer."
    spec_context = AutosarSpecEngine().build_context(requirement)
    prompt = f"""Transform the following natural language automotive requirement into a structured AUTOSAR Software Component (SWC) specification.

AUTOSAR SPECIFICATION EVIDENCE:
{spec_context}

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


def generate_autosar_code(
    requirement: str,
    platform: str = "classic",
    output_file: str | None = None,
    max_tokens: int = 8192,
    component: str | None = None,
) -> str:
    """Generate platform-specific source using matching AUTOSAR evidence."""
    platform = platform.strip().lower()
    if platform not in PLATFORMS:
        raise ValueError("platform must be 'classic' or 'adaptive'")

    language, _, platform_name = PLATFORMS[platform]
    output_file, component_name = _resolve_output_path(
        requirement, platform, output_file, component
    )
    spec_context = AutosarSpecEngine().build_context(requirement, platform=platform)
    system_prompt = (
        f"You are an AUTOSAR {platform_name} Platform {language} code generator. "
        "Generate complete, maintainable source code and follow the supplied "
        "specification evidence. Do not invent AUTOSAR APIs or normative requirements."
    )
    code_fence = "cpp" if platform == "adaptive" else "c"
    prompt = f"""Generate {language} source code for the following AUTOSAR requirement or software-component specification.

REQUIREMENT / SPECIFICATION:
{requirement}

RETRIEVED AUTOSAR {platform_name.upper()} SPECIFICATION EVIDENCE:
{spec_context}

IMPLEMENTATION REQUIREMENTS:
- Implement every specified input, output, runnable, and behavior; do not omit listed signals or logic.
- Return one complete source file in {language}, including required declarations and headers.
- Use only APIs supported by the supplied evidence or explicitly provided by the requirement.
- If project-specific RTE or service names are absent, use clearly marked integration placeholders instead of fabricated AUTOSAR APIs.
- Return source code only, preferably in one ```{code_fence} fenced block.
"""
    response = query_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
    )
    if not isinstance(response, str):
        response = getattr(response, "text", None) or getattr(response, "content", None)
    if not response:
        raise ValueError("Local model returned an empty or unsupported response.")

    source_code = extract_source_code(response, language)
    output_dir = os.path.dirname(os.path.abspath(output_file))
    os.makedirs(output_dir, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as output:
        output.write(source_code + "\n")

    print(f"\n[SUCCESS] AUTOSAR {component_name} {platform_name} {language} source saved to:")
    print(f"  --> {os.path.abspath(output_file)}")
    return source_code


def main():
    parser = argparse.ArgumentParser(
        description="Generate AUTOSAR Classic C or Adaptive C++ source from a requirement/specification"
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
        default=None,
        help="Output path; the filename is prefixed with the inferred or specified component name",
    )
    parser.add_argument(
        "--platform",
        choices=tuple(PLATFORMS),
        default="classic",
        help="AUTOSAR platform and source language (default: classic/C)",
    )
    parser.add_argument(
        "--component",
        help="AUTOSAR component name for the generated filename (inferred when omitted)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=8192,
        help="Maximum tokens to generate (default: 8192)",
    )
    args = parser.parse_args()

    requirement_text = (
        " ".join(args.requirement)
        if isinstance(args.requirement, list)
        else args.requirement
    )

    print("=" * 60)
    language, _, platform_name = PLATFORMS[args.platform]
    output_file, component_name = _resolve_output_path(
        requirement_text, args.platform, args.output, args.component
    )
    print(f"AUTOSAR_LLM - AUTOSAR {platform_name} {language} Generator (Local Qwen)")
    print("=" * 60)
    print(f"Input Requirement:\n  \"{requirement_text}\"\n")
    print(f"Component: {component_name}\nTarget Output: {output_file}\n")

    try:
        generate_autosar_code(
            requirement=requirement_text,
            platform=args.platform,
            output_file=output_file,
            max_tokens=args.max_tokens,
            component=component_name,
        )
    except Exception as exc:
        print(f"\n[ERROR] Specification generation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
