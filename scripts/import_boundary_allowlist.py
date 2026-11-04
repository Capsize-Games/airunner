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

ALLOWLIST: frozenset[tuple[str, int, str]] = frozenset()
