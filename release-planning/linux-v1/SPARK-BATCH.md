# Spark batch 1 — 2026-09-13

The user expanded authorization from one issue to a bounded parallel batch and requested PR review. Each task uses GPT-5.3-Codex-Spark, low effort, in an isolated worktree. Spark has finite separate usage. No automatic model escalation or additional batches. Reviews consume the coordinating task's ordinary allowance.

| Issue | Task ID | Worktree | Scope |
|---|---|---|---|
| Capsize-Games/airunner#2085 R03 | 01a09b33-3593-7882-8abf-546b09e4db58 | /home/joe/.codex/worktrees/f62b/airunnerdesktop | Agent guidance; initial diff reviewed, clarification and draft PR requested |
| Capsize-Games/airunner#2084 R01 | 01a09b3c-e96d-7892-bdf7-2fab8a21393d | /home/joe/.codex/worktrees/f2c8/airunnerdesktop | Desktop feature inventory |
| Capsize-Games/airunnerweb#216 W01 | 01a09b3d-16cb-7541-8adc-4c472ecbc429 | /home/joe/.codex/worktrees/1133/airunner | UwUchat reference inventory |
| Capsize-Games/airunnerweb#217 W02 | 01a09b3d-41eb-7743-9984-97b03b0228b0 | /home/joe/.codex/worktrees/84c8/airunner | Disposable test database guard |

All tasks may commit their scoped changes and push draft PRs. They may not merge, deploy, close issues, change model, or start other work. Existing source checkouts and user edits must remain untouched. Tests explicitly assigned by issues are authorized, using isolated tooling and doubles; no live database/model/GUI use.

Hourly thread heartbeat `review-airunner-linux-v1-spark-batch` reviews only this batch's new PR head SHAs and sends scoped correction requests to existing tasks. It remains quiet on unchanged state, pauses when all reviews are handed back to the user, and pauses if the ordinary account allowance reaches 10% remaining. It does not launch additional workers. User/counsel safety and legal approval and real hardware acceptance remain human gates.

Task IDs recovered from local session metadata because list_threads omitted newly created tasks, then checked with task tools. Master tracker: https://github.com/Capsize-Games/airunner/issues/2083.
