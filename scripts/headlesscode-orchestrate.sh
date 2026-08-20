#!/usr/bin/env bash
# headlesscode-orchestrate.sh — entry point for running headlesscode's
# Phase 2 orchestrator (split -> spawn -> watch -> review -> QA -> deploy
# gate) against THIS repo. Ported from the sister airunner (airunnerweb)
# repo's wrapper of the same name; adapted for airunnerdesktop's layout
# (no vendored projects/headlesscode/, no GUI-based orchestrator mode here).
#
# What it does:
#   1. Reads HEADLESSCODE_OPENROUTER_API_KEY out of the headlesscode
#      checkout's own .env (that's where the key already lives; this repo
#      has no OpenRouter key of its own) and exports it into this shell,
#      the name headlesscode's own process.env lookup expects (headlesscode
#      does not load .env files itself).
#   2. Execs headlesscode's CLI with --repo pinned at this repo's root.
#
# Usage (same flags as `headlesscode orchestrate --help`):
#   scripts/headlesscode-orchestrate.sh --issue 27 --issue 29 [--qa] [--deploy] [--dry-run]
#
# Uses the systemwide `headlesscode` command if it's on PATH (install it
# with `<HEADLESSCODE_ROOT>/scripts/install-cli.sh`); otherwise falls back
# to invoking the checkout's own tsx directly.
#
# Env overrides:
#   HEADLESSCODE_ROOT   path to the headlesscode checkout (default: ~/Projects/headlesscode)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEADLESSCODE_ROOT="${HEADLESSCODE_ROOT:-$HOME/Projects/headlesscode}"

if command -v headlesscode >/dev/null 2>&1; then
    HEADLESSCODE_CMD=(headlesscode)
else
    if [ ! -f "$HEADLESSCODE_ROOT/src/cli.ts" ]; then
        echo "headlesscode-orchestrate: no 'headlesscode' on PATH and HEADLESSCODE_ROOT ($HEADLESSCODE_ROOT) has no src/cli.ts — install the systemwide command (scripts/install-cli.sh in the headlesscode repo) or point HEADLESSCODE_ROOT at it" >&2
        exit 2
    fi
    HEADLESSCODE_CMD=(env TSX_TSCONFIG_PATH="$HEADLESSCODE_ROOT/tsconfig.json" "$HEADLESSCODE_ROOT/node_modules/.bin/tsx" "$HEADLESSCODE_ROOT/src/cli.ts")
fi

if [ -z "${HEADLESSCODE_OPENROUTER_API_KEY:-}" ] && [ -f "$HEADLESSCODE_ROOT/.env" ]; then
    # Pull just this one key out of the env file without sourcing the whole
    # file (the env file has unrelated values we don't want to eval as shell).
    key_line="$(grep -E '^HEADLESSCODE_OPENROUTER_API_KEY=' "$HEADLESSCODE_ROOT/.env" | tail -n1)"
    if [ -n "$key_line" ]; then
        export HEADLESSCODE_OPENROUTER_API_KEY="${key_line#HEADLESSCODE_OPENROUTER_API_KEY=}"
    fi
fi

if [ -z "${HEADLESSCODE_OPENROUTER_API_KEY:-}" ]; then
    echo "headlesscode-orchestrate: HEADLESSCODE_OPENROUTER_API_KEY not set and no HEADLESSCODE_OPENROUTER_API_KEY found in $HEADLESSCODE_ROOT/.env" >&2
    exit 2
fi

exec "${HEADLESSCODE_CMD[@]}" orchestrate --repo "$REPO_ROOT" "$@"
