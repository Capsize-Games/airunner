"""Settings mixin modules for modular settings management."""

from airunner.components.application.gui.windows.main.mixins.settings_property_mixin import (
    SettingsPropertyMixin,
)
from airunner.components.application.gui.windows.main.mixins.settings_list_property_mixin import (
    SettingsListPropertyMixin,
)
from airunner.components.application.gui.windows.main.mixins.image_property_mixin import (
    ImagePropertyMixin,
)
from airunner.components.application.gui.windows.main.mixins.settings_cache_mixin import (
    SettingsCacheMixin,
)
from airunner.components.application.gui.windows.main.mixins.layer_settings_mixin import (
    LayerSettingsMixin,
)
from airunner.components.application.gui.windows.main.mixins.settings_loader_mixin import (
    SettingsLoaderMixin,
)
from airunner.components.application.gui.windows.main.mixins.basic_settings_update_mixin import (
    BasicSettingsUpdateMixin,
)
from airunner.components.application.gui.windows.main.mixins.layer_settings_update_mixin import (
    LayerSettingsUpdateMixin,
)
from airunner.components.application.gui.windows.main.mixins.model_management_mixin import (
    ModelManagementMixin,
)
from airunner.components.application.gui.windows.main.mixins.utility_and_chatbot_mixin import (
    UtilityAndChatbotMixin,
)

__all__ = [
    "SettingsPropertyMixin",
    "SettingsListPropertyMixin",
    "ImagePropertyMixin",
    "SettingsCacheMixin",
    "LayerSettingsMixin",
    "SettingsLoaderMixin",
    "BasicSettingsUpdateMixin",
    "LayerSettingsUpdateMixin",
    "ModelManagementMixin",
    "UtilityAndChatbotMixin",
]
