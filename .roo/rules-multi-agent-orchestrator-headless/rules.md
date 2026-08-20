## Relationship to workspace-wide rules

`.roo/rules/rules.md` (workspace-wide, all modes) already covers host
boundaries, migration/multi-tenant rules, security/logging, and
committing basics — read it, it applies here too. This file only
covers what's specific to the headless orchestrator path.

## What this actually is

`scripts/headlesscode-orchestrate.sh` delegates to a separate project
(`~/Projects/headlesscode`, override with `HEADLESSCODE_ROOT`) that
vendors the split/spawn/review machinery this pipeline uses — this repo
has no GUI-based (xdotool) orchestrator mode of its own, this headless
path is the only one. Worker sessions still open real PRs and comment/
close real issues themselves — the orchestrator layer only splits,
spawns, watches, reviews, optionally QAs, and optionally deploy-gates.
The reviewer checklist lives in `${HEADLESSCODE_ROOT:-~/Projects/headlesscode}/plans/review-mode-prompt.md`.

## Requirements

- `HEADLESSCODE_OPENROUTER_API_KEY` must be live — the wrapper script
  reads it out of the headlesscode checkout's own `.env` automatically
  (this repo has no OpenRouter key of its own) and re-exports it, the
  name headlesscode's own `process.env` lookup expects (headlesscode
  does not read `.env` files itself). Workers, the reviewer, and QA all
  run against OpenRouter, not against whatever model/provider is
  configured for Zoo Code itself.
- `~/Projects/headlesscode` must exist and be runnable (`node >= 18`).
  If it's been moved, set `HEADLESSCODE_ROOT` before calling the
  wrapper script.
- The systemwide `headlesscode` command should be installed and on
  `PATH` — run `<HEADLESSCODE_ROOT>/scripts/install-cli.sh` once, or
  after the checkout moves. `scripts/headlesscode-orchestrate.sh` uses
  it automatically when present and otherwise falls back to invoking
  the checkout's own `tsx` via `HEADLESSCODE_ROOT`; the `checkpoints`/
  `dashboard`/`orchestrate status` examples below assume it's on
  `PATH`.

## Running more than one round at once

Don't start a second round against issue numbers already in flight in
an active `.orchestrator-state.json` — they'll race on the same
worktree names (`w1`, `w2`, ...). Check `git worktree list` and
`.orchestrator-state.json` before starting a round.

## Failure modes specific to this path

- A worker that never produces a `.harness.done/` marker under
  `.worktrees/<name>/` is still running or crashed without recording
  an exit code — check `.worktrees/<name>/harness.log` and
  `.worktrees/<name>/.harness.pid` (`kill -0 <pid>` to check liveness)
  before concluding it's stuck.
- `headlesscode orchestrate` aborts outright (no partial run) if the
  global concurrent-session cap is already reached
  (`HEADLESSCODE_MAX_CONCURRENT_SESSIONS`, default 3) — this is a
  deliberate guardrail, not a bug; wait for the existing round to
  finish rather than raising the cap to force it through.

## A worker hitting max-iterations is NOT a reason to destroy its worktree

**Real incident, 2026-08-02**: two workers failed with "Max iterations (50)
reached without task completion" — both plan docs needed substantial file
exploration before their first edit, a documented cost-cheap cause
(`run-worker.sh`'s own comment: "default 50 — often too low for a
multi-phase plan doc that needs substantial file exploration before its
first edit"). The response was `git worktree remove --force` +
`git branch -D` on both, then a fresh respawn. This time nothing committed
was lost (both branches were still at the same commit as master — no real
edits had landed yet), but that was luck, not a property of the fix. If a
worker had made real uncommitted progress before hitting the cap, this
would have destroyed it.

**When a group fails on `max iterations reached without task completion`
(or any other config-tunable resource cap — duration, cost)**: the default
response is to raise the relevant cap
(`HEADLESSCODE_MAX_ITERATIONS`/`--max-iterations`,
`HEADLESSCODE_MAX_COST_USD`, etc.) and **resume the SAME worktree/branch**,
not delete it and start over. The worktree already has whatever real
progress the worker made, plus its checkpoint history — a fresh worker in
a fresh worktree repeats the same exploration from zero, at the same or
higher cost, with no guarantee it won't just hit the same wall again.
Destroying a worktree instead of resuming it is only correct when the
worktree is confirmed to have no salvageable progress (e.g. genuinely at
the same commit as its base, as verified by `git log`/`git diff` against
master — not assumed), or when the human explicitly asks for a clean
restart.

## Checkpoints (worker-side revert)

Each worker now auto-commits a shadow-git checkpoint (not a real commit in
this repo, and not visible to `git status` here) before it starts and
after every tool-executing turn. If a worker's edits go badly wrong,
don't try to hand-fix it — from a shell, run:

```
headlesscode checkpoints --workspace <repo>/.worktrees/<name> list
headlesscode checkpoints --workspace <repo>/.worktrees/<name> restore <hash>
```

(`headlesscode` is a systemwide command wrapping the
`<HEADLESSCODE_ROOT>` checkout — see
`<HEADLESSCODE_ROOT>/scripts/install-cli.sh` if it's missing from
`PATH`; it can be run from anywhere, `--workspace` resolves relative to
wherever you invoke it from)

to revert that worktree's real files to an earlier point. See
`<HEADLESSCODE_ROOT>/docs/checkpoints.md` for details.

## Blocked groups — a worker needs a decision from YOU

Unlike the GUI mode, a headless worker cannot pop up a multiple-choice
question. When one calls its equivalent of `ask_followup_question`, it
writes a marker and then blocks/polls for up to ~30 minutes (configurable)
before giving up and guessing on its own. During that window, the group's
status in `.orchestrator-state.json` is `"blocked"` with the question text
attached (`group.blocked.question`) — this is NOT the same as stalled or
failed.

**For long/unattended rounds, launch the orchestrator detached instead of
blocking your own turn on it**, the same way `run-worker.sh` launches
workers:

```
nohup bash scripts/headlesscode-orchestrate.sh --issue <n1> --issue <n2> ... \
  > .worktrees/.orchestrate-round.log 2>&1 &
```

Then wait on it with ONE command instead of hand-rolling a poll loop
over the state file / `harness.log`:

```
headlesscode orchestrate status --repo <this-repo-root> --wait [--timeout-ms <n>]
```

(run from anywhere — `--repo` still needs this repo's absolute path
since `headlesscode` may be invoked from outside it, e.g. from
`<HEADLESSCODE_ROOT>` or a worktree)

`--wait` blocks inside the single call until every group is terminal
(`done` / `failed` / `needs-human` — `blocked` is deliberately NOT
terminal, so a blocked group keeps the wait running), prints the
per-group summary plus a one-line verdict, and exits 0 only when every
group is done (non-zero = failed / needs-human / timed out). `--json`
gives the same with top-level `allDone` / `timedOut` / `verdict` fields.
While you're actively monitoring, bound the wait with a modest
`--timeout-ms` (e.g. 30–60 minutes) so you wake periodically and can
answer blocked questions instead of letting them sit; the default (2h)
is right for truly unattended waits. When the wait returns, check the
verdict and summary for any `"blocked"` group and resolve it as follows:

1. Read the question and the worker's `.worktrees/<name>/harness.log` for
   context — don't answer blind.
2. If you're confident, decide it yourself.
3. If it's genuinely ambiguous, ask the human directly — you have a real
   `ask_followup_question` with multiple-choice UI available to yourself
   even though the worker doesn't; use it.
4. Unblock the worker:
   ```
   bash <HEADLESSCODE_ROOT>/scripts/headlesscode-answer.sh \
     .worktrees/<name> "<your answer text>"
   ```
   The worker picks this up within its poll interval (a few seconds) and
   continues with your answer as real input, not a guess.

Don't let a blocked group sit past its timeout unanswered if you're
actively monitoring the round — that's exactly the case this exists to
avoid (a worker silently falling back to guessing on something it
explicitly flagged as needing a human).

## Cost/token monitoring

Every session (worker, reviewer, QA) now writes a usage record to
`.headlesscode/usage/<session-id>.jsonl` in its own worktree, and
`headlesscode orchestrate`'s watcher rolls per-group and round-total cost
into `.orchestrator-state.json` (`group.usage`, top-level `totalUsage`) as
groups finish — read the state file directly for a quick total, or run:

```
headlesscode dashboard --repo <this-repo-root>
```

and open the printed localhost URL for a live-refreshing view across all
worktrees in this repo (sessions, per-round totals, and any currently
blocked groups). Local-only, read-only, no auth — don't expose the port
beyond localhost.
