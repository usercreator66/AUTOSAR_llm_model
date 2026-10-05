import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import autosar_cfg_gui
import generate_c
import generate_spec
import llm_client


class AutosarGenerationRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_c_generator_adds_retrieved_evidence_to_model_prompt(self):
        evidence = "RETRIEVED_AUTOSAR_EVIDENCE"
        response = "#include <stdint.h>\nuint8_t read_value(void) { return 1U; }"
        with patch("generate_c.AutosarSpecEngine") as engine:
            engine.return_value.build_context.return_value = evidence
            with patch.object(generate_c, "query_llm", return_value=response) as query:
                generate_c.generate_c_code("Create a CanIf helper", str(self.output_dir / "out.c"))

        self.assertIn(evidence, query.call_args.kwargs["prompt"])

    def test_swc_spec_generator_adds_retrieved_evidence_to_model_prompt(self):
        evidence = "RETRIEVED_AUTOSAR_EVIDENCE"
        with patch("generate_spec.AutosarSpecEngine") as engine:
            engine.return_value.build_context.return_value = evidence
            with patch.object(generate_spec, "query_llm", return_value="SWC: Example") as query:
                generate_spec.generate_swc_spec("Create a CanIf component", str(self.output_dir / "spec.txt"))

        self.assertIn(evidence, query.call_args.kwargs["prompt"])

    def test_classic_code_generation_uses_classic_evidence_and_writes_c(self):
        evidence = "CLASSIC_SPEC_EVIDENCE"
        source = "#include <stdint.h>\nvoid runnable(void) { }"
        output_path = self.output_dir / "CanIf_classic.c"
        with patch("generate_spec.AutosarSpecEngine") as engine:
            engine.return_value.build_context.return_value = evidence
            with patch.object(generate_spec, "query_llm", return_value=f"```c\n{source}\n```") as query:
                result = generate_spec.generate_autosar_code(
                    "Implement the CanIf Classic runnable",
                    "classic",
                    str(self.output_dir / "classic.c"),
                )

        engine.return_value.build_context.assert_called_once_with(
            "Implement the CanIf Classic runnable", platform="classic"
        )
        self.assertIn(evidence, query.call_args.kwargs["prompt"])
        self.assertEqual(result, source)
        self.assertEqual(output_path.read_text(encoding="utf-8").strip(), source)

    def test_adaptive_code_generation_uses_adaptive_evidence_and_writes_cpp(self):
        evidence = "ADAPTIVE_SPEC_EVIDENCE"
        source = "#include <cstdint>\nclass AdaptiveService { };"
        output_path = self.output_dir / "AdaptiveService_adaptive.cpp"
        with patch("generate_spec.AutosarSpecEngine") as engine:
            engine.return_value.build_context.return_value = evidence
            with patch.object(generate_spec, "query_llm", return_value=f"```cpp\n{source}\n```") as query:
                result = generate_spec.generate_autosar_code(
                    "Implement the Adaptive service",
                    "adaptive",
                    str(self.output_dir / "adaptive.cpp"),
                    component="AdaptiveService",
                )

        engine.return_value.build_context.assert_called_once_with(
            "Implement the Adaptive service", platform="adaptive"
        )
        self.assertIn(evidence, query.call_args.kwargs["prompt"])
        self.assertEqual(result, source)
        self.assertEqual(output_path.read_text(encoding="utf-8").strip(), source)

    def test_code_generation_rejects_unknown_platform(self):
        with self.assertRaisesRegex(ValueError, "platform must be"):
            generate_spec.generate_autosar_code("Implement a runnable", "unknown")

    def test_component_name_is_inferred_from_autosar_identifier(self):
        self.assertEqual(
            generate_spec.infer_component_name("Generate a CanTp transport component"),
            "CanTp",
        )

    def test_gui_generator_adds_retrieved_evidence_to_model_prompt(self):
        evidence = "RETRIEVED_AUTOSAR_EVIDENCE"
        response = "#include <stdint.h>\nuint8_t read_value(void) { return 1U; }"
        with patch("autosar_spec_engine.AutosarSpecEngine") as engine:
            engine.return_value.build_context.return_value = evidence
            with patch.object(llm_client, "LLMClient") as client:
                client.return_value.query.return_value = response
                autosar_cfg_gui.generate(
                    "Implement the requested module",
                    "Create a CanIf helper",
                    "Return a C function",
                    "model",
                    "",
                    None,
                    "c",
                    "4.4.0",
                )

        self.assertIn(evidence, client.return_value.query.call_args.kwargs["prompt"])


if __name__ == "__main__":
    unittest.main()