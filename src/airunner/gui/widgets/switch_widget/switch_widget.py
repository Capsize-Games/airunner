from PySide6.QtCore import QObject, QPropertyAnimation, QEasingCurve, Property, QPointF, Slot, QSize, Signal
from PySide6.QtGui import QGradient, QLinearGradient, QPalette, Qt, QPainter, QColor
from PySide6.QtWidgets import QAbstractButton, QApplication


class SwitchPrivate(QObject):
    def __init__(self, q, parent=None):
        QObject.__init__(self, parent=parent)
        self.mPointer = q
        self.mPosition = 0.0
        self.mGradient = QLinearGradient()
        self.mGradient.setSpread(QGradient.Spread.PadSpread)
        self.checked = False

        self.animation = QPropertyAnimation(self)
        self.animation.setTargetObject(self)
        self.animation.setPropertyName(b'position')
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutExpo)

        self.animation.finished.connect(self.mPointer.update)

    @Property(float)
    def position(self):
        return self.mPosition

    @position.setter
    def position(self, value):
        self.mPosition = value
        self.mPointer.update()

    def draw(self, painter):
        r = self.mPointer.rect()
        margin = r.height() / 10
        shadow = self.mPointer.palette().color(QPalette.ColorRole.Shadow)
        light = self.mPointer.palette().color(QPalette.ColorRole.Light)
        button = self.mPointer.palette().color(QPalette.ColorRole.Button)
        painter.setPen(Qt.PenStyle.NoPen)

        if self.mPointer.isEnabled() and self.checked:
            self.mGradient.setColorAt(0, Qt.GlobalColor.blue)
            self.mGradient.setColorAt(1, Qt.GlobalColor.blue)
        else:
            self.mGradient.setColorAt(0, shadow.darker(130))
            self.mGradient.setColorAt(1, light.darker(130))

        self.mGradient.setStart(0, r.height())
        self.mGradient.setFinalStop(0, 0)
        painter.setBrush(self.mGradient)
        painter.drawRoundedRect(r, r.height() / 2, r.height() / 2)

        self.mGradient.setColorAt(0, shadow.darker(140))
        self.mGradient.setColorAt(1, light.darker(160))
        self.mGradient.setStart(0, 0)
        self.mGradient.setFinalStop(0, r.height())
        painter.setBrush(self.mGradient)
        painter.drawRoundedRect(r.adjusted(margin, margin, -margin, -margin), r.height() / 2, r.height() / 2)

        self.mGradient.setColorAt(0, button.darker(130))
        self.mGradient.setColorAt(1, button)

        painter.setBrush(self.mGradient)

        x = r.height() / 2.0 + self.mPosition * (r.width() - r.height())
        painter.drawEllipse(QPointF(x, r.height() / 2), r.height() / 2 - margin, r.height() / 2 - margin)

    @Slot(bool, name='animate')
    def animate(self, checked):
        self.checked = checked
        self.animation.setDirection(
            QPropertyAnimation.Direction.Forward if checked else QPropertyAnimation.Direction.Backward
        )
        self.animation.start()


class SwitchWidget(QAbstractButton):
    toggled = Signal(bool)

    def __init__(self, parent=None):
        QAbstractButton.__init__(self, parent=parent)
        self.dPtr = SwitchPrivate(self)
        self.setCheckable(True)
        self.clicked.connect(self.dPtr.animate)
        self.clicked.connect(self.emitToggled)
        self._backgroundColor = QColor("blue")  # Initialize the internal attribute
        self.setChecked(False)
        self.dPtr.animate(False)

    def emitToggled(self, checked):
        self.toggled.emit(checked)

    def sizeHint(self):
        return QSize(84, 42)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.dPtr.draw(painter)

    @Property(QColor)
    def backgroundColor(self):
        return self._backgroundColor  # Return the internal attribute

    @backgroundColor.setter
    def backgroundColor(self, color):
        self._backgroundColor = color  # Set the internal attribute
        self.update()


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    w = SwitchWidget()
    w.setProperty("backgroundColor", QColor("blue"))
    w.show()
    sys.exit(app.exec_())
