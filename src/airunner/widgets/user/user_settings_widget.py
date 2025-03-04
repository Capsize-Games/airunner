from PySide6.QtCore import Slot

from airunner.data.models import User
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.user.templates.user_settings_ui import Ui_user_settings_widget
from airunner.utils.get_lat_lon import get_lat_lon


class UserSettingsWidget(BaseWidget):
    widget_class_ = Ui_user_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        session = self.session
        user = session.query(User).first()
        if user is not None:
            self.ui.username.setText(user.username)
            self.ui.zipcode.setText(user.zipcode)
            self.ui.unit_system.setCurrentText(user.unit_system)
        else:
            user = User()
            session.add(user)
            session.commit()

    @Slot(str)
    def username_changed(self, val):
        session = self.session
        user = session.query(User).first()
        user.username = val
        session.commit()

    @Slot(str)
    def zipcode_changed(self, val):
        # only do zipcode lookup if zipcode is 5 digits
        if len(val) == 5:
            session = self.session
            user = session.query(User).first()
            if user.zipcode != val:
                user.zipcode = val
                result = get_lat_lon(val)
                if result:
                    lat, lon, display_name = result
                    user.latitude = lat
                    user.longitude = lon
                    user.location_display_name = display_name
                session.commit()

    @Slot(str)
    def unit_system_changed(self, val):
        session = self.session
        user = session.query(User).first()
        user.unit_system = val
        session.commit()