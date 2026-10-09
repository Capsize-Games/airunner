"""Guards the phase-4 removal of the Jinja2 chat widget (#2230).

The desktop chat surface is the hosted UwUChat client; the old Jinja2
transcript widget, its templates and its render paths must not come
back alongside it.
"""

from __future__ import annotations

from pathlib import Path

from airunner.components.server.local_http_server import (
    MultiDirectoryCORSRequestHandler,
)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_GUI_ROOT = _REPO_ROOT / "src" / "airunner"
_BASE_WIDGET = (
    _GUI_ROOT
    / "components"
    / "application"
    / "gui"
    / "widgets"
    / "base_widget.py"
)
_LOCAL_SERVER = _GUI_ROOT / "components" / "server" / "local_http_server.py"


def test_no_jinja_templates_ship_with_the_gui() -> None:
    """No Jinja2 transcript template remains in the GUI tree."""
    leftovers = sorted(
        str(path.relative_to(_REPO_ROOT))
        for path in _GUI_ROOT.rglob("*.jinja2.html")
    )
    assert leftovers == []
    assert not (_GUI_ROOT / "static" / "content_widgets").exists()


def test_base_widget_has_no_template_render_path() -> None:
    """The shared widget base no longer renders Jinja2 templates."""
    source = _BASE_WIDGET.read_text(encoding="utf-8")
    for marker in (
        "render_template",
        "web_engine_view",
        "CONTENT_WIDGETS_BASE_PATH",
        "jinja2",
    ):
        assert marker not in source


def test_local_server_renders_no_templates() -> None:
    """The static server serves files; it renders no templates."""
    source = _LOCAL_SERVER.read_text(encoding="utf-8")
    for marker in (
        "import jinja2",
        "FileSystemLoader",
        "get_template",
    ):
        assert marker not in source


def test_local_server_refuses_template_suffix() -> None:
    """A ``.jinja2.html`` path never resolves to a served file."""
    handler = MultiDirectoryCORSRequestHandler.__new__(
        MultiDirectoryCORSRequestHandler
    )
    handler.directories = [str(_GUI_ROOT / "static")]
    assert handler.translate_path("/static/html/x.jinja2.html") == ""
