"""Local retrieval over AUTOSAR Classic and Adaptive specification PDFs."""

from __future__ import annotations

import argparse
import logging
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:-]*")
_RELEASE_PATTERN = re.compile(r"R\d{2}_\d{2}", re.IGNORECASE)


@dataclass(frozen=True)
class SpecExcerpt:
    """A retrieved specification excerpt with a stable document citation."""

    source: str
    platform: str
    release: str
    page: int
    text: str
    score: float

    @property
    def citation(self) -> str:
        return f"AUTOSAR {self.platform.title()} Platform {self.release}, {self.source}, p. {self.page}"


@dataclass(frozen=True)
class IndexReport:
    """Summary of one local specification-indexing pass."""

    pdfs_seen: int
    pdfs_indexed: int
    pdfs_unchanged: int
    pages_indexed: int
    chunks_indexed: int
    errors: tuple[str, ...]


class AutosarSpecEngine:
    """Incrementally index local AUTOSAR PDFs and retrieve cited evidence."""

    def __init__(
        self,
        spec_root: Optional[str | Path] = None,
        index_path: Optional[str | Path] = None,
        chunk_chars: int = 1800,
        overlap_chars: int = 240,
    ) -> None:
        self.spec_root = Path(spec_root) if spec_root else Path(__file__).parent / "autosar_spec"
        self.spec_root = self.spec_root.expanduser().resolve()
        self.index_path = (
            Path(index_path).expanduser().resolve()
            if index_path
            else self.spec_root / ".autosar_spec_index.sqlite3"
        )
        self.chunk_chars = max(int(chunk_chars), 400)
        self.overlap_chars = min(max(int(overlap_chars), 0), self.chunk_chars // 2)

    def _connect(self) -> sqlite3.Connection:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.index_path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            "CREATE TABLE IF NOT EXISTS documents ("
            "file_path TEXT PRIMARY KEY, platform TEXT NOT NULL, release TEXT NOT NULL, "
            "mtime_ns INTEGER NOT NULL, size_bytes INTEGER NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS chunks ("
            "id INTEGER PRIMARY KEY, file_path TEXT NOT NULL, page INTEGER NOT NULL, "
            "chunk_index INTEGER NOT NULL, text TEXT NOT NULL, "
            "UNIQUE(file_path, page, chunk_index))"
        )
        connection.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS spec_fts USING fts5(text)"
        )
        return connection

    @staticmethod
    def _classify_document(path: Path) -> tuple[str, str]:
        normalized_parts = [part.lower() for part in path.parts]
        if any("adaptive_autosar" in part for part in normalized_parts):
            platform = "adaptive"
        elif any("classic_autosar" in part for part in normalized_parts):
            platform = "classic"
        else:
            platform = "unknown"

        release_match = next(
            (match for part in path.parts if (match := _RELEASE_PATTERN.search(part))),
            None,
        )
        return platform, release_match.group(0).upper() if release_match else "unknown"

    def _split_page(self, text: str) -> list[str]:
        text = re.sub(r"[ \t]+\n", "\n", text).strip()
        if not text:
            return []

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_chars, len(text))
            if end < len(text):
                boundary = max(
                    text.rfind("\n", start + self.chunk_chars // 2, end),
                    text.rfind(" ", start + self.chunk_chars // 2, end),
                )
                if boundary > start:
                    end = boundary
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = max(end - self.overlap_chars, start + 1)
            while start < len(text) and text[start].isspace():
                start += 1
        return chunks

    def index_documents(self, force: bool = False) -> IndexReport:
        """Index new or changed PDFs; unchanged files are not re-extracted."""
        if not self.spec_root.is_dir():
            raise FileNotFoundError(f"AUTOSAR specification directory not found: {self.spec_root}")
        pdf_paths = sorted(path for path in self.spec_root.rglob("*.pdf") if path.is_file())
        if not pdf_paths:
            raise FileNotFoundError(f"No PDF specifications found under: {self.spec_root}")

        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF indexing requires pypdf. Install it with: pip install pypdf") from exc
        logging.getLogger("pypdf").setLevel(logging.ERROR)

        pages_indexed = 0
        chunks_indexed = 0
        pdfs_indexed = 0
        pdfs_unchanged = 0
        errors = []
        live_paths = {str(path.resolve()) for path in pdf_paths}

        with self._connect() as connection:
            for path in pdf_paths:
                absolute_path = str(path.resolve())
                stat = path.stat()
                previous = connection.execute(
                    "SELECT mtime_ns, size_bytes FROM documents WHERE file_path = ?",
                    (absolute_path,),
                ).fetchone()
                if (
                    not force
                    and previous
                    and previous["mtime_ns"] == stat.st_mtime_ns
                    and previous["size_bytes"] == stat.st_size
                ):
                    pdfs_unchanged += 1
                    continue

                try:
                    reader = PdfReader(absolute_path)
                    if reader.is_encrypted and not reader.decrypt(""):
                        raise ValueError("encrypted PDF requires a password")
                    extracted_pages = [
                        (page_number, page.extract_text() or "")
                        for page_number, page in enumerate(reader.pages, start=1)
                    ]
                except Exception as exc:
                    errors.append(f"{path.relative_to(self.spec_root)}: {exc}")
                    continue

                connection.execute(
                    "DELETE FROM spec_fts WHERE rowid IN "
                    "(SELECT id FROM chunks WHERE file_path = ?)",
                    (absolute_path,),
                )
                connection.execute("DELETE FROM chunks WHERE file_path = ?", (absolute_path,))
                platform, release = self._classify_document(path)
                connection.execute(
                    "INSERT OR REPLACE INTO documents "
                    "(file_path, platform, release, mtime_ns, size_bytes) VALUES (?, ?, ?, ?, ?)",
                    (absolute_path, platform, release, stat.st_mtime_ns, stat.st_size),
                )

                for page_number, page_text in extracted_pages:
                    page_chunks = self._split_page(page_text)
                    for chunk_number, chunk_text in enumerate(page_chunks, start=1):
                        cursor = connection.execute(
                            "INSERT INTO chunks (file_path, page, chunk_index, text) "
                            "VALUES (?, ?, ?, ?)",
                            (absolute_path, page_number, chunk_number, chunk_text),
                        )
                        connection.execute(
                            "INSERT INTO spec_fts (rowid, text) VALUES (?, ?)",
                            (cursor.lastrowid, chunk_text),
                        )
                        chunks_indexed += 1
                    if page_chunks:
                        pages_indexed += 1
                pdfs_indexed += 1
                connection.commit()

            stale_paths = connection.execute("SELECT file_path FROM documents").fetchall()
            for row in stale_paths:
                if row["file_path"] not in live_paths:
                    connection.execute(
                        "DELETE FROM spec_fts WHERE rowid IN "
                        "(SELECT id FROM chunks WHERE file_path = ?)",
                        (row["file_path"],),
                    )
                    connection.execute("DELETE FROM chunks WHERE file_path = ?", (row["file_path"],))
                    connection.execute("DELETE FROM documents WHERE file_path = ?", (row["file_path"],))

        return IndexReport(
            pdfs_seen=len(pdf_paths),
            pdfs_indexed=pdfs_indexed,
            pdfs_unchanged=pdfs_unchanged,
            pages_indexed=pages_indexed,
            chunks_indexed=chunks_indexed,
            errors=tuple(errors),
        )

    @staticmethod
    def _make_fts_query(query: str) -> str:
        terms = list(dict.fromkeys(_TOKEN_PATTERN.findall(query)))[:32]
        if not terms:
            raise ValueError("Search query must contain at least one searchable term.")
        return " OR ".join(f'"{term}"' for term in terms)

    def search(
        self,
        query: str,
        platform: Optional[str] = None,
        top_k: int = 5,
    ) -> list[SpecExcerpt]:
        """Return the best matching excerpts, with optional Classic/Adaptive filter."""
        report = self.index_documents()
        if report.errors:
            print(f"[AUTOSAR spec index] {len(report.errors)} PDF(s) could not be indexed.")

        if platform:
            platform = platform.strip().lower()
            aliases = {"ap": "adaptive", "adaptive platform": "adaptive", "cp": "classic", "classic platform": "classic"}
            platform = aliases.get(platform, platform)
            if platform not in {"classic", "adaptive"}:
                raise ValueError("platform must be 'classic', 'adaptive', or None")

        fts_query = self._make_fts_query(query)
        limit = min(max(int(top_k), 1), 30)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT chunks.file_path, documents.platform, documents.release, "
                "chunks.page, chunks.text, bm25(spec_fts) AS rank "
                "FROM spec_fts "
                "JOIN chunks ON chunks.id = spec_fts.rowid "
                "JOIN documents ON documents.file_path = chunks.file_path "
                "WHERE spec_fts MATCH ? AND (? IS NULL OR documents.platform = ?) "
                "ORDER BY rank LIMIT ?",
                (fts_query, platform, platform, limit),
            ).fetchall()

        excerpts = []
        for row in rows:
            source = Path(row["file_path"]).relative_to(self.spec_root).as_posix()
            excerpts.append(
                SpecExcerpt(
                    source=source,
                    platform=row["platform"],
                    release=row["release"],
                    page=row["page"],
                    text=row["text"],
                    score=-float(row["rank"]),
                )
            )
        return excerpts

    def build_context(
        self,
        query: str,
        platform: Optional[str] = None,
        top_k: int = 5,
        max_chars: int = 10000,
    ) -> str:
        """Format retrieved excerpts for a model prompt with source citations."""
        excerpts = self.search(query, platform=platform, top_k=top_k)
        if not excerpts:
            return "No matching AUTOSAR specification excerpts were found. Do not invent normative requirements."

        limit = max(int(max_chars), 1)
        sections = [
            "Retrieved AUTOSAR specification evidence. Treat these excerpts as source material, "
            "cite document and page for normative claims, and state when evidence is insufficient."
        ]
        used_chars = len(sections[0])
        for excerpt in excerpts:
            section = f"\n\n[{excerpt.citation}]\n{excerpt.text}"
            remaining = limit - used_chars
            if remaining <= 0:
                break
            if len(section) > remaining:
                section = section[:remaining].rsplit(" ", 1)[0].rstrip() + " ..."
            sections.append(section)
            used_chars += len(section)
            if used_chars >= limit:
                break
        return "".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search local AUTOSAR R25-11 specification PDFs.")
    parser.add_argument("query", nargs="+", help="Terms or requirement to find in the specifications")
    parser.add_argument("--root", type=Path, help="Specification directory (default: ./autosar_spec)")
    parser.add_argument("--platform", choices=("classic", "adaptive"), help="Limit search to one platform")
    parser.add_argument("--top-k", type=int, default=5, help="Maximum matching excerpts")
    parser.add_argument("--reindex", action="store_true", help="Re-extract all PDFs and rebuild their index")
    args = parser.parse_args()

    engine = AutosarSpecEngine(spec_root=args.root)
    report = engine.index_documents(force=args.reindex)
    print(
        f"Indexed {report.pdfs_indexed} PDF(s); {report.pdfs_unchanged} unchanged; "
        f"{report.chunks_indexed} text chunks added."
    )
    for error in report.errors:
        print(f"[WARNING] {error}")

    excerpts = engine.search(" ".join(args.query), platform=args.platform, top_k=args.top_k)
    if not excerpts:
        print("No matching excerpts found.")
        return
    for excerpt in excerpts:
        print(f"\n[{excerpt.citation}]\n{excerpt.text}")


if __name__ == "__main__":
    main()
