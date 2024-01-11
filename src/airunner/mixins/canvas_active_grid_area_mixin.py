from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor


class CanvasActiveGridAreaMixin:
    active_grid_area_pivot_point = None

    @property
    def active_grid_area_color(self):
        current_tab = self.app.settings_manager.current_tab
        if current_tab == "stablediffusion":
            current_section = self.app.settings_manager.current_section_stablediffusion

        if current_section == "txt2img":
            brush_color = QColor(0, 255, 0)
        elif current_section == "img2img":
            brush_color = QColor(255, 0, 0)
        elif current_section == "depth2img":
            brush_color = QColor(0, 0, 255)
        elif current_section == "pix2pix":
            brush_color = QColor(255, 255, 0)
        elif current_section == "outpaint":
            brush_color = QColor(0, 255, 255)
        elif current_section == "upscale":
            brush_color = QColor(255, 0, 155)
        elif current_section == "superresolution":
            brush_color = QColor(255, 0, 255)
        elif current_section == "controlnet":
            brush_color = QColor(255, 255, 255)
        elif current_section == "txt2vid":
            brush_color = QColor(144, 144, 144)
        else:
            brush_color = QColor(0, 0, 0)
        return brush_color

    @property
    def active_grid_area_rect(self):
        width = self.app.settings_manager.working_width
        height = self.app.settings_manager.working_height

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
            self.app.settings_manager.grid_settings.line_width
        )
        painter.setPen(pen)
        rect = QRect(
            self.active_grid_area_rect.x(),
            self.active_grid_area_rect.y(),
            self.app.settings_manager.working_width,
            self.app.settings_manager.working_height
        )
        painter.drawRect(rect)

        # draw a second rectangle around the active grid area
        # to make it more visible
        pen = QPen(
            self.active_grid_area_color,
            self.app.settings_manager.grid_settings.line_width + 1
        )
        painter.setPen(pen)
        size = 4
        rect = QRect(
            self.active_grid_area_rect.x() + size,
            self.active_grid_area_rect.y() + size,
            self.app.settings_manager.working_width - (size * 2),
            self.app.settings_manager.working_height - (size * 2)
        )
        painter.drawRect(rect)

        # draw a third black border in the center of the two rectangles
        pen = QPen(
            QColor(0, 0, 0),
            self.app.settings_manager.grid_settings.line_width + 1
        )
        painter.setPen(pen)
        size = 2
        rect = QRect(
            self.active_grid_area_rect.x() + size,
            self.active_grid_area_rect.y() + size,
            self.app.settings_manager.working_width - (size * 2),
            self.app.settings_manager.working_height - (size * 2)
        )
        painter.drawRect(rect)

    def reset_settings(self):
        self.width_slider.setValue(self.app.settings_manager.working_width)
        self.height_slider.setValue(self.app.settings_manager.working_height)
