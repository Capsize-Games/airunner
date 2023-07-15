from PyQt6.QtCore import QObject, pyqtSignal


class Var(QObject):
    my_signal = pyqtSignal()

    def __init__(self, app=None, default=None):
        super().__init__()
        self._app = app
        self.set(default, skip_save=True)

    def connect(self, callback):
        self.my_signal.connect(callback)

    def set(self, val, skip_save=False):
        self._my_variable = val
        self.emit()
        if self._app and not skip_save:
            try:
                self._app.save_settings()
            except Exception as e:
                print("Failed to save setting:", e)

    def get(self):
        return self._my_variable

    def emit(self):
        if self._my_variable is None:
            return
        self.my_signal.emit(self._my_variable)


class TQDMVar(Var):
    step = pyqtSignal(int)
    total = pyqtSignal(int)
    action = pyqtSignal(str)
    image = pyqtSignal(object)
    data = pyqtSignal(object)
    my_signal = pyqtSignal(int, int, str, object, object)

    def set(self, val, skip_save=False):
        if val is None:
            return
        self.step = val["step"]
        self.total = val["total"]
        self.action = val["action"]
        self.image = val["image"]
        self.data = val["data"]
        self.emit()

    def emit(self):
        self.my_signal.emit(self.step, self.total, self.action, self.image, self.data)


class MessageHandlerVar(QObject):
    my_signal = pyqtSignal(dict)

    def emit(self, message):
        self.my_signal.emit(message)


class ErrorHandlerVar(Var):
    message = pyqtSignal(str)
    my_signal = pyqtSignal(str)

    def set(self, val, skip_save=False):
        if val is None:
            return
        self.message = val
        self.emit()

    def emit(self):
        self.my_signal.emit(self.message)

class ImageVar(Var):
    images = pyqtSignal(object)
    data = pyqtSignal(object)
    nsfw_content_detected = pyqtSignal(bool)
    my_signal = pyqtSignal(object, object, bool)

    def set(self, val, skip_save=False):
        if val is None:
            return
        self.images = val["images"]
        self.data = val["data"]
        self.nsfw_content_detected = val["nsfw_content_detected"]
        self.emit()

    def emit(self):
        self.my_signal.emit(self.images, self.data, self.nsfw_content_detected)


class BooleanVar(Var):
    my_signal = pyqtSignal(bool)


class IntVar(Var):
    my_signal = pyqtSignal(int)


class FloatVar(Var):
    my_signal = pyqtSignal(float)


class StringVar(Var):
    my_signal = pyqtSignal(str)



class ListVar(Var):
    my_signal = pyqtSignal(list)

    def append(self, item):
        self._my_variable.append(item)
        self.emit()

    def remove(self, item):
        self._my_variable.remove(item)
        self.emit()


class DictVar(Var):
    my_signal = pyqtSignal(dict)


class DoubleVar(Var):
    my_signal = pyqtSignal(float)


class LoraVar(Var):
    my_signal = pyqtSignal(str, float, bool)

    def __init__(self, app=None, name="", scale=1.0, enabled=False):
        self.name = StringVar("")
        self.scale = FloatVar(1.0)
        self.enabled = BooleanVar(False)

        super().__init__(app, None)

        self.name.set(name, skip_save=True)
        self.scale.set(scale, skip_save=True)
        self.enabled.set(enabled, skip_save=True)

        self.name.my_signal.connect(self.emit)
        self.scale.my_signal.connect(self.emit)
        self.enabled.my_signal.connect(self.emit)

    def emit(self):
        name = self.name.get() if self.name.get() is not None else ""
        scale = self.scale.get() if self.scale.get() is not None else 1.0
        enabled = self.enabled.get() if self.enabled.get() is not None else False
        self.my_signal.emit(name, scale, enabled)


# TODO: extensions
class ExtensionVar(Var):
    name = StringVar("")
    description = StringVar("")
    repo = StringVar("")
    version = StringVar("")
    reviewed = BooleanVar(False)
    official = BooleanVar(False)
    enabled = BooleanVar(False)
    my_signal = pyqtSignal(str, bool)
    object = None

    def __init__(
        self,
        app=None,
        name="",
        description="",
        repo="",
        version="",
        reviewed=False,
        official=False,
        enabled=False
    ):
        super().__init__(app, None)
        self.name.set(name, skip_save=True)
        self.description.set(description, skip_save=True)
        self.repo.set(repo, skip_save=True)
        self.version.set(version, skip_save=True)
        self.reviewed.set(reviewed, skip_save=True)
        self.official.set(official, skip_save=True)
        self.enabled.set(enabled, skip_save=True)
        self.enabled.my_signal.connect(self.emit)

    def emit(self):
        self.my_signal.emit(self.name.get(), self.enabled.get() == True)
