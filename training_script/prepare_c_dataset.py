"""Build a LLaMA-Factory Alpaca dataset from all files in a folder."""

import argparse
import json
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def build_records(input_dir: Path, instruction: str) -> list[dict[str, str]]:
    if not input_dir.is_dir():
        raise ValueError(f"Input path is not a folder: {input_dir}")

    source_files = sorted(path for path in input_dir.rglob("*") if path.is_file())

    if not source_files:
        raise ValueError(f"No C/C++ source files found in {input_dir}")

    file_blocks = []
    for source_path in source_files:
        relative_path = source_path.relative_to(input_dir)
        file_blocks.append(f"--- FILE: {relative_path.as_posix()} ---\n{read_text(source_path)}")

    return [
        {
            "instruction": instruction,
            "input": "\n\n".join(file_blocks),
            "output": "",
        }
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        "--input-dir",
        dest="input_dir",
        type=Path,
        required=True,
        help="Folder whose files should be included recursively",
    )
    parser.add_argument("--output-file", type=Path, required=True, help="Destination JSON dataset")
    parser.add_argument(
        "--instruction",
        default="Analyze the supplied AUTOSAR C source and produce the required implementation or specification.",
    )
    args = parser.parse_args()

    records = build_records(args.input_dir, args.instruction)
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records to {args.output_file}")


if __name__ == "__main__":
    main()