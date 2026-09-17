"""Known exceptions to scripts/check_import_boundaries.py (issue #2193).

Split into its own module because it is policy data, not checking
logic, and the two together pushed check_import_boundaries.py well
past this account's 250-line file guideline.

Explicit, individually-justified exceptions. Each entry names the
file, the exact imported module, and the issue that removes it --
never a wildcard and never a count threshold (#2193's own
requirement). A violation not in this set fails the check.

Entries left over from before #2186/#2190 merge: those two branches
already fix every one of these sites; they show as violations here
only because this checker was written and run against master before
either landed. Once both are merged this whole block becomes empty
and should be deleted, not just have entries commented out.
"""

from __future__ import annotations

ALLOWLIST: frozenset[tuple[str, int, str]] = frozenset(
    {
        # Fixed by #2186 (not yet merged to the branch this check runs
        # against).
        (
            "services/src/airunner_services/daemon_client/"
            "resource_store.py",
            190,
            "airunner.utils.settings.get_qsettings",
        ),
        (
            "services/src/airunner_services/daemon_client/"
            "resource_store.py",
            206,
            "airunner.utils.settings.get_qsettings",
        ),
        (
            "services/src/airunner_services/database/models/"
            "application_settings.py",
            24,
            "airunner.utils.settings.get_qsettings",
        ),
        (
            "services/src/airunner_services/database/models/"
            "application_settings.py",
            40,
            "airunner.utils.settings.get_qsettings",
        ),
        # Fixed by #2189 (not yet merged to the branch this check runs
        # against).
        (
            "services/src/airunner_services/llm/tools/math_tools.py",
            11,
            "airunner_services.eval.math_tools",
        ),
        # Fixed by #2190 (not yet merged to the branch this check runs
        # against).
        (
            "services/src/airunner_services/vendor/melo/api.py",
            9,
            "airunner_common.contract_enums",
        ),
        (
            "services/src/airunner_services/vendor/melo/api.py",
            10,
            "airunner_services.utils.memory.clear_memory",
        ),
        (
            "services/src/airunner_services/vendor/melo/data_utils.py",
            7,
            "airunner_common.contract_enums",
        ),
        (
            "services/src/airunner_services/vendor/melo/"
            "runtime_support.py",
            7,
            "airunner_common.settings",
        ),
        (
            "services/src/airunner_services/vendor/melo/"
            "runtime_support.py",
            8,
            "airunner_services.utils.application",
        ),
        (
            "services/src/airunner_services/vendor/melo/"
            "runtime_support.py",
            19,
            "airunner_services.database.models.path_settings",
        ),
        (
            "services/src/airunner_services/vendor/melo/split_utils.py",
            3,
            "airunner_common.contract_enums",
        ),
        (
            "services/src/airunner_services/vendor/melo/text/"
            "__init__.py",
            1,
            "airunner_common.contract_enums",
        ),
        (
            "services/src/airunner_services/vendor/melo/text/"
            "cleaner.py",
            4,
            "airunner_common.contract_enums",
        ),
        (
            "services/src/airunner_services/vendor/melo/text/"
            "language_base.py",
            6,
            "airunner_common.settings",
        ),
        (
            "services/src/airunner_services/vendor/melo/text/"
            "symbols.py",
            2,
            "airunner_common.contract_enums",
        ),
        (
            "services/src/airunner_services/vendor/openvoice/api.py",
            5,
            "airunner.enums",
        ),
        (
            "services/src/airunner_services/vendor/openvoice/"
            "se_extractor.py",
            13,
            "airunner_common.settings",
        ),
        (
            "services/src/airunner_services/vendor/openvoice/"
            "se_extractor.py",
            14,
            "airunner.utils.application",
        ),
        (
            "services/src/airunner_services/vendor/openvoice/utils.py",
            5,
            "airunner.enums",
        ),
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
            463,
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
