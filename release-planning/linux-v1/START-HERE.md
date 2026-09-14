# Start here

The authoritative remote entry point is https://github.com/Capsize-Games/airunner/issues/2083 . Every child includes its own scope, prerequisites and checks; do not paste the entire audit into a small-model session.

First session: https://github.com/Capsize-Games/airunner/issues/2085 (R03, docs-only guidance repair). The owner authorized exactly one GPT-5.3-Codex-Spark session. No automatic queue is enabled.

Other initial ready work:

- Desktop feature inventory R01: https://github.com/Capsize-Games/airunner/issues/2084
- UwUchat reference inventory W01: https://github.com/Capsize-Games/airunnerweb/issues/216
- Isolated web test database W02: https://github.com/Capsize-Games/airunnerweb/issues/217

After R03 review, the WebSocket authentication fix S01 and launcher resource fix P01 can proceed in separate sessions; check each prerequisite first. Do not parallelize changes touching the same source files.

Recommended model use: Spark for one small bounded change using its separate finite allowance; GPT-5.6 Luna is an alternative for economical routine work using ordinary allowance. Never automatically escalate models. Security, migrations and legal/policy changes need appropriate review regardless of the implementation model.

Use AGENT-HANDOFF.md as the prompt. README.md indexes every issue; github-receipts.json records the actual issue numbers. issues/ contains the filed bodies. The generator/publisher scripts are maintenance tools, not commands for implementation agents to rerun. No source commit or public release is implied by this handoff.
