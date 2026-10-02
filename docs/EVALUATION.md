# Evaluation design, results and critique

40 frozen questions: ten each for requirements, deadlines, submission information and concepts. Each was run in Raw and RAG conditions (80 saved outputs), with the same generator/settings but different prompts and evidence access. The public aggregate JSON files are in `results/formal/`; exact questions, outputs and review records are provided via the LMS CODE attachment.

| Scoring interpretation | Raw | RAG |
|---|---:|---:|
| Historical provisional answer score | 9/40 | 30/40 |
| Post-hoc strict completeness | 3/40 | 23/40 |
| Page-citation support | 0/40 | 29/40 |
| Complete AND page-supported | 0/40 | 22/40 |

Strict completeness requires every frozen required fact. Citation support evaluates the cited page/document, not necessarily the exact retrieved passage. The two views reinterpret the same outputs; the stricter audit is not a new model run or preregistered replacement. **Both are AI-assisted; the later audit is unblinded and not human-validated.** There is no human reference set for judge precision/recall.

Strict completeness by category (Raw/RAG, each out of 10): requirements 1/9; deadlines 0/3; submission information 0/5; concepts 2/6. Deadlines are the weakest RAG category. Some required facts demand more than the question wording, so incompleteness is not necessarily factual error. Raw has no course sources, making its zero course-citation count expected. Structured abstention flags differ from prose: Raw 28 flags versus 26 textual withholdings, RAG 0 versus 1; missing-information yes/no answers complicate interpretation.

## Cost and latency

Raw input/output tokens: 5,401/2,067; RAG: 41,596/2,827. Recorded per-million token prices were $0.15 input and $0.60 output. Forty-call totals: $0.00205035 Raw and $0.0079356 RAG. Scaling observed average usage to 1,000 questions yields $0.05125875 and $0.19839, about 3.87 times as much for RAG. This excludes local embedding, hosting, maintenance and review and is not a current-price quote.

Mean API request times were 1.5428383 and 1.5025675 seconds. Retrieval and browser overhead are excluded; no speed advantage or statistical generalisation is established.

## Limits and replication

One course, one generation model, small overlapping development/formal samples, no independent human review or user study. Different prompts confound retrieval effects. Source/page retrieval hits do not prove passage-level sufficiency. Later confirmation of a fact does not repair a wrong historical citation.

The public export has aggregate evidence only. For score/cost recomputation and file-integrity checks, follow [RUN_MARKER.md](RUN_MARKER.md) with both LMS packages. Those checks validate recorded arithmetic and integrity, not semantic truth. New generation would require separate authorised paid requests and must not overwrite the historical files.
