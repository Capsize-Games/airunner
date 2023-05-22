from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor


class CanvasActiveGridAreaMixin:
    active_grid_area_pivot_point = None

    @property
    def active_grid_area_color(self):
        if self.parent.current_section == "txt2img":
            brush_color = QColor(0, 255, 0)
        elif self.parent.current_section == "img2img":
            brush_color = QColor(255, 0, 0)
        elif self.parent.current_section == "depth2img":
            brush_color = QColor(0, 0, 255)
        elif self.parent.current_section == "pix2pix":
            brush_color = QColor(255, 255, 0)
        elif self.parent.current_section == "outpaint":
            brush_color = QColor(0, 255, 255)
        elif self.parent.current_section == "upscale":
            brush_color = QColor(255, 0, 155)
        elif self.parent.current_section == "superresolution":
            brush_color = QColor(255, 0, 255)
        elif self.parent.current_section == "controlnet":
            brush_color = QColor(255, 255, 255)
        else:
            brush_color = QColor(0, 0, 0)
        return brush_color

    @property
    def active_grid_area_rect(self):
        width = self.settings_manager.settings.working_width.get()
        height = self.settings_manager.settings.working_height.get()

        rect = QRect(
            self.active_grid_area_pivot_point.x(),
            self.active_grid_area_pivot_point.y(),
            self.active_grid_area_pivot_point.x() + width,
            self.active_grid_area_pivot_point.y() + height
        )

        # apply self.pos_x and self.pox_y to the rect
        rect.translate(self.pos_x, self.pos_y)

        return rect

    def initialize(self):
        self.active_grid_area_pivot_point = QPoint(0, 0)

    def paint_event(self, event):
        if not self.saving:
            painter = QPainter(self.canvas_container)
            self.draw_active_grid_area_container(painter)
            painter.end()

    def draw_active_grid_area_container(self, painter):
        """
        Draw a rectangle around the active grid area of
        """
        painter.setPen(self.grid_pen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        pen = QPen(
            self.active_grid_area_color,
            self.settings_manager.settings.line_width.get()
        )
        painter.setPen(pen)
        rect = QRect(
            self.active_grid_area_rect.x(),
            self.active_grid_area_rect.y(),
            self.settings_manager.settings.working_width.get(),
            self.settings_manager.settings.working_height.get()
        )
        painter.drawRect(rect)

        # draw a second rectangle around the active grid area
        # to make it more visible
        pen = QPen(
            self.active_grid_area_color,
            self.settings_manager.settings.line_width.get() + 1
        )
        painter.setPen(pen)
        size = 4
        rect = QRect(
            self.active_grid_area_rect.x() + size,
            self.active_grid_area_rect.y() + size,
            self.settings_manager.settings.working_width.get() - (size * 2),
            self.settings_manager.settings.working_height.get() - (size * 2)
        )
        painter.drawRect(rect)

        # draw a thirder black border in the center of the two rectangles
        pen = QPen(
            QColor(0, 0, 0),
            self.settings_manager.settings.line_width.get() + 1
        )
        painter.setPen(pen)
        size = 2
        rect = QRect(
            self.active_grid_area_rect.x() + size,
            self.active_grid_area_rect.y() + size,
            self.settings_manager.settings.working_width.get() - (size * 2),
            self.settings_manager.settings.working_height.get() - (size * 2)
        )
        painter.drawRect(rect)

    def reset_settings(self):
        self.window.width_slider.setValue(self.settings_manager.settings.working_width.get())
        self.window.height_slider.setValue(self.settings_manager.settings.working_height.get())
