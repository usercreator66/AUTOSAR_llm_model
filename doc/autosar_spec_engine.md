# `autosar_spec_engine.py`

[Open source](../autosar_spec_engine.py)

## Purpose

Indexes local Classic and Adaptive AUTOSAR specification PDFs and retrieves cited evidence for generation prompts. It uses SQLite FTS5 for full-text search, not model fine-tuning.

## Main API

- `AutosarSpecEngine.index_documents()` incrementally extracts pages from new or changed PDFs and stores document metadata and text chunks.
- `AutosarSpecEngine.search(query, platform, top_k, document_types, sources, refresh_index)` returns matching excerpts with platform, release, source, page, and score. `document_types` filters filename families such as `EXP`, `RS`, or `SWS`; `sources` restricts retrieval to selected list entries.
- `AutosarSpecEngine.build_context(...)` formats ranked excerpts and citations for a model prompt and forwards the same retrieval filters.
- `SpecExcerpt` and `IndexReport` represent search results and indexing summaries.

## Data and commands

The default source root is `autosar_spec/`; the database is `autosar_spec/.autosar_spec_index.sqlite3`. Component generation indexes the PDFs once, then queries this database separately for EXP, RS, and SWS evidence. PDF text extraction requires `pypdf`.

```powershell
python autosar_spec_engine.py "CanIf controller" --platform classic
python autosar_spec_engine.py "CanIf controller" --reindex
```