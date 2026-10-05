"""Build an AUTOSAR CP R25-11 ECUC learning dataset from ARXML and PDF specifications."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, deque
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SPEC_ROOT = ROOT / "autosar_spec" / "R25_11"
DEFAULT_SOURCE = SPEC_ROOT / "AUTOSAR_CP_MOD_ECUConfigurationParameters.zip"
DEFAULT_OUTPUT = ROOT / "data" / "AR_R2511_train.json"
NAMESPACE = "http://autosar.org/schema/r4.0"
NS = {"a": NAMESPACE}
SOURCE_MEMBER = "AUTOSAR_CP_MOD_ECUConfigurationParameters.arxml"
CONTAINER_TAGS = {"ECUC-PARAM-CONF-CONTAINER-DEF", "ECUC-CHOICE-CONTAINER-DEF"}
PDF_PREFIXES = ("AUTOSAR_CP_SWS_", "AUTOSAR_CP_RS_", "AUTOSAR_CP_TPS_")
PDF_RULE_MARKER = re.compile(
    r"\b(?:shall|shall not|must|must not|should|should not|required|mandatory|optional|only|unless|if|when|depends|dependent|minimum|maximum|at least|at most|not allowed|prohibited)\b",
    re.IGNORECASE,
)
PDF_NON_NORMATIVE_PAGE = re.compile(r"\b(?:release management|revision history|table of contents)\b", re.IGNORECASE)


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def normalize(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def child(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element if local_name(item) == name), None)


def field(element: ET.Element, name: str) -> str | None:
    item = child(element, name)
    if item is None:
        return None
    return normalize(" ".join(item.itertext())) or None


def description(element: ET.Element, section_name: str) -> str | None:
    section = child(element, section_name)
    if section is None:
        return None
    translations = [
        normalize(" ".join(item.itertext()))
        for item in section.iter()
        if local_name(item) in {"L-1", "L-2", "L-4"}
        and item.get("L", "EN").upper() == "EN"
    ]
    translations = list(dict.fromkeys(text for text in translations if text))
    return " ".join(translations) or normalize(" ".join(section.itertext())) or None


def multiplicity(element: ET.Element) -> str:
    lower = field(element, "LOWER-MULTIPLICITY")
    upper = field(element, "UPPER-MULTIPLICITY")
    infinite = field(element, "UPPER-MULTIPLICITY-INFINITE")
    if upper is None and infinite and infinite.lower() == "true":
        upper = "unbounded"
    if lower is None and upper is None:
        return "Not specified by this definition."
    return f"{lower if lower is not None else 'not specified'}..{upper if upper is not None else 'not specified'} instances"


def configuration_classes(element: ET.Element, group_name: str, entry_name: str) -> list[str]:
    group = child(element, group_name)
    if group is None:
        return []
    entries = []
    for entry in group.iter():
        if local_name(entry) != entry_name:
            continue
        config_class = field(entry, "CONFIG-CLASS")
        variant = field(entry, "CONFIG-VARIANT")
        value = " / ".join(part for part in (config_class, variant) if part)
        if value:
            entries.append(value)
    return list(dict.fromkeys(entries))


def trace_id(element: ET.Element) -> str | None:
    reference = child(element, "RELATED-TRACE-ITEM-REF")
    return normalize(" ".join(reference.itertext())) if reference is not None else None


def find_definitions(section: ET.Element | None, predicate) -> list[ET.Element]:
    if section is None:
        return []
    return [item for item in section.iter() if item is not section and predicate(local_name(item))]


def nested_containers(section: ET.Element | None) -> list[ET.Element]:
    if section is None:
        return []
    found = []

    def visit(parent: ET.Element) -> None:
        for item in parent:
            if local_name(item) in CONTAINER_TAGS:
                found.append(item)
            else:
                visit(item)

    visit(section)
    return found


def enum_literals(element: ET.Element) -> list[str]:
    literals = child(element, "LITERALS")
    if literals is None:
        return []
    result = []
    for item in literals.iter():
        if local_name(item) != "ECUC-ENUMERATION-LITERAL-DEF":
            continue
        name = field(item, "SHORT-NAME")
        desc = description(item, "DESC")
        if name:
            result.append(f"{name}: {desc}" if desc else name)
    return result


def source_line(archive_name: str) -> str:
    return f"Source: AUTOSAR CP R25-11, {archive_name}::{SOURCE_MEMBER}."


def make_record(instruction: str, query: str, answer: list[str]) -> dict[str, str]:
    return {
        "instruction": instruction,
        "input": query,
        "output": "\n".join(line for line in answer if line),
    }


def parameter_record(module: str, path: str, container: ET.Element, param: ET.Element, archive_name: str) -> dict[str, str]:
    name = field(param, "SHORT-NAME") or "(unnamed parameter)"
    tag = local_name(param)
    parameter_type = tag.removeprefix("ECUC-").removesuffix("-PARAM-DEF")
    desc = description(param, "DESC")
    intro = description(param, "INTRODUCTION")
    min_value = field(param, "MIN")
    max_value = field(param, "MAX")
    default = field(param, "DEFAULT-VALUE")
    literals = enum_literals(param)
    value_classes = configuration_classes(param, "VALUE-CONFIG-CLASSES", "ECUC-VALUE-CONFIGURATION-CLASS")
    multiplicity_classes = configuration_classes(
        param, "MULTIPLICITY-CONFIG-CLASSES", "ECUC-MULTIPLICITY-CONFIGURATION-CLASS"
    )
    symbolic = field(param, "SYMBOLIC-NAME-VALUE")
    requires_symbolic = field(param, "REQUIRES-SYMBOLIC-NAME-VALUE")
    post_build_value = field(param, "POST-BUILD-VARIANT-VALUE")
    post_build_multiplicity = field(param, "POST-BUILD-VARIANT-MULTIPLICITY")
    constraints = []
    if min_value is not None or max_value is not None:
        constraints.append(f"Declared value range: {min_value if min_value is not None else 'no minimum'}..{max_value if max_value is not None else 'no maximum'}.")
    else:
        constraints.append("Numeric minimum/maximum: not specified by this parameter definition.")
    if literals:
        constraints.append("Enumeration literals: " + "; ".join(literals) + ".")
    elif "ENUMERATION" in tag:
        constraints.append("Enumeration literals: none listed in this definition; do not invent vendor-specific values.")
    constraints.append(f"Default value: {default if default is not None else 'not specified by this definition'}.")
    constraints.append(f"Multiplicity: {multiplicity(param)}.")
    constraints.append(f"Value configuration classes/variants: {', '.join(value_classes) if value_classes else 'not specified'}.")
    constraints.append(f"Multiplicity configuration classes/variants: {', '.join(multiplicity_classes) if multiplicity_classes else 'not specified'}.")
    constraints.append(f"SYMBOLIC-NAME-VALUE: {symbolic if symbolic is not None else 'not specified'}.")
    constraints.append(f"REQUIRES-SYMBOLIC-NAME-VALUE: {requires_symbolic if requires_symbolic is not None else 'not specified'}.")
    constraints.append(f"Post-build value variant: {post_build_value if post_build_value is not None else 'not specified'}; post-build multiplicity variant: {post_build_multiplicity if post_build_multiplicity is not None else 'not specified'}.")
    constraints.append(f"Origin: {field(param, 'ORIGIN') or 'not specified'}.")
    related = trace_id(param)
    constraints.append(f"AUTOSAR trace item: {related}." if related else "AUTOSAR trace item: not specified.")
    answer = [
        f"Parameter: {name}",
        f"ECUC definition type: {parameter_type}.",
        f"Module: {module}.",
        f"Definition path: {path}.",
        f"Description: {desc}" if desc else "Description: not supplied in this definition.",
        f"Additional introduction: {intro}" if intro else "",
        *constraints,
        "Dependency guidance: the parent path and any separate ECUC reference definitions constrain how this parameter is placed or connected. This parameter definition alone does not establish dependencies that are not explicitly listed.",
        "Limitation: distinguish AUTOSAR-defined constraints from vendor-specific implementation constraints; do not infer an omitted bound, default, enum value, or dependency.",
        source_line(archive_name),
    ]
    query = f"For AUTOSAR CP R25-11, explain ECUC parameter {name} at {path}. Include its meaning, type, limits, default, multiplicity, variants, and any dependency caveats."
    return make_record(
        "Explain an AUTOSAR ECUC parameter from its release-specific definition without inventing omitted constraints.",
        query,
        answer,
    )


def reference_record(module: str, path: str, reference: ET.Element, archive_name: str) -> dict[str, str]:
    name = field(reference, "SHORT-NAME") or "(unnamed reference)"
    target = child(reference, "DESTINATION-REF")
    target_path = normalize(" ".join(target.itertext())) if target is not None else None
    target_type = target.get("DEST") if target is not None else None
    value_classes = configuration_classes(reference, "VALUE-CONFIG-CLASSES", "ECUC-VALUE-CONFIGURATION-CLASS")
    multiplicity_classes = configuration_classes(
        reference, "MULTIPLICITY-CONFIG-CLASSES", "ECUC-MULTIPLICITY-CONFIGURATION-CLASS"
    )
    desc = description(reference, "DESC")
    related = trace_id(reference)
    answer = [
        f"Reference definition: {name}.",
        f"Module: {module}.",
        f"Owning container: {path}.",
        f"Description: {desc}" if desc else "Description: not supplied in this definition.",
        f"Allowed destination type: {target_type or 'not specified'}.",
        f"Destination definition path: {target_path or 'not specified'}.",
        f"Multiplicity: {multiplicity(reference)}.",
        f"Value configuration classes/variants: {', '.join(value_classes) if value_classes else 'not specified'}.",
        f"Multiplicity configuration classes/variants: {', '.join(multiplicity_classes) if multiplicity_classes else 'not specified'}.",
        f"Origin: {field(reference, 'ORIGIN') or 'not specified'}.",
        f"AUTOSAR trace item: {related}." if related else "AUTOSAR trace item: not specified.",
        "Dependency interpretation: this reference is the explicit link to the listed destination type/path. Do not replace it with an unrelated module or infer additional targets.",
        source_line(archive_name),
    ]
    query = f"What configuration dependency does the ECUC reference {name} define in {module} at {path}? State its allowed target and cardinality."
    return make_record(
        "Explain an AUTOSAR ECUC reference as a typed configuration dependency using only its declared target and constraints.",
        query,
        answer,
    )


def container_record(module: str, path: str, container: ET.Element, archive_name: str) -> dict[str, str]:
    name = field(container, "SHORT-NAME") or "(unnamed container)"
    kind = "choice container" if local_name(container) == "ECUC-CHOICE-CONTAINER-DEF" else "parameter configuration container"
    desc = description(container, "DESC")
    intro = description(container, "INTRODUCTION")
    value_classes = configuration_classes(container, "VALUE-CONFIG-CLASSES", "ECUC-VALUE-CONFIGURATION-CLASS")
    multiplicity_classes = configuration_classes(
        container, "MULTIPLICITY-CONFIG-CLASSES", "ECUC-MULTIPLICITY-CONFIGURATION-CLASS"
    )
    related = trace_id(container)
    answer = [
        f"Container: {name} ({kind}).",
        f"Module: {module}.",
        f"Definition path: {path}.",
        f"Description: {desc}" if desc else "Description: not supplied in this definition.",
        f"Additional introduction: {intro}" if intro else "",
        f"Multiplicity: {multiplicity(container)}.",
        f"Value configuration classes/variants: {', '.join(value_classes) if value_classes else 'not specified'}.",
        f"Multiplicity configuration classes/variants: {', '.join(multiplicity_classes) if multiplicity_classes else 'not specified'}.",
        f"Origin: {field(container, 'ORIGIN') or 'not specified'}.",
        f"AUTOSAR trace item: {related}." if related else "AUTOSAR trace item: not specified.",
        "Configuration guidance: child parameter definitions, sub-containers, and reference definitions are separate constraints. For a choice container, inspect the listed CHOICES alternatives and their own multiplicities; do not assume every alternative is configured.",
        source_line(archive_name),
    ]
    query = f"Explain the role and cardinality of AUTOSAR ECUC container {name} at {path} in module {module}. Include configuration-class and choice-branch caveats."
    return make_record(
        "Explain an AUTOSAR ECUC configuration container and how its cardinality and branch structure limit configuration.",
        query,
        answer,
    )


def relation_record(module: str, parent_path: str, parent: ET.Element | None, child_container: ET.Element, relation: str, archive_name: str) -> dict[str, str]:
    child_name = field(child_container, "SHORT-NAME") or "(unnamed container)"
    parent_name = field(parent, "SHORT-NAME") if parent is not None else module
    child_path = f"{parent_path}/{child_name}"
    desc = description(child_container, "DESC")
    parent_kind = "choice container" if parent is not None and local_name(parent) == "ECUC-CHOICE-CONTAINER-DEF" else "configuration container/module root"
    answer = [
        f"Module: {module}.",
        f"Parent: {parent_name} ({parent_kind}) at {parent_path}.",
        f"Relationship: child is declared under {relation}.",
        f"Child: {child_name} at {child_path}.",
        f"Child kind: {'choice container' if local_name(child_container) == 'ECUC-CHOICE-CONTAINER-DEF' else 'parameter configuration container'}.",
        f"Child multiplicity: {multiplicity(child_container)}.",
        f"Description: {desc}" if desc else "Description: not supplied in this definition.",
        "Dependency guidance: the path establishes the parent-child configuration hierarchy. Apply the child's declared multiplicity and any parent choice structure; do not treat sibling branches as mandatory unless the definitions require them.",
        source_line(archive_name),
    ]
    query = f"How is ECUC container {child_name} related to {parent_name} in module {module}, and what constrains its instances?"
    return make_record(
        "Explain a declared AUTOSAR ECUC parent-child or choice relationship and its configuration limits.",
        query,
        answer,
    )


def build_parameter_matcher(parameter_names: dict[str, str]):
    transitions = [{}]
    failures = [0]
    outputs = [[]]

    for key in parameter_names:
        state = 0
        for char in key:
            next_state = transitions[state].get(char)
            if next_state is None:
                next_state = len(transitions)
                transitions[state][char] = next_state
                transitions.append({})
                failures.append(0)
                outputs.append([])
            state = next_state
        outputs[state].append(key)

    queue = deque()
    for state in transitions[0].values():
        queue.append(state)

    while queue:
        state = queue.popleft()
        for char, next_state in transitions[state].items():
            queue.append(next_state)
            fallback = failures[state]
            while fallback and char not in transitions[fallback]:
                fallback = failures[fallback]
            failures[next_state] = transitions[fallback].get(char, 0)
            outputs[next_state].extend(outputs[failures[next_state]])

    return transitions, failures, outputs


def find_parameter_hits(text: str, matcher, parameter_names: dict[str, str]) -> dict[str, tuple[str, str]]:
    transitions, failures, outputs = matcher
    folded = text.casefold()
    hits = {}
    state = 0
    for index, char in enumerate(folded):
        while state and char not in transitions[state]:
            state = failures[state]
        state = transitions[state].get(char, 0)
        for key in outputs[state]:
            start = index - len(key) + 1
            end = index + 1
            if start < 0:
                continue
            if start and (folded[start - 1].isalnum() or folded[start - 1] == "_"):
                continue
            if end < len(folded) and (folded[end].isalnum() or folded[end] == "_"):
                continue
            if key in hits:
                continue
            excerpt = text[max(0, start - 260) : min(len(text), end + 420)].strip()
            if PDF_RULE_MARKER.search(excerpt):
                hits[key] = (parameter_names[key], excerpt)
    return hits


def pdf_evidence_records(pdf_root: Path, parameter_records: list[dict[str, str]]) -> tuple[list[dict[str, str]], Counter[str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF extraction requires pypdf. Install project requirements with: python -m pip install -r requirements.txt") from exc

    parameter_names = {}
    for record in parameter_records:
        match = re.search(r"^Parameter: (.+)$", record["output"], re.MULTILINE)
        if match and len(match.group(1)) >= 4:
            parameter_names[match.group(1).casefold()] = match.group(1)
    if not parameter_names:
        return [], Counter()

    matcher = build_parameter_matcher(parameter_names)
    pdf_files = sorted(
        path for path in pdf_root.rglob("*.pdf") if path.name.startswith(PDF_PREFIXES)
    )
    records = []
    counts: Counter[str] = Counter()

    for file_index, pdf_path in enumerate(pdf_files, 1):
        try:
            reader = PdfReader(str(pdf_path), strict=False)
        except Exception as exc:
            counts["pdf_files_failed"] += 1
            print(f"[PDF] Skipping {pdf_path.name}: {exc}")
            continue

        counts["pdf_files_scanned"] += 1
        for page_number, page in enumerate(reader.pages, 1):
            counts["pdf_pages_scanned"] += 1
            try:
                page_text = page.extract_text() or ""
            except Exception:
                counts["pdf_pages_failed"] += 1
                continue
            flattened = normalize(page_text)
            if not flattened:
                counts["pdf_pages_without_text"] += 1
                continue
            if PDF_NON_NORMATIVE_PAGE.search(flattened):
                counts["pdf_non_normative_pages_skipped"] += 1
                continue

            hits = list(find_parameter_hits(flattened, matcher, parameter_names).values())
            if not hits:
                continue

            counts["pdf_pages_with_parameter_constraints"] += 1
            for group_index in range(0, len(hits), 4):
                group = hits[group_index : group_index + 4]
                source = f"{pdf_path.name}, page {page_number}"
                evidence = [f"[{name}] {excerpt}" for name, excerpt in group]
                query = (
                    f"Using only the cited AUTOSAR CP R25-11 PDF evidence, identify explicit limitations, "
                    f"conditions, or dependencies for these ECUC parameter identifiers: "
                    f"{', '.join(name for name, _ in group)}. If the excerpt does not state a constraint, say so.\n"
                    f"Source: {source}\nEvidence excerpts:\n" + "\n".join(evidence)
                )
                answer = [
                    f"Source: AUTOSAR CP R25-11, {source}.",
                    "Parameter identifiers matched directly in the extracted PDF text: " + ", ".join(name for name, _ in group) + ".",
                    "Source evidence (line wrapping normalized):",
                    *[f"- {name}: {excerpt}" for name, excerpt in group],
                    "Interpretation limit: apply only restrictions stated in these excerpts. A missing bound, default, or dependency in this page is not evidence that it is absent from the complete AUTOSAR definition or another specification.",
                ]
                records.append(
                    make_record(
                        "Extract AUTOSAR ECUC parameter limitations and dependencies from cited normative specification text without inventing unstated rules.",
                        query,
                        answer,
                    )
                )
                counts["pdf_parameter_evidence_examples"] += 1
                counts["pdf_parameter_name_hits"] += len(group)

        if file_index % 20 == 0 or file_index == len(pdf_files):
            print(f"[PDF] Scanned {file_index}/{len(pdf_files)} specification files; added {counts['pdf_parameter_evidence_examples']} examples")

    return records, counts


def build_dataset(source_zip: Path, pdf_root: Path = SPEC_ROOT, include_pdfs: bool = True) -> tuple[list[dict[str, str]], Counter[str]]:
    with ZipFile(source_zip) as archive:
        if SOURCE_MEMBER not in archive.namelist():
            raise FileNotFoundError(f"Missing {SOURCE_MEMBER} in {source_zip}")
        root = ET.fromstring(archive.read(SOURCE_MEMBER))

    records: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    archive_name = source_zip.name

    def walk_container(module: str, container: ET.Element, parent_names: list[str], parent: ET.Element | None, relation: str) -> None:
        name = field(container, "SHORT-NAME") or "(unnamed container)"
        path = "/".join([module, *parent_names, name])
        records.append(container_record(module, path, container, archive_name))
        counts["containers"] += 1
        if parent is not None:
            records.append(relation_record(module, "/".join([module, *parent_names]), parent, container, relation, archive_name))
            counts["container_relationships"] += 1

        parameter_section = child(container, "PARAMETERS")
        params = find_definitions(parameter_section, lambda tag: tag.startswith("ECUC-") and tag.endswith("-PARAM-DEF"))
        for param in params:
            param_name = field(param, "SHORT-NAME") or "(unnamed parameter)"
            records.append(parameter_record(module, f"{path}/{param_name}", container, param, archive_name))
            counts[f"parameter:{local_name(param).removeprefix('ECUC-').removesuffix('-PARAM-DEF')}"] += 1

        reference_section = child(container, "REFERENCES")
        references = find_definitions(reference_section, lambda tag: tag == "ECUC-REFERENCE-DEF")
        for reference in references:
            records.append(reference_record(module, path, reference, archive_name))
            counts["references"] += 1

        for relation_name in ("SUB-CONTAINERS", "CHOICES"):
            section = child(container, relation_name)
            for child_container in nested_containers(section):
                walk_container(module, child_container, [*parent_names, name], container, relation_name)

    for module_def in root.findall(".//a:ECUC-MODULE-DEF", NS):
        module = field(module_def, "SHORT-NAME") or "(unnamed module)"
        module_containers = child(module_def, "CONTAINERS")
        for container in nested_containers(module_containers):
            walk_container(module, container, [], None, "CONTAINERS")
        counts["modules"] += 1

    if include_pdfs:
        pdf_records, pdf_counts = pdf_evidence_records(pdf_root, records)
        records.extend(pdf_records)
        counts.update(pdf_counts)

    return records, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--pdf-root", type=Path, default=SPEC_ROOT)
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-pdfs", action="store_true", help="Build from the ECUC ARXML model only")
    args = parser.parse_args()

    records, counts = build_dataset(args.source_zip, args.pdf_root, include_pdfs=not args.no_pdfs)
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_path = args.output_file.with_suffix(args.output_file.suffix + ".tmp")
    temp_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validated = json.loads(temp_path.read_text(encoding="utf-8"))
    if not validated or any(not all(row.get(key, "").strip() for key in ("instruction", "input", "output")) for row in validated):
        temp_path.unlink(missing_ok=True)
        raise ValueError("Generated dataset contains an empty or invalid training record.")
    temp_path.replace(args.output_file)

    print(f"Wrote {len(records)} source-grounded examples to {args.output_file}")
    print(f"Source: {args.source_zip}::{SOURCE_MEMBER}")
    for key, value in sorted(counts.items()):
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
