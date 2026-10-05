import sys
from types import SimpleNamespace

from autosar_spec_engine import AutosarSpecEngine


class FakePage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


class FakePdfReader:
    def __init__(self, _path):
        self.is_encrypted = False
        self.pages = [
            FakePage(
                "CanIf controller configuration defines the CAN controller "
                "and channel references for Classic Platform."
            ),
            FakePage("A separate page describes unrelated diagnostic behavior."),
        ]


def test_indexes_searches_and_cites_pdf_page(tmp_path, monkeypatch):
    spec_root = tmp_path / "autosar_spec"
    pdf_dir = spec_root / "classic_autosar_R25_11"
    pdf_dir.mkdir(parents=True)
    pdf_path = pdf_dir / "AUTOSAR_CP_SWS_CANInterface.pdf"
    pdf_path.write_bytes(b"fake pdf")
    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakePdfReader))

    engine = AutosarSpecEngine(spec_root=spec_root)
    results = engine.search("CanIf controller", platform="classic", top_k=3)

    assert len(results) == 1
    assert results[0].page == 1
    assert results[0].platform == "classic"
    assert results[0].release == "R25_11"
    assert results[0].source == "classic_autosar_R25_11/AUTOSAR_CP_SWS_CANInterface.pdf"

    context = engine.build_context("CanIf controller", platform="CP")
    assert "AUTOSAR Classic Platform R25_11" in context
    assert "p. 1" in context

    report = engine.index_documents()
    assert report.pdfs_unchanged == 1
    assert report.pdfs_indexed == 0


def test_search_returns_empty_for_unmatched_platform(tmp_path, monkeypatch):
    spec_root = tmp_path / "autosar_spec"
    pdf_dir = spec_root / "classic_autosar_R25_11"
    pdf_dir.mkdir(parents=True)
    (pdf_dir / "spec.pdf").write_bytes(b"fake pdf")
    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakePdfReader))

    engine = AutosarSpecEngine(spec_root=spec_root)

    assert engine.search("CanIf controller", platform="adaptive") == []
