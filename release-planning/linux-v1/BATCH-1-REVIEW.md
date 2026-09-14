# Batch 1 review — 2026-09-13

No changes merged. Static review only; no GUI, model, live database or runtime tests launched. Spark five-hour usage reached 100%; reset reported at 2026-09-13 13:37 America/Denver. Do not switch models automatically.

## R03 — airunner PR 2152, b334abc5f5b456a7701f35bce32c3e7dd698b8d8

Verified replacement files exist and `git diff master --check` passes. Single documentation file changed. One clarification before acceptance: `.github/copilot-instructions.md:9` calls authorized regression additions “documentation-scoped test additions/changes”. These tickets authorize actual regression test code. Replace that sentence with: “Regression tests explicitly required by the assigned release issue are authorized additions/changes within that issue's scope.” Push same PR; no runtime checks needed.

## R01 — desktop feature matrix, no PR

Not acceptance-ready. Two cited source paths do not exist: `src/airunner/components/art/gui/widgets/canvas/canvas_generation_mixin.py` and `src/airunner/components/llm/gui/widgets/chat_prompt_widget.py`. The issue link uses the wrong organization/repository. Matrix has no stable feature IDs despite claiming they exist in its notes. Does not classify every row as local/network-optional/unsupported hardware. Checkmarked “deterministic coverage” mostly states possible API checks rather than naming existing tests or concrete proposed scenarios; art inference is not itself a deterministic contract check. Correct anchors, give stable IDs and explicit scenarios/evidence status, and map proposed followups to existing tickets before suggesting duplicates. Commit only matrix and open draft PR as already authorized.

## W01 — UwUchat reference, no PR

Not acceptance-ready. Claims verified artifacts that do not exist at the reference checkout: `server/src/airunner_services/memory_updater.py`, `server/src/airunner_services/episodic_summarizer.py`, `projects/uwuchat/server/routes/rpc_chatbot_profile.py`, `projects/uwuchat/server/routes/rpc_chatbot_status.py`, and `server/src/airunner_services/tests/unit/test_cheap_stage_fallback_logging.py`. Locate true sources or mark unverified/remove claims; do not merely rename guessed paths. No capability-to-Desktop-port-issue mapping. Missing neutral test IDs/scenarios for memory and narrative behaviors. Original checkout has relevant uncommitted local dialogue changes; document exact divergence read-only and identify the owner decision without copying private prompt content. Revalidate every claimed source anchor and behavior against the pinned commit. Commit only reference document and open draft PR.

## W02 — test DB guard, commit 3d5e8837df6916dc2a1e648feda329b424f923cf, no PR

Blocking findings from code review:

1. All four new tests call the decorated `conftest_module._db(monkeypatch)` directly. Pytest forbids direct fixture calls; use fixture injection or an undecorated helper with the side effects replaced by doubles. Ensure tests actually reach the guard.
2. `_normalize_db_url` compares full URL identity, including username, driver spelling and query options, and does not normalize omitted port to 5432. Different users, psycopg/psycopg2 drivers, omitted/default ports or benign connection options can refer to the SAME database yet pass the guard. Compare conservative backend/host/port/database target identity independent of credentials; handle query host/port/database overrides conservatively (reject ambiguous forms if needed). Add cases with doubles for each bypass.
3. `drivername.startswith('postgres')` and missing database components permit malformed/incomplete targets. Require supported PostgreSQL schemes and explicit target identity; make parse failures consistent without echoing URLs/credentials. SQLAlchemy malformed URLs can raise ArgumentError, which is not handled by the ValueError catch.

Worker's Docker check failed on placeholder image `ghcr.io/<your-org>/airunner:latest`; tests are NOT verified. Find an existing safe isolated test image/config if available; do not launch production dependencies or connect to a DB. If blocked, retain exact validation limitation in draft PR. Changes must remain limited to the two issue files.

## Resume instructions

After the reported Spark reset, send each existing task only its section above plus its original one-issue/isolated-worktree/no-merge constraints. Keep model Spark. Do not fan out further. If allowance still blocked, back off until the next reported reset rather than repeated retries. Review new heads against these findings; mark acceptance only with evidence.
