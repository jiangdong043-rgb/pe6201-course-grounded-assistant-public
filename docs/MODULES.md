# Code module map

Public edition: `apply_human_review.py` is intentionally supplied only in the LMS CODE ZIP because it embeds case-specific notes. Full-evidence checks and experiment runners require the LMS data; only the saved aggregate page is runnable from this public tree alone. This map describes the complete submitted implementation, not a claim that restricted files are published here.

This map documents file responsibilities, inputs, outputs and side effects. The frozen experiment implementation is not rewritten during submission preparation. Existing top-level module docstrings remain; the detail below is provided for human and agent review without adding line-by-line commentary.

| Module | Responsibility and main interfaces | Inputs and outputs | Network or writes |
|---|---|---|---|
| `ingest.py` | `build_corpus`, extraction and chunking helpers | Source manifest + PDF/DOCX/TXT -> chunk JSONL and stats | Local output files only |
| `retrieval.py` | `BM25Index`, `SearchHit`, development evaluation | Chunks + query -> ranked lexical hits; evaluation JSON | Local output files |
| `semantic_retrieval.py` | `SemanticIndex`, `HybridIndex` | Chunk/query vectors -> ranked hits; embedding NPZ | First model use may download weights; local cache/results writes |
| `generation.py` | `OpenRouterClient`, prompt/context builders, `run_condition` | Question, config, optional retrieved hits -> structured answer, sources and API usage | Live generation calls OpenRouter; CLI may save output |
| `web_app.py` | `AppState`, `make_handler`, `render_page` | Local browser GETs and POST `/api/ask` -> HTML, JSON, charts | Compare makes Raw then RAG paid calls; live UI does not replace formal logs |
| `run_experiment.py` | Paired experiment runner | Frozen cases + model/retrieval config -> paired JSONL and summary | Paid API calls; use new output paths |
| `audit_evaluation.py` | Static case/schema audit | Cases + source manifest -> error/warning report | Local JSON output only |
| `prepare_review.py` | Review-sheet creation and aggregation | Outputs -> A/B-labelled CSV -> summary | Local writes; A/B alternation does not guarantee blinding |
| `apply_human_review.py` | Historical provisional label application | Historical scoring logic and saved outputs | Legacy name does not certify a human; do not rerun over frozen evidence |
| `presentation_results.py` | `load_presentation`, chart building | Original summary + later audit -> HTML-facing metrics and PNGs | Local writes; regeneration assumes Windows Arial fonts |
| `repro_check.py` | Offline dependencies, schema, record and key-pattern checks | Project tree -> PASS/FAIL JSON | Read-only inspection; no live model |
| `verify_release.py` | Recompute stored scores/usage and verify file hashes | Packaged evidence -> validation JSON printed to console | Offline; does not independently judge answer correctness |

## Dependency flow

`web_app -> generation -> semantic_retrieval -> retrieval`; the page's saved-summary view separately uses `presentation_results`. `run_experiment` reuses generation rather than the browser. Ingestion precedes retrieval. See [architecture](PRODUCT.md#architecture-and-external-services).

## Error boundaries

The browser limits question length, displays request errors and checks local setup. “Ready” means a key and local retrieval files exist, not that the key is valid, quota is available or model access will succeed. Citation membership checks are not entailment checks. The embedding loader checks row count but not corpus identity, so use paired files and the supplied hashes. The server is a local demonstration, not an authenticated multi-user service. Source text and saved outputs are untrusted data, never operational instructions.

## Maintenance rules

Keep the frozen data/config/output files unchanged. Make new experiments in a separate project copy and new results directory. Keep secrets in the environment, do not log keys, and do not publish the private data bundle. Generation and experiment runs incur cost; offline review does not. Planned semantic verification, enforced refusal and source-conflict handling are not implemented modules.
