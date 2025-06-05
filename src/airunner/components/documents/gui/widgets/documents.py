from airunner.components.documents.gui.widgets.templates.documents_ui import (
    Ui_documents,
)

from airunner.gui.widgets.base_widget import BaseWidget
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon

from airunner.components.browser.gui.widgets.mixins.session_persistence_mixin import (
    SessionPersistenceMixin,
)
from airunner.components.browser.gui.widgets.mixins.privacy_mixin import (
    PrivacyMixin,
)
from airunner.components.browser.gui.widgets.mixins.panel_mixin import (
    PanelMixin,
)
from airunner.components.browser.gui.widgets.mixins.navigation_mixin import (
    NavigationMixin,
)
from airunner.components.browser.gui.widgets.mixins.summarization_mixin import (
    SummarizationMixin,
)
from airunner.components.browser.gui.widgets.mixins.cache_mixin import (
    CacheMixin,
)
from airunner.components.browser.gui.widgets.mixins.ui_setup_mixin import (
    UISetupMixin,
)


class DocumentsWidget(
    UISetupMixin,
    SessionPersistenceMixin,
    PrivacyMixin,
    PanelMixin,
    NavigationMixin,
    SummarizationMixin,
    CacheMixin,
    BaseWidget,
):
    """Widget that displays a single browser instance (address bar, navigation, webview, etc.).

    Inherits mixins for modular browser logic.
    """

    titleChanged = Signal(str)
    urlChanged = Signal(str, str)  # url, title
    faviconChanged = Signal(QIcon)
    widget_class_ = Ui_documents

    def __init__(self, *args, private: bool = False, **kwargs):
        self._favicon = None
        self._private = private
        super().__init__(*args, **kwargs)
        self.setup_ui()
        self.setup_signals()
        self.setup_mixin_methods()