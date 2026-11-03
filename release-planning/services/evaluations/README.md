# Service evaluation fixtures

The fixtures in this directory define inputs and scoring before model runs.
Their IDs, source text, fact expectations, and scoring rules are versioned as
reviewable evaluation data. Do not edit a fixture after observing model output;
make a new fixture version and retain the old results if a correction is needed.

## Grounded answers

`grounded_qa_v1.json` contains 20 questions over four synthetic documents and
20 atomic facts. It defines separate retrieval-only measurements and
generated-answer scoring. Retrieval-only results use returned document
metadata to resolve stable `source_id` values. Generated-answer scoring checks
the expected facts, at least one supporting citation, all citations against sources actually retrieved for that
question, unsupported claims, and quote integrity. A retrieval hit does not
count as a correct generated answer.

The source IDs are stable fixture identities; runtime file paths and database
IDs are setup details. Keep the mapping from runtime metadata to fixture IDs in
the run receipt. Preserve all 20 questions in the denominator and save the
prompt, retrieved source IDs, output, model/tool parameters, and score for every
case.

## Companion memory

`memory_correction_recall_v1.json` contains 10 fixed tool sequences using the
registered names `record_companion_fact`, `recall_companion_facts`,
`update_companion_fact`, `retract_companion_fact`, and
`recall_companion_turns`. Fact IDs and session IDs are captured from setup or
tool outputs; the fixture does not assume globally stable database IDs. Each
scenario runs in a fresh isolated database, except the deliberate repository
reopen within MCR-04. Cross-bot cases create two distinct chatbot IDs.

Scoring requires latest-value recall, correct citation-to-row resolution,
no cross-bot facts or turns, persistence where requested, the documented
unknown response, and retraction behavior. The fixture measures the retained
companion memory tools and repository. It does not score mood or persona policy.

## Evaluation stages

1. Validate fixture schema, IDs, counts, content hashes, and immutable model
   artifact identity before launching an endpoint or model.
2. Run retrieval-only queries against the fixture corpus, recording embedding
   time separately from index search and source resolution. Report
   source-recall@3, source-precision@3, reciprocal rank of the first gold
   source, and query latency for all 20 questions.
3. Run generated answers separately through the authenticated service route
   selected for the release candidate. Capture actual prompts, tool inputs,
   retrieved sources, output tokens, outputs, and endpoint errors.
4. Score generated answers using the frozen atomic facts and citation rules.
   Never infer generated-answer factuality from retrieval scores.
5. Run the 10 companion-memory sequences against the retained registered tool
   APIs and an isolated persistent repository; exercise a close/reopen at
   MCR-04 and verify database row scope for every citation.
6. Keep fixture-set targets from
   `../EVALUATION_TARGETS.md`: at least 19/20 grounded questions and 10/10
   memory scenarios. These are targets, not results. Report each individual
   case and any missing/failed run; do not remove timeouts or errors from the
   denominator.

The current source defines `rag_search`, HTTP routes `POST /api/v1/llm/rag/index`,
`POST /api/v1/llm/rag/reindex`, `POST /api/v1/llm/rag/index/cancel`, and
`GET /api/v1/llm/rag/index/status`. Generic document deletion is exposed at
`DELETE /api/v1/library/resources/Document/{record_id}` and
`POST /api/v1/library/resources/Document/delete`. The memory cases use the five
registered companion tools listed above. Resolve and record the exact normal
authenticated answer route and request schema against the selected service
release before generated-answer runs; direct component or tool calls are
diagnostic evidence, not authenticated-service acceptance.

`e5_latency_100_chunks_v1.json` fixes 100 synthetic chunk texts with SHA-256
identities and 30 query inputs for a separate latency workload. Assert exactly
100 indexed chunks and record actual query token counts before timing. Record
embedding, search and end-to-end time, all failures, and the runtime identity.
The fixture is unrun and does not establish general retrieval quality. Keep it
separate from the 20 grounded-answer questions and their relevance labels.
