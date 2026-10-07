import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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
        project_path = self.output_dir / "adaptive_project"
        header_path = project_path / "include" / "AdaptiveService.hpp"
        header_path.parent.mkdir(parents=True)
        header_path.write_text(
            "namespace ara::com { class ServiceProxy {}; }\n"
            "namespace ara::diag { class Reporter {}; }\n",
            encoding="utf-8",
        )
        with patch("generate_spec.AutosarSpecEngine") as engine:
            engine.return_value.build_context.return_value = evidence
            with patch.object(generate_spec, "query_llm", return_value=f"```cpp\n{source}\n```") as query:
                result = generate_spec.generate_autosar_code(
                    "Implement the Adaptive service",
                    "adaptive",
                    str(self.output_dir / "adaptive.cpp"),
                    component="AdaptiveService",
                    project_path=project_path,
                )

        engine.return_value.build_context.assert_called_once_with(
            "Implement the Adaptive service", platform="adaptive"
        )
        self.assertIn(evidence, query.call_args.kwargs["prompt"])
        self.assertIn("namespace ara::com", query.call_args.kwargs["prompt"])
        self.assertIn("namespace ara::diag", query.call_args.kwargs["prompt"])
        self.assertIn("AdaptiveService.hpp", query.call_args.kwargs["prompt"])
        self.assertEqual(result, source)
        self.assertEqual(output_path.read_text(encoding="utf-8").strip(), source)

    def test_project_context_reads_source_and_excludes_venv(self):
        project_path = self.output_dir / "project"
        source_path = project_path / "src" / "CanIf.cpp"
        virtualenv_path = project_path / ".venv" / "Lib" / "site-packages" / "ignored.cpp"
        generated_path = project_path / "output" / "aradiag_adaptive.cpp"
        source_path.parent.mkdir(parents=True)
        virtualenv_path.parent.mkdir(parents=True)
        generated_path.parent.mkdir(parents=True)
        source_path.write_text("namespace ara::com { class CanIfProxy {}; }", encoding="utf-8")
        virtualenv_path.write_text("SHOULD_NOT_BE_INCLUDED", encoding="utf-8")
        generated_path.write_text("UNWANTED_ARADIAG_CONTEXT", encoding="utf-8")

        context = generate_spec.load_project_context(project_path, "Implement CanIf")

        self.assertIn("src/CanIf.cpp", context)
        self.assertIn("namespace ara::com", context)
        self.assertNotIn("SHOULD_NOT_BE_INCLUDED", context)
        self.assertNotIn("UNWANTED_ARADIAG_CONTEXT", context)

    def test_project_context_preserves_single_line_content_when_truncated(self):
        project_path = self.output_dir / "single_line_project"
        source_path = project_path / "src" / "service.cpp"
        source_path.parent.mkdir(parents=True)
        source_path.write_text("SINGLE_LINE_SOURCE_" + "x" * 200, encoding="utf-8")

        context = generate_spec.load_project_context(
            project_path, max_chars=80
        )

        self.assertIn("SINGLE_LINE_SOURCE_", context)
        self.assertIn("[truncated]", context)

    def test_code_generation_rejects_unknown_platform(self):
        with self.assertRaisesRegex(ValueError, "platform must be"):
            generate_spec.generate_autosar_code("Implement a runnable", "unknown")

    def test_component_name_is_inferred_from_autosar_identifier(self):
        self.assertEqual(
            generate_spec.infer_component_name("Generate a CanTp transport component"),
            "CanTp",
        )

    def test_component_spec_selection_matches_rs_and_sws_suffixes(self):
        spec_root = self.output_dir / "autosar_spec"
        platform_dir = spec_root / "adaptive_autosar_R25_11"
        platform_dir.mkdir(parents=True)
        filenames = (
            "AUTOSAR_AP_EXP_ARAComAPI.pdf",
            "AUTOSAR_AP_RS_CommunicationManagement.pdf",
            "AUTOSAR_AP_SWS_CommunicationManagement.pdf",
            "AUTOSAR_AP_RS_OtherComponent.pdf",
            "AUTOSAR_AP_SWS_OtherComponent.pdf",
        )
        for filename in filenames:
            (platform_dir / filename).write_bytes(b"spec")
        spec_list = self.output_dir / "input_adaptive_spec.txt"
        spec_list.write_text(
            "\n".join(
                f"autosar_spec/adaptive_autosar_R25_11/{filename}"
                for filename in filenames
            ),
            encoding="utf-8",
        )

        selected = generate_spec.select_component_spec_files(
            "CommunicationManagement.pdf",
            "adaptive",
            spec_list_path=spec_list,
            spec_root=spec_root,
        )

        self.assertEqual(selected["exp"], ())
        self.assertEqual(selected["rs"], ("AUTOSAR_AP_RS_CommunicationManagement.pdf",))
        self.assertEqual(selected["sws"], ("AUTOSAR_AP_SWS_CommunicationManagement.pdf",))
        self.assertEqual(selected["primary_types"], ("RS", "SWS"))

    def test_component_selection_uses_sws_when_diagnostics_has_no_rs(self):
        spec_root = self.output_dir / "autosar_spec"
        platform_dir = spec_root / "adaptive_autosar_R25_11"
        platform_dir.mkdir(parents=True)
        (platform_dir / "AUTOSAR_AP_SWS_Diagnostics.pdf").write_bytes(b"spec")
        spec_list = self.output_dir / "input_adaptive_spec.txt"
        spec_list.write_text(
            "autosar_spec/adaptive_autosar_R25_11/AUTOSAR_AP_SWS_Diagnostics.pdf\n",
            encoding="utf-8",
        )

        selected = generate_spec.select_component_spec_files(
            "Diagnostics.pdf",
            "adaptive",
            spec_list_path=spec_list,
            spec_root=spec_root,
        )

        self.assertEqual(selected["rs"], ())
        self.assertEqual(selected["sws"], ("AUTOSAR_AP_SWS_Diagnostics.pdf",))
        self.assertEqual(selected["primary_types"], ("SWS",))

    def test_component_spec_priority_follows_available_families(self):
        cases = (
            (("RS", "SWS", "TPS", "TR", "EXP"), ("RS", "SWS")),
            (("SWS", "TPS", "TR", "EXP"), ("SWS",)),
            (("RS", "TPS", "TR", "EXP"), ("RS",)),
            (("TPS", "TR", "EXP"), ("TPS", "TR")),
            (("EXP",), ("EXP",)),
        )
        for index, (available_types, expected_priority) in enumerate(cases):
            with self.subTest(available_types=available_types):
                spec_root = self.output_dir / f"priority_{index}" / "autosar_spec"
                platform_dir = spec_root / "adaptive_autosar_R25_11"
                platform_dir.mkdir(parents=True)
                filenames = tuple(
                    f"AUTOSAR_AP_{document_type}_PriorityComponent.pdf"
                    for document_type in available_types
                )
                for filename in filenames:
                    (platform_dir / filename).write_bytes(b"spec")
                spec_list = self.output_dir / f"input_priority_{index}.txt"
                spec_list.write_text("\n".join(filenames), encoding="utf-8")

                selected = generate_spec.select_component_spec_files(
                    "PriorityComponent.pdf",
                    "adaptive",
                    spec_list_path=spec_list,
                    spec_root=spec_root,
                )

                self.assertEqual(selected["primary_types"], expected_priority)

    def test_adaptive_component_package_uses_rs_sws_and_writes_namespace_files(self):
        selected_specs = {
            "exp": (),
            "rs": ("AUTOSAR_AP_RS_CommunicationManagement.pdf",),
            "sws": ("AUTOSAR_AP_SWS_CommunicationManagement.pdf",),
            "tps": (),
            "tr": (),
            "primary_types": ("RS", "SWS"),
        }
        excerpts = {
            "EXP": [SimpleNamespace(citation="EXP source p. 1", text="Communication design concepts")],
            "RS": [SimpleNamespace(citation="RS source p. 2", text="Normative service requirements")],
            "SWS": [SimpleNamespace(citation="SWS source p. 3", text="Software behavior requirements")],
        }
        generated_responses = [
            "EXP analysis grounded in retrieved explanation.",
            "```cpp\n#pragma once\nnamespace ara::com { class CommunicationManagement {}; }\n```",
            "```cpp\n#include \"CommunicationManagement.hpp\"\nvoid run() {}\n```",
        ]
        package_root = self.output_dir / "packages"
        with patch("generate_spec.select_component_spec_files", return_value=selected_specs):
            with patch("generate_spec.AutosarSpecEngine") as engine:
                engine.return_value.index_documents.return_value = SimpleNamespace(errors=())
                engine.return_value.search.side_effect = lambda _query, **kwargs: excerpts[
                    kwargs["document_types"][0]
                ]
                with patch.object(generate_spec, "query_llm", side_effect=generated_responses) as query:
                    generated = generate_spec.generate_component_package(
                        requirement="Implement CommunicationManagement service discovery",
                        component="CommunicationManagement",
                        platform="adaptive",
                        output_dir=package_root,
                    )

        package_dir = package_root / "CommunicationManagement"
        self.assertEqual(set(generated), {"CommunicationManagement.hpp", "CommunicationManagement.cpp"})
        self.assertTrue((package_dir / "CommunicationManagement_requirements_analysis.md").is_file())
        for filename in generated:
            contents = (package_dir / filename).read_text(encoding="utf-8")
            self.assertIn("Affected AUTOSAR specification sources:", contents)
            self.assertIn("RS source p. 2", contents)
            self.assertIn("SWS source p. 3", contents)
        search_calls = engine.return_value.search.call_args_list
        self.assertEqual([call.kwargs["document_types"] for call in search_calls], [("EXP",), ("RS",), ("SWS",)])
        self.assertEqual(search_calls[1].kwargs["sources"], selected_specs["rs"])
        self.assertEqual(search_calls[2].kwargs["sources"], selected_specs["sws"])
        self.assertIn("ara::com", query.call_args_list[1].kwargs["prompt"])

    def test_classic_component_package_writes_app_and_config_files(self):
        selected_specs = {
            "exp": ("AUTOSAR_CP_EXP_CanIf.pdf",),
            "rs": ("AUTOSAR_CP_RS_CanIf.pdf",),
            "sws": ("AUTOSAR_CP_SWS_CanIf.pdf",),
            "tps": (),
            "tr": (),
            "primary_types": ("RS", "SWS"),
        }
        excerpts = {
            "EXP": [SimpleNamespace(citation="CanIf EXP p. 1", text="CanIf concepts")],
            "RS": [SimpleNamespace(citation="CanIf RS p. 2", text="CanIf requirements")],
            "SWS": [SimpleNamespace(citation="CanIf SWS p. 3", text="CanIf software behavior")],
        }
        generated_responses = [
            "EXP analysis.",
            "```c\n#ifndef CANIF_APP_H\n#define CANIF_APP_H\n#endif\n```",
            "```c\n#ifndef CANIF_CFG_H\n#define CANIF_CFG_H\n#endif\n```",
            "```c\n#include \"CanIf_app.h\"\nvoid CanIf_Run(void) {}\n```",
            "```c\n#include \"CanIf_cfg.h\"\nint CanIf_Config = 0;\n```",
        ]
        package_root = self.output_dir / "classic_packages"
        with patch("generate_spec.select_component_spec_files", return_value=selected_specs):
            with patch("generate_spec.AutosarSpecEngine") as engine:
                engine.return_value.index_documents.return_value = SimpleNamespace(errors=())
                engine.return_value.search.side_effect = lambda _query, **kwargs: excerpts[
                    kwargs["document_types"][0]
                ]
                with patch.object(generate_spec, "query_llm", side_effect=generated_responses):
                    generated = generate_spec.generate_component_package(
                        requirement="Implement the CanIf receive runnable",
                        component="CanIf",
                        platform="classic",
                        output_dir=package_root,
                    )

        package_dir = package_root / "CanIf"
        expected_files = {"CanIf_app.c", "CanIf_app.h", "CanIf_cfg.c", "CanIf_cfg.h"}
        self.assertEqual(set(generated), expected_files)
        for filename in expected_files:
            contents = (package_dir / filename).read_text(encoding="utf-8")
            self.assertIn("Affected AUTOSAR specification sources:", contents)
            self.assertIn("CanIf RS p. 2", contents)
            self.assertIn("CanIf SWS p. 3", contents)

    def test_sws_only_package_generates_without_rs(self):
        selected_specs = {
            "exp": (),
            "rs": (),
            "sws": ("AUTOSAR_AP_SWS_Diagnostics.pdf",),
            "tps": (),
            "tr": (),
            "primary_types": ("SWS",),
        }
        excerpts = {
            "EXP": [SimpleNamespace(citation="EXP p. 1", text="Diagnostic concepts")],
            "SWS": [SimpleNamespace(citation="Diagnostics SWS p. 2", text="Diagnostic software requirement")],
        }
        responses = [
            "EXP understanding.",
            "```cpp\n#pragma once\nclass Diagnostics {};\n```",
            "```cpp\n#include \"Diagnostics.hpp\"\nvoid report() {}\n```",
        ]
        with patch("generate_spec.select_component_spec_files", return_value=selected_specs):
            with patch("generate_spec.AutosarSpecEngine") as engine:
                engine.return_value.index_documents.return_value = SimpleNamespace(errors=())
                engine.return_value.search.side_effect = lambda _query, **kwargs: excerpts[
                    kwargs["document_types"][0]
                ]
                with patch.object(generate_spec, "query_llm", side_effect=responses) as query:
                    generated = generate_spec.generate_component_package(
                        requirement="Implement Adaptive Diagnostics reporting",
                        component="Diagnostics",
                        platform="adaptive",
                        output_dir=self.output_dir / "sws_only",
                    )

        self.assertEqual(set(generated), {"Diagnostics.hpp", "Diagnostics.cpp"})
        search_types = [call.kwargs["document_types"] for call in engine.return_value.search.call_args_list]
        self.assertEqual(search_types, [("EXP",), ("SWS",)])
        self.assertIn("highest available component evidence is SWS", query.call_args_list[1].kwargs["prompt"])
        self.assertNotIn("RS source", query.call_args_list[1].kwargs["prompt"])

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