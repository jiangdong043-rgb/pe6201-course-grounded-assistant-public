# Data explanation and publication boundary

The historical corpus consists of 12 authorised course/project documents, 149 extracted units and 345 text chunks. PDF page metadata is retained; DOCX/TXT page numbers are not reliable. Chunking targets 700 characters with 100-character overlap. The paired cache has 345 vectors with 384 dimensions. Cached vector rows must correspond to the exact chunk file; the implementation checks row count, not corpus identity.

## What is public

- Implementation and configuration (no API key).
- Aggregate counts, categories, token usage, cost and API timing.
- Product, architecture, module, data and evaluation documentation.

## What the marker receives through LMS

- `PE6201_CODE_Jiang_Dong_v2.zip`: frozen 40 test cases, reference facts, 80 outputs, scoring records, full implementation and documentation.
- `PE6201_PRIVATE_DATA_Jiang_Dong_v2.zip`: actual source originals, chunk JSONL, embedding NPZ, source inventory/hashes and portable extraction manifest.
- Final report PDF and face-and-screen demo MP4.

The code and private-data ZIPs have the same `End-of-Course Project` root and are merged by unpacking into the same parent directory. Private data must not be committed to this public repository.

Case records link question/category/reference facts to sources; output records link case/condition to answer, citations, usage and latency; review records preserve original answers and separate scoring interpretations. Detailed original schemas and records are in the CODE attachment, not replaced with fabricated samples here.

The original experiment remains frozen. Later announcements do not retroactively validate historical model attributions. No new experiment or human validation was performed for this public export.
