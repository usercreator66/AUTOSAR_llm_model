"""Generate AUTOSAR C or C++ source from requirements and retrieved evidence."""

import os
import re
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from llm_client import query_llm
from autosar_spec_engine import AutosarSpecEngine

load_dotenv()

DEFAULT_REQUIREMENT = ("Generate autosar code")

PLATFORMS = {
    "classic": ("C", ".c", "Classic"),
    "adaptive": ("C++", ".cpp", "Adaptive"),
}
PROJECT_SOURCE_SUFFIXES = {".c", ".h", ".cc", ".hh", ".cpp", ".hpp", ".cxx", ".hxx", ".arxml"}
IGNORED_PROJECT_DIRS = {".git", ".venv", "__pycache__", "build", "dist", "install", "node_modules", "third_party", "vendor"}
MAX_PROJECT_FILES = 16
MAX_PROJECT_CONTEXT_CHARS = 24000
DEFAULT_SPEC_ROOT = PROJECT_ROOT / "autosar_spec"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
FILE_CHUNK_TOKENS = 4096
MAX_FILE_CHUNKS = 100
MAX_CONTINUATION_CONTEXT_CHARS = 10000
FILE_COMPLETE_MARKER = "/*__AUTOSAR_FILE_COMPLETE__*/"


def _specification_type(filename: str) -> str | None:
    match = re.search(r"_(EXP|RS|SWS|TPS|TR)_", Path(filename).name, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def select_component_spec_files(
    component: str,
    platform: str,
    spec_list_path: str | Path | None = None,
    spec_root: str | Path = DEFAULT_SPEC_ROOT,
) -> dict[str, tuple[str, ...]]:
    """Select component files and determine the strongest available evidence tier."""
    platform = platform.strip().lower()
    if platform not in PLATFORMS:
        raise ValueError("platform must be 'classic' or 'adaptive'")

    root = Path(spec_root).expanduser().resolve()
    platform_folder = root / f"{platform}_autosar_R25_11"
    list_path = (
        Path(spec_list_path).expanduser().resolve()
        if spec_list_path
        else PROJECT_ROOT / f"input_{platform}_spec.txt"
    )
    if list_path.is_file():
        listed_names = {
            Path(line.strip().replace("\\", "/")).name
            for line in list_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    elif platform_folder.is_dir():
        listed_names = {path.name for path in platform_folder.glob("*.pdf") if path.is_file()}
    else:
        raise FileNotFoundError(f"No {platform.title()} AUTOSAR spec list or spec folder found.")

    available_names = tuple(
        sorted(
            filename
            for filename in listed_names
            if (platform_folder / filename).is_file() and Path(filename).suffix.lower() == ".pdf"
        )
    )
    component_name = Path(component.strip().replace("\\", "/")).stem
    component_key = re.sub(r"[^A-Za-z0-9]", "", component_name).casefold()
    if not component_key:
        raise ValueError("component must contain letters or digits")
    matching_names = tuple(
        filename
        for filename in available_names
        if Path(filename).stem.casefold().endswith(component_key)
    )
    exp_files = tuple(name for name in matching_names if _specification_type(name) == "EXP")
    rs_files = tuple(name for name in matching_names if _specification_type(name) == "RS")
    sws_files = tuple(name for name in matching_names if _specification_type(name) == "SWS")
    tps_files = tuple(name for name in matching_names if _specification_type(name) == "TPS")
    tr_files = tuple(name for name in matching_names if _specification_type(name) == "TR")

    if rs_files and sws_files:
        primary_types = ("RS", "SWS")
    elif sws_files:
        primary_types = ("SWS",)
    elif rs_files:
        primary_types = ("RS",)
    elif tps_files or tr_files:
        primary_types = tuple(
            kind for kind, files in (("TPS", tps_files), ("TR", tr_files)) if files
        )
    elif exp_files:
        primary_types = ("EXP",)
    else:
        raise ValueError(
            f"No EXP, RS, SWS, TPS, or TR PDF ending in '{component_name}' was found "
            f"in {list_path if list_path.is_file() else platform_folder}."
        )

    return {
        "exp": exp_files,
        "rs": rs_files,
        "sws": sws_files,
        "tps": tps_files,
        "tr": tr_files,
        "primary_types": primary_types,
    }


def load_project_context(
    project_path: str | Path | None,
    requirement: str = "",
    max_files: int = MAX_PROJECT_FILES,
    max_chars: int = MAX_PROJECT_CONTEXT_CHARS,
) -> str:
    """Read relevant existing C/C++/ARXML files from an optional project folder."""
    if project_path is None:
        return "No project folder was supplied."

    root = Path(project_path).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Project path is not a folder: {root}")

    source_files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in PROJECT_SOURCE_SUFFIXES
        and path.name.casefold() not in IGNORED_PROJECT_FILES
        and not any(part.lower() in IGNORED_PROJECT_DIRS for part in path.relative_to(root).parts)
    ]
    query_terms = set(re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", requirement.casefold()))
    source_files.sort(
        key=lambda path: (
            -sum(term in path.relative_to(root).as_posix().casefold() for term in query_terms),
            path.relative_to(root).as_posix().casefold(),
        )
    )

    sections = []
    used_chars = 0
    for path in source_files[: max(int(max_files), 1)]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if not text:
            continue

        header = f"--- {path.relative_to(root).as_posix()} ---\n"
        remaining = max(int(max_chars), 1) - used_chars
        if remaining <= len(header):
            break
        content = text[: remaining - len(header)]
        if len(content) < len(text):
            last_line = content.rsplit("\n", 1)
            if len(last_line) > 1:
                content = last_line[0]
            content = content.rstrip() + "\n[truncated]"
        section = header + content
        sections.append(section)
        used_chars += len(section)
        if used_chars >= max(int(max_chars), 1):
            break

    if not sections:
        return f"No readable C, C++, header, or ARXML files were found under: {root}"
    return "\n\n".join(sections)


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

    has_source_syntax = re.search(r"[{};]", source)
    has_header_directive = re.search(
        r"(?m)^\s*#\s*(?:include|define|ifndef|ifdef|endif|pragma|undef)\b",
        source,
    )
    if not source or not (has_source_syntax or has_header_directive):
        raise ValueError(f"Model did not return recognizable {language} source code.")
    return source


def _extract_source_chunk(response: str) -> tuple[str, bool]:
    text = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL | re.IGNORECASE)
    is_complete = FILE_COMPLETE_MARKER in text
    text = text.replace(FILE_COMPLETE_MARKER, "")
    text = re.sub(r"(?m)^\s*```(?:c\+\+|cpp|c)?\s*$", "", text, flags=re.IGNORECASE)
    return text.lstrip("\r\n"), is_complete


def _remove_chunk_overlap(existing: str, chunk: str, max_lines: int = 80) -> str:
    """Remove repeated complete lines when the model restarts from its context tail."""
    existing_lines = existing.splitlines(keepends=True)
    chunk_lines = chunk.splitlines(keepends=True)
    max_overlap = min(max_lines, len(existing_lines), len(chunk_lines))
    for overlap_lines in range(max_overlap, 0, -1):
        existing_overlap = [line.rstrip("\r\n") for line in existing_lines[-overlap_lines:]]
        chunk_overlap = [line.rstrip("\r\n") for line in chunk_lines[:overlap_lines]]
        if existing_overlap == chunk_overlap:
            return "".join(chunk_lines[overlap_lines:])
    return chunk


def generate_source_to_file(
    prompt: str,
    system_prompt: str,
    output_file: str | Path,
    language: str,
    max_tokens: int = 8192,
) -> str:
    """Generate source in bounded continuations and promote only a completed file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_name(output_path.name + ".partial")
    partial_path.write_text("", encoding="utf-8")
    accumulated = ""
    chunk_limit = min(max(int(max_tokens), 1), FILE_CHUNK_TOKENS)

    for chunk_number in range(1, MAX_FILE_CHUNKS + 1):
        continuation = ""
        if accumulated:
            continuation = (
                "\n\nCONTINUE THE SAME SOURCE FILE. Do not restart or repeat prior code. "
                "Continue at the exact end of the source tail below. Emit complete logical "
                "C/C++ lines where possible. Only emit the completion marker after the entire "
                f"file is complete.\n\nSOURCE TAIL ALREADY WRITTEN:\n{accumulated[-MAX_CONTINUATION_CONTEXT_CHARS:]}"
            )
        chunk_prompt = (
            f"{prompt}\n\n"
            "OUTPUT CHUNK RULES:\n"
            "- Return only new source text, without Markdown fences or explanations.\n"
            "- If more source is needed, stop at a reasonable continuation point and do not emit the completion marker.\n"
            f"- When the complete file is finished, put this exact marker on its own final line: {FILE_COMPLETE_MARKER}"
            f"{continuation}"
        )
        response = query_llm(
            prompt=chunk_prompt,
            system_prompt=system_prompt,
            max_tokens=chunk_limit,
        )
        if not isinstance(response, str):
            response = getattr(response, "text", None) or getattr(response, "content", None)
        if not response:
            raise ValueError(f"The model returned no content for {output_path.name} chunk {chunk_number}.")

        chunk, is_complete = _extract_source_chunk(response)
        chunk = _remove_chunk_overlap(accumulated, chunk)
        if not chunk.strip() and not is_complete:
            raise ValueError(
                f"The model made no progress while generating {output_path.name}; "
                f"partial output is preserved at {partial_path}."
            )
        if chunk:
            with partial_path.open("a", encoding="utf-8", newline="") as output:
                output.write(chunk)
            accumulated += chunk

        if is_complete:
            source = extract_source_code(accumulated, language)
            partial_path.write_text(source.rstrip() + "\n", encoding="utf-8")
            partial_path.replace(output_path)
            return source

    raise ValueError(
        f"Generation exceeded {MAX_FILE_CHUNKS} chunks for {output_path.name}; "
        f"partial output is preserved at {partial_path}."
    )


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

    return os.path.join(str(DEFAULT_OUTPUT_DIR), f"{component_name}_{platform}{extension}"), component_name


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
    project_path: str | Path | None = None,
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
    project_context = load_project_context(project_path, requirement)
    system_prompt = (
        f"You are an AUTOSAR {platform_name} Platform {language} code generator. "
        "Generate complete, maintainable source code and follow the supplied "
        "specification evidence. Do not invent AUTOSAR APIs or normative requirements."
    )
    if platform == "adaptive":
        system_prompt += (
            " For communication use the ara::com namespace, and for diagnostics use "
            "ara::diag when relevant. Preserve APIs and naming patterns from the "
            "provided project files; do not invent specific types or methods."
        )
    code_fence = "cpp" if platform == "adaptive" else "c"
    prompt = f"""Generate {language} source code for the following AUTOSAR requirement or software-component specification.

REQUIREMENT / SPECIFICATION:
{requirement}

RETRIEVED AUTOSAR {platform_name.upper()} SPECIFICATION EVIDENCE:
{spec_context}

EXISTING PROJECT SOURCE FILES:
{project_context}

IMPLEMENTATION REQUIREMENTS:
- Implement every specified input, output, runnable, and behavior; do not omit listed signals or logic.
- Return one complete source file in {language}, including required declarations and headers.
- Use only APIs supported by the supplied evidence or explicitly provided by the requirement.
- If project-specific RTE or service names are absent, use clearly marked integration placeholders instead of fabricated AUTOSAR APIs.
- Prefer existing project headers, namespaces, types, naming conventions, and interfaces when project files are supplied.
- For Adaptive communication or diagnostics, preserve the ara::com or ara::diag namespace respectively when supported by the requirement and project context.
- Return source code only, preferably in one ```{code_fence} fenced block.
"""
    source_code = generate_source_to_file(
        prompt=prompt,
        system_prompt=system_prompt,
        output_file=output_file,
        language=language,
        max_tokens=max_tokens,
    )

    print(f"\n[SUCCESS] AUTOSAR {component_name} {platform_name} {language} source saved to:")
    print(f"  --> {os.path.abspath(output_file)}")
    return source_code


def _format_spec_excerpts(excerpts, empty_message: str) -> str:
    if not excerpts:
        return empty_message
    return "\n\n".join(
        f"[{excerpt.citation}]\n{excerpt.text}" for excerpt in excerpts
    )


def generate_component_package(
    requirement: str,
    component: str,
    platform: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    spec_list_path: str | Path | None = None,
    spec_root: str | Path = DEFAULT_SPEC_ROOT,
    project_path: str | Path | None = None,
    max_tokens: int = 8192,
) -> dict[str, str]:
    """Analyze a component EXP, refine with RS/SWS evidence, and write its source package."""
    platform = platform.strip().lower()
    if platform not in PLATFORMS:
        raise ValueError("platform must be 'classic' or 'adaptive'")

    selected_specs = select_component_spec_files(
        component, platform, spec_list_path=spec_list_path, spec_root=spec_root
    )
    component_name = re.sub(r"[^A-Za-z0-9_]+", "", component.strip())
    if not component_name:
        raise ValueError("component must contain at least one letter, digit, or underscore")

    engine = AutosarSpecEngine(spec_root=spec_root)
    index_report = engine.index_documents()
    for error in index_report.errors:
        print(f"[AUTOSAR spec index] {error}")

    exp_excerpts = engine.search(
        requirement,
        platform=platform,
        top_k=8,
        document_types=("EXP",),
        sources=selected_specs["exp"] or None,
        refresh_index=False,
    )
    exp_context = _format_spec_excerpts(
        exp_excerpts,
        "No relevant EXP explanation was found; use EXP evidence only when retrieved and do not invent requirements.",
    )
    analysis_prompt = f"""Analyze this AUTOSAR {platform.title()} component requirement using the selected EXP document as explanatory guidance.

COMPONENT: {component_name}
REQUIREMENT:
{requirement}

SELECTED EXP DOCUMENT(S):
{', '.join(selected_specs['exp'])}

EXP EXPLANATORY EVIDENCE:
{exp_context}

Produce a concise requirement analysis that identifies the component's responsibilities, inputs, outputs, interfaces, relevant AUTOSAR concepts, and any unresolved assumptions. Explain the requirement using the EXP evidence; do not invent normative requirements or concrete APIs. Cite source and page for claims grounded in the excerpts.
"""
    analysis = query_llm(
        prompt=analysis_prompt,
        system_prompt=f"You are an AUTOSAR {platform.title()} requirements analyst. Ground explanations in the supplied EXP evidence.",
        max_tokens=min(max(int(max_tokens), 1), 2048),
    )
    if not isinstance(analysis, str):
        analysis = getattr(analysis, "text", None) or getattr(analysis, "content", None)
    if not analysis:
        raise ValueError("The model returned an empty component requirements analysis.")

    primary_types = selected_specs["primary_types"]
    if primary_types == ("EXP",) and not exp_excerpts:
        raise ValueError(
            f"The EXP reference for '{component_name}' has no searchable text in the SQLite index."
        )

    refined_query = f"{requirement}\n\nEXP-based requirement analysis:\n{analysis}"
    source_map = {
        "RS": selected_specs["rs"],
        "SWS": selected_specs["sws"],
        "TPS": selected_specs["tps"],
        "TR": selected_specs["tr"],
    }
    evidence_excerpts = {}
    for document_type in primary_types:
        if document_type == "EXP":
            excerpts = exp_excerpts
        else:
            excerpts = engine.search(
                refined_query,
                platform=platform,
                top_k=8,
                document_types=(document_type,),
                sources=source_map[document_type],
                refresh_index=False,
            )
        if not excerpts:
            raise ValueError(
                f"The selected {document_type} document(s) for '{component_name}' have no searchable text "
                "in the SQLite index. Verify PDF extraction and reindex the specification database."
            )
        evidence_excerpts[document_type] = excerpts

    evidence_contexts = {
        document_type: _format_spec_excerpts(
            excerpts,
            f"No matching {document_type} excerpts were found.",
        )
        for document_type, excerpts in evidence_excerpts.items()
    }
    affected_sources = sorted(
        {
            excerpt.citation
            for excerpt in (*exp_excerpts, *(excerpt for excerpts in evidence_excerpts.values() for excerpt in excerpts))
        }
    )
    evidence_sections = []
    for document_type, context in evidence_contexts.items():
        qualifier = " (EXPLANATORY ONLY; NOT NORMATIVE)" if document_type == "EXP" else ""
        evidence_sections.append(f"AUTOSAR {document_type} EVIDENCE{qualifier}:\n{context}")
    combined_evidence = "\n\n".join(evidence_sections)
    if primary_types == ("RS", "SWS"):
        priority_guidance = "Use both the component RS and SWS as the primary normative basis."
    elif primary_types == ("EXP",):
        priority_guidance = "Only EXP reference material is available; treat it as non-normative and identify assumptions/placeholders explicitly."
    else:
        priority_guidance = (
            f"The highest available component evidence is {', '.join(primary_types)}; "
            "do not imply that absent higher-priority documents were checked."
        )
    package_dir = Path(output_dir).expanduser().resolve() / component_name
    package_dir.mkdir(parents=True, exist_ok=True)
    project_context = load_project_context(project_path or package_dir, requirement)

    if platform == "classic":
        outputs = (
            (f"{component_name}_app.h", "application interfaces, public types, and declarations"),
            (f"{component_name}_cfg.h", "configuration declarations and constants"),
            (f"{component_name}_app.c", "application behavior and runnable logic"),
            (f"{component_name}_cfg.c", "configuration definitions and defaults"),
        )
        language = "C"
        namespace_rules = "Use AUTOSAR Classic C conventions and only interfaces justified by the supplied sources."
    else:
        outputs = (
            (f"{component_name}.hpp", "component public interface and declarations"),
            (f"{component_name}.cpp", "component implementation"),
        )
        language = "C++"
        namespace_rules = (
            "For communication use ara::com; for diagnostics use ara::diag when relevant. "
            "Use concrete APIs only when shown in the supplied project or evidence."
        )

    generated: dict[str, str] = {}
    for filename, role in outputs:
        code_fence = "cpp" if platform == "adaptive" else "c"
        existing_generated = "\n\n".join(
            f"--- {generated_name} ---\n{source}"
            for generated_name, source in generated.items()
        ) or "No sibling output files have been generated yet."
        prompt = f"""Generate exactly one source file for an AUTOSAR {platform.title()} component.

COMPONENT: {component_name}
FILE TO GENERATE: {filename}
FILE ROLE: {role}
COMPONENT REQUIREMENT:
{requirement}

EXP EXPLANATORY CONTEXT:
{analysis}

SELECTED PRIORITY EVIDENCE:
{combined_evidence}

EXISTING PROJECT FILES:
{project_context}

SIBLING FILES ALREADY GENERATED FOR THIS COMPONENT:
{existing_generated}

IMPLEMENTATION RULES:
- {priority_guidance}
- Use EXP only to understand concepts; EXP is not normative and does not substitute for RS, SWS, TPS, or TR requirements.
- Keep declarations and definitions consistent with the sibling files and existing project patterns.
- Include a source comment naming the affected AUTOSAR specification documents; preserve that comment in the generated file.
- {namespace_rules}
- Do not fabricate APIs, configuration values, or behavior absent from the requirement, evidence, or existing project.
- Return only the complete contents of {filename}, preferably in one ```{code_fence} fenced block.
"""
        source_path = package_dir / filename
        source = generate_source_to_file(
            prompt=prompt,
            system_prompt=f"You are an AUTOSAR {platform.title()} {language} component engineer. Generate the requested file only.",
            output_file=source_path,
            language=language,
            max_tokens=max_tokens,
        )
        source_comment = "/*\n * Affected AUTOSAR specification sources:\n" + "".join(
            f" * - {citation}\n" for citation in affected_sources
        ) + " */\n"
        if not source.startswith("/*") or "Affected AUTOSAR specification sources:" not in source[:500]:
            source = source_comment + source
        source_path.write_text(source.rstrip() + "\n", encoding="utf-8")
        generated[filename] = source

    analysis_path = package_dir / f"{component_name}_requirements_analysis.md"
    analysis_path.write_text(
        f"# {component_name} Requirements Analysis\n\n"
        f"Platform: AUTOSAR {platform.title()}\n\n"
        f"## Requirement\n\n{requirement}\n\n"
        f"## EXP-Based Understanding\n\n{analysis}\n\n"
        f"## Retrieved RS/SWS Sources\n\n"
        + "\n".join(f"- {source}" for source in affected_sources)
        + "\n",
        encoding="utf-8",
    )
    print(f"[SUCCESS] Generated {len(generated)} source files for {component_name} in {package_dir}")
    return generated


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
        help="AUTOSAR component name for the generation (inferred when omitted)",
    )
    parser.add_argument(
        "--project-path",
        "--project-dir",
        dest="project_path",
        type=Path,
        help="Optional project folder whose existing C/C++/header/ARXML files guide generation",
    )
    parser.add_argument(
        "--spec-list",
        type=Path,
        help="Platform spec-list file (defaults to input_<platform>_spec.txt)",
    )
    parser.add_argument(
        "--spec-root",
        type=Path,
        default=DEFAULT_SPEC_ROOT,
        help="Root containing classic_autosar_R25_11 and adaptive_autosar_R25_11",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Parent folder for the component package (default: output)",
    )
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="Generate one source file instead of a component package",
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

    language, _, platform_name = PLATFORMS[args.platform]
    try:
        if args.component and not args.single_file:
            if args.output:
                parser.error("--output is for --single-file mode; use --output-dir for a component package")
            print(f"AUTOSAR_LLM - AUTOSAR {platform_name} component package")
            print(f"Component: {args.component}\nRequirement: {requirement_text}\n")
            generate_component_package(
                requirement=requirement_text,
                component=args.component,
                platform=args.platform,
                output_dir=args.output_dir,
                spec_list_path=args.spec_list,
                spec_root=args.spec_root,
                project_path=args.project_path,
                max_tokens=args.max_tokens,
            )
        else:
            output_file, component_name = _resolve_output_path(
                requirement_text, args.platform, args.output, args.component
            )
            print("=" * 60)
            print(f"AUTOSAR_LLM - AUTOSAR {platform_name} {language} Generator (Local Qwen)")
            print("=" * 60)
            print(f"Input Requirement:\n  \"{requirement_text}\"\n")
            print(f"Component: {component_name}\nTarget Output: {output_file}\n")
            generate_autosar_code(
                requirement=requirement_text,
                platform=args.platform,
                output_file=output_file,
                max_tokens=args.max_tokens,
                component=component_name,
                project_path=args.project_path,
            )
    except Exception as exc:
        print(f"\n[ERROR] Specification generation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
