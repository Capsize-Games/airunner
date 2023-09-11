from PyQt6.QtCore import QObject, Qt


class InputEventManager(QObject):
    events = {
        "wheelEvent": [],
    }

    shortcuts = {
        "generate": {
            "display_name": "F5",
            "key_value": Qt.Key.Key_F5,
            "modifiers": Qt.KeyboardModifier.NoModifier,
            "press_callbacks": [],
            "release_callbacks": [],
            "shortcut": None
        },
        "fullscreen": {
            "display_name": "F11",
            "key_value": Qt.Key.Key_F11,
            "modifiers": Qt.KeyboardModifier.NoModifier,
            "press_callbacks": [],
            "release_callbacks": [],
            "shortcut": None
        },
        "control_pressed": {
            "display_name": "Ctrl",
            "key_value": Qt.Key.Key_Control,
            "modifiers": Qt.KeyboardModifier.NoModifier,
            "press_callbacks": [],
            "release_callbacks": [],
            "shortcut": None
        },
        "shift_pressed": {
            "display_name": "Shift",
            "key_value": Qt.Key.Key_Shift,
            "modifiers": Qt.KeyboardModifier.NoModifier,
            "press_callbacks": [],
            "release_callbacks": [],
            "shortcut": None
        },
        "delete_outside_active_grid_area": {
            "display_name": "Delete",
            "key_value": Qt.Key.Key_Delete,
            "modifiers": Qt.KeyboardModifier.ShiftModifier,
            "press_callbacks": [],
            "release_callbacks": [],
            "shortcut": None
        },
    }

    def __init__(self, app):
        """
        A class which handles the keyboard shortcuts for the application.
        This class is responsible for setting up the shortcuts and handling the events.
        It should be instantiated in the main window.

        :param app: The main application object, this is the main window object.
        """
        super().__init__()
        self.app = app
        self.initialize_shortcuts()
        self.initialize_events()

    def register_event(self, event_name, callback):
        """
        Register events by name and callback function.
        :param event_name: must be a key in the events dictionary
        :param callback: a function which will be called when the event is triggered
        :return:
        """
        if event_name in self.events:
            self.events[event_name].append(callback)

    def register_keypress(self, key, press_callback=None, release_callback=None):
        if key in self.shortcuts:
            if press_callback:
                self.shortcuts[key]["press_callbacks"].append(press_callback)
            if release_callback:
                self.shortcuts[key]["release_callbacks"].append(release_callback)

    def initialize_shortcuts(self):
        self.app.keyPressEvent = self.handle_key_press_event
        self.app.keyReleaseEvent = self.handle_key_release_event

    def handle_key_press_event(self, event):
        for shortcut, value in self.shortcuts.items():
            if event.key() == value["key_value"]:
                modifier = value["modifiers"]
                if modifier != Qt.KeyboardModifier.NoModifier:
                    if event.modifiers() == modifier:
                        for callback in value["press_callbacks"]:
                            callback()
                else:
                    for callback in value["press_callbacks"]:
                        callback()

    def handle_key_release_event(self, event):
        for shortcut, value in self.shortcuts.items():
            if event.key() == value["key_value"]:
                for callback in value["release_callbacks"]:
                    callback()

    def initialize_events(self):
        self.app.wheelEvent = self.handle_wheel_event

    def handle_wheel_event(self, event):
        for callback in self.events["wheelEvent"]:
            callback(event)
