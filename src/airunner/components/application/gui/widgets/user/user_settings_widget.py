from PySide6.QtCore import Slot

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.application.gui.widgets.user.templates.user_settings_ui import (
    Ui_user_settings_widget,
)
from airunner.utils.location import get_lat_lon


class UserSettingsWidget(BaseWidget):
    ui: Ui_user_settings_widget  # type: ignore[assignment]
    widget_class_ = Ui_user_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.resource_store.first("User")
        if user is not None:
            self.ui.username.setText(user.username)
            self.ui.zipcode.setText(user.zipcode)
            self.ui.unit_system.setCurrentText(user.unit_system)
        else:
            self.resource_store.create("User", {})

    @Slot(str)
    def username_changed(self, val):
        user = self.resource_store.first("User")
        self.resource_store.update(
            "User",
            user.id,
            {"username": val},
        )

    @Slot(str)
    def zipcode_changed(self, val):
        # only do zipcode lookup if zipcode is 5 digits
        if len(val) == 5:
            user = self.resource_store.first("User")
            data = {}
            if user.zipcode != val:
                data["zipcode"] = val
                result = get_lat_lon(val)
                if result:
                    data["latitude"] = result["lat"]
                    data["longitude"] = result["lon"]
                    data["location_display_name"] = str(result["row"])
                self.resource_store.update("User", user.id, data)

    @Slot(str)
    def unit_system_changed(self, val):
        user = self.resource_store.first("User")
        self.resource_store.update(
            "User",
            user.id,
            {"unit_system": val},
        )
