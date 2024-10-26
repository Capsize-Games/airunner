from PySide6.QtCore import Slot

from airunner.data.models.settings_models import User
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.user.templates.user_settings_ui import Ui_user_settings_widget


class UserSettingsWidget(BaseWidget):
    widget_class_ = Ui_user_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        session = self.session
        user = session.query(User).first()
        if user is not None:
            self.ui.username.setText(user.username)
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
