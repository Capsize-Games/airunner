from PySide6.QtCore import Slot

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.application.gui.widgets.user.templates.user_settings_ui import (
    Ui_user_settings_widget,
)
from airunner.components.user.data.user import User
from airunner.utils.location import get_lat_lon


class UserSettingsWidget(BaseWidget):
    widget_class_ = Ui_user_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = User.objects.first()
        if user is not None:
            self.ui.username.setText(user.username)
            self.ui.zipcode.setText(user.zipcode)
            self.ui.unit_system.setCurrentText(user.unit_system)
        else:
            user = User()
            user.save()

    @Slot(str)
    def username_changed(self, val):
        user = User.objects.first()
        User.objects.update(
            pk=user.id,
            username=val,
        )

    @Slot(str)
    def zipcode_changed(self, val):
        # only do zipcode lookup if zipcode is 5 digits
        if len(val) == 5:
            user = User.objects.first()
            data = {}
            if user.zipcode != val:
                data["zipcode"] = val
                result = get_lat_lon(val)
                if result:
                    data["latitude"] = result["lat"]
                    data["longitude"] = result["lon"]
                    data["location_display_name"] = str(result["row"])
                User.objects.update(pk=user.id, **data)

    @Slot(str)
    def unit_system_changed(self, val):
        user = User.objects.first()
        User.objects.update(
            pk=user.id,
            unit_system=val,
        )
