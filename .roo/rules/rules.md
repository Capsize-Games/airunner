## Workspace-wide rules (apply to every mode)

These load for every mode regardless of slug. Mode-specific rules
(`.roo/rules-<slug>/`) supplement this, they don't replace it.

## Host System Boundaries

**NEVER modify host system settings.** This includes (but is not
limited to):

- Firewall rules (iptables, nftables, ufw)
- Network configuration (interfaces, routing tables, /etc/hosts)
- System packages (apt, pip on the host outside `venv`)
- Docker daemon configuration
- VPN settings (Mullvad, WireGuard, etc.)
- **Any file outside `~/Projects/airunnerdesktop/`** — this includes
  where git worktrees get created. A worktree living in a sibling
  directory outside this repo causes Zoo Code's file-edit tools (which
  gate on workspace root) to stall on every operation against anything
  outside it. Worktrees belong under `.worktrees/` inside this repo
  (already gitignored) — never as a sibling directory.
- **`/tmp` or any other system-wide temp directory.** Same problem in a
  different disguise: `/tmp` is outside the repo, so writing there
  triggers the same manual-approval gate and breaks automated flows.
  Use `tmp/` at the repo root instead (already gitignored, already
  inside the workspace, needs no approval). If you catch yourself about
  to write to `/tmp`, write to `tmp/` instead.

Connectivity or environment problems are the human's to diagnose. If a
dev server or GPU backend is unreachable, report the symptoms and
stop — do not attempt to fix the host's networking, drivers, or
firewall.

## Environment

This is a Python desktop app developed against a local virtualenv
(`./venv`, set up via `scripts/install.sh`), not a Docker-only stack —
Docker is one supported run path (`docker-compose.yml`), not the only
one. Prefer running Python/tests inside the repo's own `venv` (`source
venv/bin/activate` or `venv/bin/python`/`venv/bin/pytest` directly)
rather than the host's system Python. Don't assume a GPU or display is
available in a headless/CI context — GUI-dependent code paths
(`gui_probe.py`, PyQt windows) may need `--headless` or an offscreen
Qt platform plugin; check `scripts/run.sh` and `README.md` for the
actual invocation before assuming.

## Security and Privacy

- Never log prompts, conversation bodies, transcriptions, tool
  payloads, API responses, filesystem paths, tokens, secrets, or other
  user content unless explicitly asked. Log counts, sizes, IDs, hashes,
  timing, and state transitions — not raw content.
- Validate all user-controlled local paths before use; never traverse
  outside the app's configured base/data directory.
- Never commit or hardcode API keys, tokens, or credentials — use
  `.env`/environment variables (see `.env.example`).

## Committing

- Never use `--no-verify` or skip a failing pre-commit hook unless
  explicitly instructed.
- Never force-push, never `git reset --hard`/`git clean` without
  checking what's actually there first (`git status` before anything
  that could discard uncommitted work).

## Prefer scripts over repeated manual/LLM work

The `scripts/` directory exists for exactly this: if you find yourself
about to do the same multi-step shell/verification/analysis sequence
more than once or twice in a session (a boot check, a baseline test
run, a log-diagnosis routine, a repeated grep-and-check pattern), write
it as a script under `scripts/` instead of re-deriving and re-running
it by hand or by LLM reasoning each time. A script is deterministic,
fast, cheap, and reviewable; redoing the same analysis from scratch
every time is slow, costs tokens, and risks drifting slightly each
time you do it. Check `scripts/` first for something that already does
what you need before reasoning through it yourself; if nothing fits,
consider whether what you're about to do is worth scripting for next
time, not just this once.
