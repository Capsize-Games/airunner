from PyQt6.QtCore import QObject, Qt


class ShortCut:
    @property
    def display_name(self):
        if self.modifiers is not Qt.KeyboardModifier.NoModifier:
            return f"{self.modifiers}+{self.display_name}"
        return self.display_name

    def __init__(
        self,
        key_value=None,
        modifiers=Qt.KeyboardModifier.NoModifier,
        press_callbacks=None,
        release_callbacks=None
    ):
        self.key_value = key_value
        self.modifiers = modifiers
        self.press_callbacks = [] if press_callbacks is None else press_callbacks
        self.release_callbacks = [] if release_callbacks is None else release_callbacks


class InputEventManager(QObject):
    events = {
        "wheelEvent": [],
    }

    shortcuts = {
        "generate": ShortCut(
            key_value=Qt.Key.Key_F5
        ),
        "fullscreen": ShortCut(
            key_value=Qt.Key.Key_F11
        ),
        "control_pressed": ShortCut(
            key_value=Qt.Key.Key_Control
        ),
        "shift_pressed": ShortCut(
            key_value=Qt.Key.Key_Shift
        ),
        "delete_outside_active_grid_area": ShortCut(
            key_value=Qt.Key.Key_Delete,
            modifiers=Qt.KeyboardModifier.ShiftModifier
        ),
        "brush_tool": ShortCut(
            key_value=Qt.Key.Key_B
        ),
        "eraser_tool": ShortCut(
            key_value=Qt.Key.Key_E
        ),
        "active_grid_area_tool": ShortCut(
            key_value=Qt.Key.Key_G
        ),
        "focus_canvas": ShortCut(
            key_value=Qt.Key.Key_F
        ),
        "toggle_grid": ShortCut(
            key_value=Qt.Key.Key_H
        ),
        "toggle_safety_checker": ShortCut(
            key_value=Qt.Key.Key_T
        ),
        "settings": ShortCut(
            key_value=Qt.Key.Key_S
        ),
        "undo": ShortCut(
            key_value=Qt.Key.Key_Z,
            modifiers=Qt.KeyboardModifier.ControlModifier
        ),
        "redo": ShortCut(
            key_value=Qt.Key.Key_Y,
            modifiers=Qt.KeyboardModifier.ControlModifier
        ),
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

    def set_shortcut(self, shortcut_name: str, key_value: Qt.Key, modifier: Qt.KeyboardModifier, press_callback, release_callback):
        """
        Create a new keyboard press / release shortcut
        :param shortcut_name:
        :param key_value:
        :param modifier:
        :param press_callback:
        :param release_callback:
        :return:
        """
        press_callbacks = [press_callback] if press_callback else []
        release_callbacks = [release_callback] if release_callback else []
        self.shortcuts[shortcut_name] = ShortCut(
            key_value=key_value,
            modifiers=modifier,
            press_callbacks=press_callbacks,
            release_callbacks=release_callbacks
        )

    def remap_shortcut(self, shortcut_name: str, key_value: Qt.Key = None, modifier: Qt.KeyboardModifier = None):
        """
        Remaps the keys of an existing shortcut
        :param shortcut_name:
        :param key_value:
        :param modifier:
        :return:
        """
        if shortcut_name not in self.shortcuts:
            raise KeyError(f"Shortcut {shortcut_name} does not exist.")

        if key_value is not None:
            self.shortcuts[shortcut_name].key_value = key_value

        if modifier is not None:
            self.shortcuts[shortcut_name].modifiers = modifier

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
                self.shortcuts[key].press_callbacks.append(press_callback)
            if release_callback:
                self.shortcuts[key].release_callbacks.append(release_callback)

    def initialize_shortcuts(self):
        self.app.keyPressEvent = self.handle_key_press_event
        self.app.keyReleaseEvent = self.handle_key_release_event

    def handle_key_press_event(self, event):
        for shortcut, value in self.shortcuts.items():
            if event.key() == value.key_value:
                modifier = value.modifiers
                if modifier != Qt.KeyboardModifier.NoModifier:
                    if event.modifiers() == modifier:
                        for callback in value.press_callbacks:
                            callback()
                else:
                    for callback in value.press_callbacks:
                        callback()

    def handle_key_release_event(self, event):
        for shortcut, value in self.shortcuts.items():
            if event.key() == value.key_value:
                for callback in value.release_callbacks:
                    callback()

    def initialize_events(self):
        self.app.wheelEvent = self.handle_wheel_event

    def handle_wheel_event(self, event):
        for callback in self.events["wheelEvent"]:
            callback(event)
