"""Unit verification for the fresh-canvas undo/redo fix.

Background
----------
The bug: on a fresh canvas, drawing a stroke then clicking undo did nothing.
Root cause: the history transaction was keyed on layer id ``None`` at press
time while the stroke actually landed on layer 0, so the "before" state
(blank global drawing-pad record) and "after" state (still-blank global
record, because the stroke bytes were written to layer 0's per-layer record)
compared equal and ``_commit_layer_history_transaction`` dropped the entry.

The fix resolves the stroke-target layer id (lowest-id fallback when the
active layer item / selection is unavailable) so the transaction is keyed on
the same layer the stroke lands on.

This file reproduces that scenario at the unit level WITHOUT launching the
GUI.  It loads ``canvas_history_mixin.py`` directly via importlib and stubs
every module-level dependency (``PySide6``, ``PIL``, the airunner helper
modules) in ``sys.modules``, so it runs on a bare Python 3 interpreter --
no PySide6, PIL, or ``packaging`` required.

ISOLATION REQUIREMENT
---------------------
The ``sys.modules`` stubs are installed at import time. Running this module
inside a shared pytest process poisons the interpreter for every other test
(real PySide6/PIL/airunner modules get shadowed, which can segfault Qt-heavy
suites). The module therefore only installs its stubs when run standalone::

    python3 src/airunner/components/art/gui/widgets/canvas/mixins/tests/test_canvas_history_fresh_canvas.py

When pytest collects this file as part of a larger session it is NOT run --
a single skip test explains the isolation requirement instead (issue #2055),
so the GUI suite can be collected in one invocation without segfaults.

If you specifically want pytest reporting for these checks, run the file in
its OWN process with ``RUN_ISOLATED_TESTS=1`` and the full dev dependency
set installed (PySide6, Pillow, and the repo packages), because pytest then
imports the real ``mixins/__init__.py`` aggregation and the mixin under test
loads against the real modules::

    RUN_ISOLATED_TESTS=1 pytest src/airunner/components/art/gui/widgets/canvas/mixins/tests/test_canvas_history_fresh_canvas.py -q
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

# ---------------------------------------------------------------------------
# Isolation guard (issue #2055).
#
# ``_install_stubs()`` replaces real third-party modules in ``sys.modules``.
# It is only safe when this module is the only thing in the process. The
# stubs are therefore installed only for standalone runs; a shared pytest
# session never installs them and contributes a single skip test instead.
# ``RUN_ISOLATED_TESTS=1`` opts into running the checks under pytest in an
# isolated process against the real modules.
# ---------------------------------------------------------------------------
_RUNNING_STANDALONE = __name__ == "__main__"
_ISOLATED_SESSION = os.environ.get("RUN_ISOLATED_TESTS") == "1"
_ALLOW_STUBS = _RUNNING_STANDALONE or _ISOLATED_SESSION

# ---------------------------------------------------------------------------
# Stubs for the module-level imports of canvas_history_mixin.py
# ---------------------------------------------------------------------------


class _QPointF:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self._x = float(x)
        self._y = float(y)

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y

    def __repr__(self) -> str:
        return f"QPointF({self._x}, {self._y})"


class _QTimer:
    """QTimer stub: records singleShot callbacks but never fires them."""

    calls = []

    @staticmethod
    def singleShot(ms: int, callback) -> None:
        _QTimer.calls.append((ms, callback))


class _QApplication:
    @staticmethod
    def focusWidget():
        return None


class _QGraphicsView:
    pass


class _ImageQt:
    @staticmethod
    def ImageQt(image):
        # Passthrough: the unit test never decodes image bytes.
        return image


def _convert_binary_to_image(data):
    # Passthrough stub; the test only checks that the layer item received a
    # non-None surface on undo, never decodes pixels.
    return data


class _ViewState:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _CanvasPositionManager:
    @staticmethod
    def absolute_to_display(pos, view_state):
        return pos

    @staticmethod
    def display_to_absolute(pos, view_state):
        return pos


def _ensure_layer_setting(resource_name, layer_id, store=None):
    if store is None:
        raise RuntimeError("ensure_layer_setting stub requires a store")
    return store.get_layer(resource_name, layer_id)


def _install_stubs() -> None:
    """Install stub modules into sys.modules before loading the mixin.

    Used only for standalone runs (``python3 <this file>``): on a bare
    interpreter every module the mixin imports is stubbed, so no repository
    code and none of its dependencies (PySide6, Pillow, ...) are loaded.
    """
    created = {}

    def make_pkg(name: str) -> types.ModuleType:
        mod = types.ModuleType(name)
        mod.__path__ = []  # mark as a package
        created[name] = mod
        sys.modules[name] = mod
        return mod

    # Package chain stubs.
    make_pkg("PySide6")
    make_pkg("PIL")
    make_pkg("airunner")
    make_pkg("airunner.components")
    make_pkg("airunner.components.art")
    make_pkg("airunner.components.art.data")
    make_pkg("airunner.components.art.utils")
    make_pkg("airunner.utils")

    # Leaf module stubs.
    qt_core = types.ModuleType("PySide6.QtCore")
    qt_core.QPointF = _QPointF
    qt_core.QTimer = _QTimer
    sys.modules["PySide6.QtCore"] = qt_core

    qt_widgets = types.ModuleType("PySide6.QtWidgets")
    qt_widgets.QApplication = _QApplication
    qt_widgets.QGraphicsView = _QGraphicsView
    sys.modules["PySide6.QtWidgets"] = qt_widgets

    pil_imageqt = types.ModuleType("PIL.ImageQt")
    pil_imageqt.ImageQt = _ImageQt.ImageQt
    sys.modules["PIL.ImageQt"] = pil_imageqt

    layer_records = types.ModuleType(
        "airunner.components.art.data.canvas_layer_records"
    )
    layer_records.ensure_layer_setting = _ensure_layer_setting
    sys.modules["airunner.components.art.data.canvas_layer_records"] = (
        layer_records
    )

    pos_manager = types.ModuleType(
        "airunner.components.art.utils.canvas_position_manager"
    )
    pos_manager.CanvasPositionManager = _CanvasPositionManager
    pos_manager.ViewState = _ViewState
    sys.modules["airunner.components.art.utils.canvas_position_manager"] = (
        pos_manager
    )

    utils_image = types.ModuleType("airunner.utils.image")
    utils_image.convert_binary_to_image = _convert_binary_to_image
    sys.modules["airunner.utils.image"] = utils_image

    # Make the package attributes point at the leaf modules so
    # ``from a.b.c import x`` style lookups behave predictably.
    created["airunner"].utils = sys.modules["airunner.utils"]
    created["airunner.components"].art = sys.modules[
        "airunner.components.art"
    ]
    created["airunner.components.art"].data = sys.modules[
        "airunner.components.art.data"
    ]
    created["airunner.components.art"].utils = sys.modules[
        "airunner.components.art.utils"
    ]
    sys.modules["airunner.utils"].image = sys.modules["airunner.utils.image"]
    sys.modules["airunner.components.art.data"].canvas_layer_records = (
        layer_records
    )
    sys.modules[
        "airunner.components.art.utils"
    ].canvas_position_manager = pos_manager


def _load_mixin():
    """Load the real CanvasHistoryMixin from disk (stubbed or real deps)."""
    mixin_path = (
        Path(__file__).resolve().parents[1] / "canvas_history_mixin.py"
    )
    spec = importlib.util.spec_from_file_location(
        "canvas_history_mixin_under_test", mixin_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.CanvasHistoryMixin


if _RUNNING_STANDALONE:
    # Bare interpreter: stub the whole dependency chain so the mixin loads
    # without PySide6/Pillow (or any other repository dependency).
    _install_stubs()
elif _ISOLATED_SESSION:
    # Isolated pytest run (RUN_ISOLATED_TESTS=1, full dev dependency set
    # installed). Pytest re-imports the real ancestor ``__init__.py`` files
    # (including the ``mixins`` package aggregation) when setting up the
    # ``Package`` nodes, so the real package tree must be importable FIRST;
    # the ``sys.modules`` stubs are installed only afterwards so the mixin
    # under test uses the deterministic stubs (and never schedules real Qt
    # timers that segfault at interpreter exit). Make the repo ``src/`` and
    # ``shared/`` importable and pre-import the real mixins package.
    _repo_root = Path(__file__).resolve().parents[8]
    for _extra_path in (_repo_root / "src", _repo_root / "shared"):
        _extra = str(_extra_path)
        if _extra not in sys.path:
            sys.path.append(_extra)
    import airunner.components.art.gui.widgets.canvas.mixins  # noqa: F401
    _install_stubs()


if _ALLOW_STUBS:
    CanvasHistoryMixin = _load_mixin()

    # -----------------------------------------------------------------------
    # Minimal fakes for the scene protocol the mixin depends on.
    # -----------------------------------------------------------------------


    class FakeLayerItem:
        """Stand-in for a layer graphics item; records surface updates."""

        def __init__(self, layer_id: int):
            self.layer_id = layer_id
            self.updated_images = []
            self.pos_calls = []
            self.layer_image_data = {}

        def updateImage(self, image, **kwargs):
            self.updated_images.append(image)

        def setPos(self, pos):
            self.pos_calls.append(pos)


    class FakeStore:
        """Stand-in for the resource store's get_layer(...) API."""

        def __init__(self):
            self._records = {}

        def get_layer(self, resource_name: str, layer_id: int):
            return self._records.setdefault(
                layer_id,
                SimpleNamespace(
                    image=None, mask=None, x_pos=0, y_pos=0, text_items=None
                ),
            )

        def record(self, layer_id: int):
            return self._records[layer_id]


    class FakeCanvasAPI:
        def __init__(self):
            self.update_history_calls = []
            self.update_image_positions_calls = 0

        def update_history(self, undo: int, redo: int) -> None:
            self.update_history_calls.append((undo, redo))

        def update_image_positions(self) -> None:
            self.update_image_positions_calls += 1


    class FakeArt:
        def __init__(self):
            self.canvas = FakeCanvasAPI()


    class StubScene(CanvasHistoryMixin):
        """A minimal canvas scene hosting the real mixin under test."""

        def __init__(self, store, layer_items, selected_id):
            self.resource_store = store
            self._layer_items = layer_items
            self._selected_layer_id = selected_id
            self.drawing_pad_settings = SimpleNamespace(
                image=None, mask=None, x_pos=0, y_pos=0, text_items=None
            )
            self.application_settings = SimpleNamespace(
                document_width=64,
                document_height=64,
                working_width=64,
                working_height=64,
            )
            self.undo_history = []
            self.redo_history = []
            self._history_transactions = {}
            self._structure_history_transaction = None
            self._pending_image_binary = None
            self._current_active_image_binary = None
            self.current_active_image = None
            self.original_item_positions = {}
            self.api = SimpleNamespace(art=FakeArt())
            self.parent = SimpleNamespace()

        # --- protocol methods expected by the mixin ---------------------------

        def _get_current_selected_layer_id(self):
            return self._selected_layer_id

        def _resolve_layer_canvas_item(self):
            # Simulate press time on a fresh canvas where the active layer item
            # could not be resolved (returns None), forcing the history mixin's
            # lowest-id fallback over _layer_items -- the path under test.
            return None

        def update_drawing_pad_settings(self, layer_id=None, **updates):
            if layer_id is None:
                target = self.drawing_pad_settings
            else:
                target = self.resource_store.get_layer(
                    "DrawingPadSettings", layer_id
                )
            for key, value in updates.items():
                setattr(target, key, value)

        def get_canvas_offset(self):
            return _QPointF(0.0, 0.0)

        def _refresh_layer_display(self):
            pass

        def _update_canvas_memory_allocation(self):
            pass

        def _create_blank_surface(self, width, height):
            return f"blank:{int(width)}x{int(height)}"

        def _is_active_history_scene(self):
            # The active-scene gating lives in _is_active_history_scene and is
            # not the subject of this test; treat this scene as the active one.
            return True

        def views(self):
            return []

        def update(self):
            pass


    def make_airaw1(width: int = 64, height: int = 64, fill: int = 0xFF) -> bytes:
        """Build a minimal AIRAW1 payload (matches brush_scene release path)."""
        return (
            b"AIRAW1"
            + width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + bytes([fill]) * (width * height * 4)
        )


    # ---------------------------------------------------------------------------
    # Test scenarios
    # ---------------------------------------------------------------------------


    def _fresh_canvas_scene():
        store = FakeStore()
        layer0_item = FakeLayerItem(0)
        scene = StubScene(
            store=store,
            layer_items={0: layer0_item},
            selected_id=None,  # fresh canvas: no resolvable selection
        )
        return store, layer0_item, scene


    def test_resolve_target_fresh_canvas():
        """No selection + layer 0 present -> target resolves to 0 (lowest id)."""
        _, _, scene = _fresh_canvas_scene()
        resolved = scene._resolve_history_target_layer_id()
        assert resolved == 0, f"expected 0, got {resolved!r}"


    def test_resolve_target_stale_selection():
        """Stale selected id (not in _layer_items) -> lowest-id item wins."""
        store = FakeStore()
        layer0_item = FakeLayerItem(0)
        layer5_item = FakeLayerItem(5)
        scene = StubScene(
            store=store,
            layer_items={0: layer0_item, 5: layer5_item},
            selected_id=99,  # saved selection pointing at a deleted layer
        )
        resolved = scene._resolve_history_target_layer_id()
        assert resolved == 0, f"expected 0 (lowest-id), got {resolved!r}"


    def test_resolve_target_valid_selection():
        """Selected id present in _layer_items -> selection is honored."""
        store = FakeStore()
        layer0_item = FakeLayerItem(0)
        layer5_item = FakeLayerItem(5)
        scene = StubScene(
            store=store,
            layer_items={0: layer0_item, 5: layer5_item},
            selected_id=5,
        )
        resolved = scene._resolve_history_target_layer_id()
        assert resolved == 5, f"expected 5 (selection), got {resolved!r}"


    def test_empty_layer_items_skips_history():
        """No layers at all -> no target, _add_image_to_undo skips history."""
        store = FakeStore()
        scene = StubScene(
            store=store,
            layer_items={},
            selected_id=None,
        )
        resolved = scene._resolve_history_target_layer_id()
        assert resolved is None, f"expected None, got {resolved!r}"

        result = scene._add_image_to_undo(layer_id=None)
        assert result is None, f"expected None return, got {result!r}"
        assert scene.undo_history == [], "no history entry may be created"
        assert scene._history_transactions == {}, "no transaction may be started"


    def test_fresh_canvas_draw_undo():
        """The full fresh-canvas draw -> undo scenario (the original bug)."""
        store, layer0_item, scene = _fresh_canvas_scene()

        # --- press: begin history on the resolved stroke-target layer ----------
        target_layer_id = scene._add_image_to_undo(layer_id=None)
        assert target_layer_id == 0, f"expected 0, got {target_layer_id!r}"

        # Before-state captured at press must be blank (image is None).
        before = scene._history_transactions[0]["before"]
        assert before["image"] is None, (
            f"expected blank before-state, got {before['image']!r}"
        )
        assert scene._pending_image_binary is None

        # --- stroke lands: release writes the stroke bytes to layer 0 ---------
        raw_binary = make_airaw1()
        scene.current_active_image = raw_binary
        scene._pending_image_binary = raw_binary
        scene._current_active_image_binary = raw_binary
        scene.update_drawing_pad_settings(
            layer_id=0,
            image=raw_binary,
            x_pos=0,
            y_pos=0,
        )

        scene._commit_layer_history_transaction(target_layer_id, "image")

        # The before/after must differ, so the entry is NOT dropped.
        assert len(scene.undo_history) == 1, (
            f"expected 1 undo entry, got {len(scene.undo_history)}"
        )
        entry = scene.undo_history[0]
        assert entry["layer_id"] == 0, f"entry keyed on {entry['layer_id']!r}"
        assert entry["before"]["image"] is None
        assert entry["after"]["image"] == raw_binary
        assert entry["before"] != entry["after"], (
            "before/after must differ for the entry to survive"
        )

        # History counts were broadcast.
        assert scene.api.art.canvas.update_history_calls[-1] == (1, 0), (
            f"unexpected history broadcast: "
            f"{scene.api.art.canvas.update_history_calls[-1]}"
        )

        # --- undo: pop the entry and restore the before-state (blank) ---------
        scene.on_action_undo_signal()

        assert scene.undo_history == [], "undo must empty the undo stack"
        assert len(scene.redo_history) == 1, (
            "undo must push the entry onto the redo stack"
        )
        assert scene.redo_history[0]["layer_id"] == 0

        # Layer 0's settings record is back to blank.
        assert store.record(0).image is None, (
            "layer 0 image must be restored to the blank before-state"
        )
        # The layer graphics item received the blank surface update.
        assert layer0_item.updated_images == ["blank:64x64"], (
            f"layer item updates: {layer0_item.updated_images!r}"
        )
        # The final history broadcast reflects (undo=0, redo=1).
        assert scene.api.art.canvas.update_history_calls[-1] == (0, 1), (
            f"unexpected final history broadcast: "
            f"{scene.api.art.canvas.update_history_calls[-1]}"
        )


    def _run_all() -> int:
        tests = [
            ("resolve target on fresh canvas (no selection) -> 0",
             test_resolve_target_fresh_canvas),
            ("stale selected layer id falls back to lowest-id item",
             test_resolve_target_stale_selection),
            ("valid selected layer id is honored",
             test_resolve_target_valid_selection),
            ("empty _layer_items -> resolve None and skip history",
             test_empty_layer_items_skips_history),
            ("fresh-canvas draw -> history entry -> undo restores blank layer",
             test_fresh_canvas_draw_undo),
        ]
        failures = 0
        for label, fn in tests:
            try:
                fn()
            except AssertionError as exc:
                failures += 1
                print(f"FAIL: {label}\n      {exc}")
            except Exception as exc:  # noqa: BLE001 - report any unexpected error
                failures += 1
                print(f"ERROR: {label}\n      {type(exc).__name__}: {exc}")
            else:
                print(f"PASS: {label}")
        print(f"\n{len(tests) - failures}/{len(tests)} checks passed")
        return 1 if failures else 0

else:
    # Shared pytest session: do NOT install the sys.modules stubs (they would
    # poison the interpreter for every other test, issue #2055). Contribute a
    # single skip test that explains how to run this file in isolation.
    CanvasHistoryMixin = None  # noqa: F841 - document that the mixin is unloaded

    import pytest as _pytest_module

    def test_requires_isolated_run():
        """This file installs sys.modules stubs at import time (issue #2055)."""
        _pytest_module.skip(
            "test_canvas_history_fresh_canvas.py must not run in a shared "
            "pytest session: it installs sys.modules stubs that poison the "
            "interpreter for other tests. Run it standalone "
            "(`python3 <file>.py`) or, with the full dev dependency set "
            "installed, in its own process via "
            "`RUN_ISOLATED_TESTS=1 pytest <file> -q`."
        )


if __name__ == "__main__":
    if _ALLOW_STUBS:
        sys.exit(_run_all())
    # Standalone execution always implies _ALLOW_STUBS; this branch is only a
    # safety net if the guard logic ever changes.
    print(
        "Refusing to run: the sys.modules stubs are only installed when "
        "RUN_ISOLATED_TESTS=1 is set or the file runs as __main__."
    )
    sys.exit(1)
