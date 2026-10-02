# Product documentation

## Persona, inputs and outputs

Primary persona: a PE6201 student trying to find a requirement, deadline, submission detail or concept across course files. Secondary persona: an instructor/TA inspecting implementation and evidence. One course is the deliberate prototype scope; measured student time savings and adoption have not been established.

Inputs: a freely typed question (1–1,000 characters), an authorised document corpus and generation/retrieval settings. Outputs: side-by-side Raw/RAG text, source labels, token use, generation cost and API request time. Example buttons fill the question box; they do not replace free input. Browser file upload and autonomous assignment submission are not implemented.

## Architecture

![Architecture](architecture.png)

Local ingestion turns 12 PDF/DOCX/TXT files into 149 extracted units and 345 chunks, targeting 700 characters with 100-character overlap. Local embeddings use BAAI/bge-small-en-v1.5; retrieval returns five passages. OpenRouter runs openai/gpt-4o-mini at temperature 0, output cap 350 tokens. Raw runs first without passages; RAG then runs with retrieved passages and a different prompt. The HTML page also loads historical aggregate results separately from live answers.

Citation-label membership is checked, but semantic support is not enforced. Source originals remain local; selected passages leave the machine on a deliberate live RAG call. A first retrieval may download embedding model weights. The local HTTP server is not a public production service.

## Targets and achievements

The initial 20-question/90% target was superseded by a 40-question comparison reported as counts, including a Raw baseline. No replacement numeric acceptance threshold was pre-registered. Achieved results are in the [evaluation document](EVALUATION.md) and repository homepage; observed scores must not be retroactively called targets.

The intended improvement is more source-grounded answers than an ungrounded baseline. RAG has higher observed completeness/citation counts in this experiment, but the study does not demonstrate superiority over other source-grounded products, causal retrieval effects or user time savings.

## Tuning, rough edges and future work

Development retrieval used 12 questions: BM25 with 1,200-character chunks found the expected source/page in 10/12 at top five, versus 11/12 for semantic retrieval with 700-character chunks. Because both retrieval and chunking changed, the improvement cannot be attributed to embeddings alone. Page-level hits can miss the specific required passage. Development questions overlap semantically with formal questions.

Missing facts, unsupported attributions and conflicts remain possible. Enforced refusal, semantic citation verification, source-conflict resolution, adversarial testing and independent human assessment are future work, not implemented achievements. Official course announcements remain authoritative.
