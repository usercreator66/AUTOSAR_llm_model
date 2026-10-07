import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generator import generate_spec


class IterativeSourceWriterTests(unittest.TestCase):
    def test_single_file_generation_uses_iterative_writer(self):
        output_path = Path(tempfile.mkdtemp()) / "Example_generated.c"
        response = (
            "#include <stdint.h>\nuint8_t Example_Read(void) { return 1U; }\n"
            + generate_spec.FILE_COMPLETE_MARKER
        )
        with patch("generator.generate_spec.AutosarSpecEngine") as engine:
            engine.return_value.build_context.return_value = "Retrieved AUTOSAR evidence"
            with patch.object(generate_spec, "query_llm", return_value=response) as query:
                source = generate_spec.generate_autosar_code(
                    requirement="Create Example reader",
                    platform="classic",
                    output_file=str(output_path),
                    component="Example",
                )

        self.assertEqual(query.call_count, 1)
        self.assertIn("Example_Read", source)
        self.assertEqual(output_path.read_text(encoding="utf-8"), source + "\n")

    def test_appends_chunks_and_removes_repeated_overlap(self):
        output_path = Path(tempfile.mkdtemp()) / "LargeComponent.cpp"
        chunks = [
            "#include <cstdint>\nvoid first() {\n    const int value = 1;\n}\n",
            "    const int value = 1;\n}\nvoid second() {\n    return;\n}\n"
            + generate_spec.FILE_COMPLETE_MARKER,
        ]
        with patch.object(generate_spec, "query_llm", side_effect=chunks) as query:
            source = generate_spec.generate_source_to_file(
                prompt="Generate this component source.",
                system_prompt="Return source only.",
                output_file=output_path,
                language="C++",
            )

        self.assertEqual(query.call_count, 2)
        self.assertIn("void first()", source)
        self.assertEqual(source.count("const int value"), 1)
        self.assertIn("void second()", source)
        self.assertNotIn(generate_spec.FILE_COMPLETE_MARKER, source)
        self.assertEqual(output_path.read_text(encoding="utf-8"), source + "\n")
        self.assertFalse(Path(str(output_path) + ".partial").exists())

    def test_keeps_partial_file_and_does_not_promote_without_completion_marker(self):
        output_path = Path(tempfile.mkdtemp()) / "Incomplete.cpp"
        with patch.object(generate_spec, "MAX_FILE_CHUNKS", 1):
            with patch.object(generate_spec, "query_llm", return_value="void incomplete() {"):
                with self.assertRaisesRegex(ValueError, "partial output is preserved"):
                    generate_spec.generate_source_to_file(
                        prompt="Generate this component source.",
                        system_prompt="Return source only.",
                        output_file=output_path,
                        language="C++",
                    )

        self.assertFalse(output_path.exists())
        self.assertEqual(Path(str(output_path) + ".partial").read_text(encoding="utf-8"), "void incomplete() {")


if __name__ == "__main__":
    unittest.main()
