"""Known exceptions to scripts/check_import_boundaries.py (issue #2193).

Split into its own module because it is policy data, not checking
logic, and the two together pushed check_import_boundaries.py well
past this account's 250-line file guideline.

Explicit, individually-justified exceptions. Each entry names the
file, the exact imported module, and the issue that removes it --
never a wildcard and never a count threshold (#2193's own
requirement). A violation not in this set fails the check.

The entries from #2186/#2189/#2190 that used to live here were
removed once those PRs merged (#2203/#2206/#2207) -- confirmed
via test_allowlist_entries_are_individually_justified, which fails
loudly on a stale entry rather than letting one silently accumulate.
"""

from __future__ import annotations

ALLOWLIST: frozenset[tuple[str, int, str]] = frozenset(
    {
        # Genuinely open, not yet decided. A private test-mode
        # configuration helper (airunner_native.launcher.
        # _configure_test_mode) is imported by three services files
        # to keep sidecar-launcher tests from opening a real GUI. This
        # is a narrow, always-lazy import, but airunner_services ->
        # airunner_native is not otherwise a designed edge (unlike
        # airunner_native -> airunner/airunner_services, which the
        # checker's own allowed graph now grants, this direction has
        # no structural reason -- services does not launch anything
        # native). Whether to formalize this edge or move
        # _configure_test_mode somewhere neutral (airunner_common is
        # the obvious candidate) is an open question, not resolved by
        # this issue.
        (
            "services/src/airunner_services/bin/airunner_headless.py",
            473,
            "airunner_native.launcher",
        ),
        (
            "services/src/airunner_services/runtimes/"
            "sidecar_art_launcher.py",
            74,
            "airunner_native.launcher",
        ),
        (
            "services/src/airunner_services/runtimes/"
            "sidecar_tts_launcher.py",
            67,
            "airunner_native.launcher",
        ),
    }
)
