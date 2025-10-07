from typing import Dict, List, Optional, Tuple
from abc import ABC, ABCMeta
from abc import abstractmethod
import os

from PySide6 import QtGui
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer
from urllib.parse import urlencode
from airunner.enums import CanvasToolName, TemplateName
from airunner.gui.styles.styles_mixin import StylesMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.settings import (
    CONTENT_WIDGETS_BASE_PATH,
    LOCAL_SERVER_HOST,
    LOCAL_SERVER_PORT,
)
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application import create_worker
from airunner.utils.widgets import (
    save_splitter_settings,
    load_splitter_settings,
)
from airunner.enums import SignalCode
from airunner.components.icons.managers.icon_manager import IconManager
from airunner.utils.settings.get_qsettings import get_qsettings


class BaseABCMeta(type(QWidget), ABCMeta):
    pass


class AbstractBaseWidget(
    MediatorMixin,
    SettingsMixin,
    StylesMixin,
    QWidget,
    ABC,
    metaclass=BaseABCMeta,
):
    @abstractmethod
    def save_state(self):
        """
        Save the state of the widget.
        """

    @abstractmethod
    def restore_state(self):
        """
        Restore the state of the widget.
        """


class BaseWidget(AbstractBaseWidget):
    """
    Base class for all widgets.
    """

    widget_class_: Optional[object] = None
    icons: List[Optional[Tuple[str, str]]] = []
    ui: Optional[object] = None
    _splitters: List[str] = []
    _splitter_debounce_timer: Optional[QTimer] = None
    _splitter_debounce_ms = 300

    def __init__(self, *args, **kwargs):
        self.splitter_namespace = self.__class__.__name__
        # Instance-specific defaults
        self.icon_manager: Optional[IconManager] = None
        # Ensure each instance has its own signal_handlers dict rather than
        # sharing a class-level mutable default.
        self.signal_handlers = {} if not getattr(self, "signal_handlers", None) else dict(self.signal_handlers)
        self.signal_handlers.update(
            {
                SignalCode.QUIT_APPLICATION: self.handle_close,
                SignalCode.RETRANSLATE_UI_SIGNAL: self.on_retranslate_ui_signal,
                SignalCode.REFRESH_STYLESHEET_SIGNAL: self.on_theme_changed_signal,
            }
        )
        self.settings = get_qsettings()
        super().__init__(*args, **kwargs)

        if self.widget_class_:
            self.ui = self.widget_class_()

        if self.ui:
            self.ui.setupUi(self)
            self.icon_manager = IconManager(self.icons, self.ui)
            self.icon_manager.set_icons()

        self.services: Dict = {}
        self.worker_class_map: Dict = {}
        self.initialize_ui()
        self._setup_splitters()
        self.render_template()

    @property
    def web_engine_view(self) -> Optional[object]:
        """
        Set this to the QWebEngineView instance in your widget if you want to render templates.
        """
        return None

    @property
    def template(self) -> Optional[str]:
        """
        Override this property to return the name of the Jinja2 template to render.
        The template should be located in the static HTML directory.
        """
        return None

    @property
    def template_context(self) -> Dict:
        settings = get_qsettings()
        theme = settings.value("theme", TemplateName.SYSTEM_DEFAULT.value)
        return {
            "theme": theme.lower().replace(" ", "_"),
        }

    def render_template(self):
        if not self.web_engine_view or not self.template:
            return
        settings = get_qsettings()
        theme = settings.value("theme", TemplateName.SYSTEM_DEFAULT.value)
        theme_name = theme.lower().replace(" ", "_")
        try:
            # Pass theme variable to Jinja2 template for correct CSS links
            self._render_template(
                self.web_engine_view,
                self.template,
                **self.template_context,
            )
            # Also set window.currentTheme for JS
            js = f"window.currentTheme = '{theme_name}';"
            self.web_engine_view.page().runJavaScript(js)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(
                    f"Failed to render template {self.template}: {e}"
                )
            else:
                print(f"Failed to render template {self.template}: {e}")

    def on_theme_changed_signal(self, data: Dict):
        template = data.get("template", TemplateName.SYSTEM_DEFAULT)
        self.set_stylesheet(
            template=template,
        )

    @property
    def static_html_dir(self) -> str:
        """
        Return the directory where static HTML files are stored.
        """
        return os.path.join(CONTENT_WIDGETS_BASE_PATH, "html")

    @property
    def splitters(self) -> List[str]:
        """
        Return a list of splitter names as they appear in the UI.
        """
        return self._splitters

    @splitters.setter
    def splitters(self, value: List[str]):
        """
        Set the list of splitter names as they appear in the UI.
        """
        self._splitters = value

    @property
    def current_tool(self) -> CanvasToolName:
        return CanvasToolName(self.application_settings.current_tool)

    @property
    def is_dark(self) -> bool:
        return self.application_settings.dark_mode_enabled

    def initialize_ui(self):
        """
        Initialize the UI for the widget.
        This function is called in the constructor and can be overriden
        to set things like the slider widget.
        """

    def initialize(self):
        """
        Call this function to initialize the widget.
        :return:
        """
        self.initialize_workers()
        self.initialize_form()

    def initialize_workers(self):
        """
        Override this function to initialize workers.

        worker_class_map should be a dictionary of property names and worker classes.
        Example:
        worker_class_map = {
            "worker": WorkerClass
        }
        :return:
        """
        for property_name, worker_class_name_ in self.worker_class_map.items():
            worker = create_worker(worker_class_name_)
            setattr(self, property_name, worker)

    def initialize_form(self):
        pass

    def showEvent(self, event):
        super().showEvent(event)
        """
        Triggered when the app is loaded.
        Override this function in order to initialize the widget rather than
        using __init__.
        """
        self.initialize()
        self.restore_state()

    def save_state(self):
        """
        Called on close and saves the state of all splitter widgets
        """
        self._save_splitter_state()

    def restore_state(self):
        """
        Restore the state of the widget.
        """
        self.load_splitter_settings()

    def handle_close(self):
        """
        Callback for the QUIT_APPLICATION signal.
        """

    def on_retranslate_ui_signal(self):
        """
        Callback for the RETRANSLATE_UI_SIGNAL signal.
        """
        if self.ui:
            self.ui.retranslateUi(self)

    def set_button_icon(self, is_dark, button_name, icon):
        try:
            getattr(self, button_name).setIcon(
                QtGui.QIcon(
                    os.path.join(
                        f"src/icons/{icon}{'-light' if is_dark else ''}.png"
                    )
                )
            )
        except AttributeError as _e:
            pass

    def get_form_element(self, element):
        return getattr(self.ui, element)

    def get_plain_text(self, element):
        try:
            return self.get_form_element(element).toPlainText()
        except AttributeError:
            return None

    def get_text(self, element):
        try:
            return self.get_form_element(element).text()
        except AttributeError:
            return None

    def get_value(self, element):
        try:
            return self.get_form_element(element).value()
        except AttributeError:
            return None

    def get_is_checked(self, element):
        try:
            return self.get_form_element(element).isChecked()
        except AttributeError:
            return None

    def set_plain_text(self, element, val):
        try:
            self.get_form_element(element).setPlainText(val)
            return True
        except AttributeError:
            return False

    def set_text(self, element, val):
        try:
            self.get_form_element(element).setText(val)
            return True
        except AttributeError:
            return False
        except TypeError:
            return False

    def set_value(self, element, val):
        try:
            self.get_form_element(element).setValue(val)
            return True
        except AttributeError:
            return False

    def set_is_checked(self, element, val):
        try:
            self.get_form_element(element).setChecked(val)
            return True
        except AttributeError:
            return False

    def _setup_splitters(self):
        self._splitter_debounce_timer = QTimer(self)
        self._splitter_debounce_timer.setSingleShot(True)
        self._splitter_debounce_timer.timeout.connect(
            self._save_splitter_state
        )

        for splitter_name in self.splitters:
            try:
                splitter = getattr(self.ui, splitter_name)
                if splitter:
                    splitter.splitterMoved.connect(
                        self._debounce_splitter_moved
                    )
            except AttributeError:
                pass

    def _debounce_splitter_moved(self, *args):
        self._splitter_debounce_timer.start(self._splitter_debounce_ms)

    def _save_splitter_state(self):
        save_splitter_settings(
            self.ui, self.splitters, self.splitter_namespace
        )

    def load_splitter_settings(self, **kwargs):
        data = {
            "namespace": self.splitter_namespace,
        }
        data.update(kwargs)
        load_splitter_settings(self.ui, self.splitters, **data)

    def _render_template(self, element, template_name: str, **kwargs):
        """
        Load a Jinja2 template from the local HTTP server, passing kwargs as query parameters for server-side rendering.
        """
        # Build the URL to the template on the local server
        base_url = f"https://{LOCAL_SERVER_HOST}:{LOCAL_SERVER_PORT}/static/html/{template_name}"
        # Pass kwargs as query parameters (JSON-encode complex values)
        query = urlencode(
            {k: v if isinstance(v, str) else str(v) for k, v in kwargs.items()}
        )
        url = f"{base_url}?{query}" if query else base_url
        # Load the URL in the QWebEngineView
        element.setUrl(url)
