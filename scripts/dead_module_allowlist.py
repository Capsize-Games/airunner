"""Audited dead-module exceptions for scripts/check_dead_modules.py.

Every entry is a module nothing references -- no static import anywhere
in ``services/src``, ``services/tests`` or ``scripts``, no dotted-path
string registration, no bundle-spec mention. Each value explains what
the module is and what must happen to remove the entry: either the
module gets referenced again or it gets deleted. Never a wildcard, never
a count threshold (the same rule as
``scripts/import_boundary_allowlist.py``).

Owning issue: #2480. All entries below were audited against the real
tree; ``services/tests/test_dead_modules.py`` fails loudly on a stale
entry (file gone, or module referenced again) so fixed or resurrected
modules cannot linger here.
"""

from __future__ import annotations

# module -> why it is allowed to stay unreferenced (issue #2480).
ALLOWLIST: dict[str, str] = {
    # Unused agent-template dataclass; nothing imports AgentTemplate.
    "airunner_services.agents.templates": (
        "#2480: audited dead code, remove the module or reference it."
    ),
    # Service-owned API singleton; nothing imports API (all call sites
    # use ServiceApp / route functions directly).
    "airunner_services.api.api": (
        "#2480: audited dead code, remove the module or reference it."
    ),
    # Compatibility re-export shim (art_model_resolution,
    # art_model_versions); zero references repo-wide, including tests.
    "airunner_services.api.routes.art_model_paths": (
        "#2480: audited dead code, remove the module or reference it."
    ),
    # Service-owned application-data helpers; superseded, no importers.
    "airunner_services.application_data": (
        "#2480: audited dead code, remove the module or reference it."
    ),
    # Daemon-client mixin superseded by gui_daemon_client/launcher (the
    # only names services/src/airunner_services/daemon_client/__init__.py
    # exports); no importers.
    "airunner_services.daemon_client.conversation_client": (
        "#2480: audited dead code, remove the module or reference it."
    ),
    # Confined math worker, spawned as ``sys.executable <this file>`` by
    # file path, never imported: math_executor._worker_path joins
    # ``math_worker.py`` next to the executor so the child stays
    # stdlib-only and never imports the service package. Exercised by
    # services/tests/test_math_executor_confinement.py.
    "airunner_services.llm.core.math_worker": (
        "#2480/#2491: live via subprocess file-path spawn, not via import; "
        "entry stays while the executor spawns it by path."
    ),
    # Spawned as ``sys.executable <this file>`` by file path, never
    # imported: services/src/airunner_services/llm/core/tool_worker_runner.py:109
    # (``worker = os.path.join(here, "tool_worker.py")``). Docstring
    # states the contract: run by the runner, never forked.
    "airunner_services.llm.core.tool_worker": (
        "#2480: live via subprocess file-path spawn, not via import; "
        "entry stays while the runner spawns it by path."
    ),
    # Confinement policy for the tool-worker subprocess, loaded
    # dynamically via tool_worker._load_sibling and exercised for real
    # by services/tests/test_release_w3_llm_sandbox.py
    # (pytest.importorskip + guard_tool_code calls); never imported
    # statically.
    "airunner_services.llm.core.tool_worker_confine": (
        "#2480: live via dynamic sibling load plus test coverage; entry "
        "stays until it is imported statically or removed."
    ),
    # Model-registration side-effect package (imports TargetFiles,
    # TargetDirectories, Chatbot for SQLAlchemy registration) that
    # nothing imports, so the registration never runs.
    "airunner_services.llm.data": (
        "#2480: audited dead code, remove the package or reference it."
    ),
    # Empty ``__init__`` in a package nothing imports.
    "airunner_services.llm.data.bootstrap": (
        "#2480: audited dead code, remove the package or reference it."
    ),
    # Data-model package for the long-running harness; registers
    # ProjectState et al on import but nothing imports it.
    "airunner_services.llm.long_running.data": (
        "#2480: audited dead code, remove the package or reference it."
    ),
    # Empty ``__init__`` in a package nothing imports.
    "airunner_services.llm.managers.agent.agents": (
        "#2480: audited dead code, remove the package or reference it."
    ),
    # Empty ``__init__`` in a package nothing imports.
    "airunner_services.llm.managers.agent.agents.tool_mixins": (
        "#2480: audited dead code, remove the package or reference it."
    ),
    # HuggingFace download manager; live download paths go through
    # services/src/airunner_services/downloads/ instead.
    "airunner_services.llm.managers.download_huggingface": (
        "#2480: audited dead code, remove the module or reference it."
    ),
    # Empty ``__init__`` in a package nothing imports.
    "airunner_services.llm.managers.storage": (
        "#2480: audited dead code, remove the package or reference it."
    ),
    # Self-described legacy shim retained for import stability
    # (``Legacy chat store package retained for import stability.``)
    # that nothing imports.
    "airunner_services.llm.managers.storage.chat_store": (
        "#2480: audited dead code, remove the package or reference it."
    ),
    # Crawl tool nothing references (only
    # services/src/airunner_services/llm/core/tool_registry.py registers
    # tool_search_tool, by dotted string).
    "airunner_services.llm.tools.intelligent_crawl_tool": (
        "#2480: audited dead code, remove the module or reference it."
    ),
    # Model-persistence helpers; daemon.py only has same-named methods,
    # no module import.
    "airunner_services.model_management.model_persistence": (
        "#2480: audited dead code, remove the module or reference it."
    ),
    # Superseded by airunner_common.logging_utils, which is what
    # bin/airunner_headless.py and app/service_app.py actually import.
    "airunner_services.utils.application.logging_utils": (
        "#2480: audited dead code, remove the module or reference it."
    ),
    # VRAM estimation utilities nothing imports.
    "airunner_services.utils.vram_utils": (
        "#2480: audited dead code, remove the module or reference it."
    ),
}
