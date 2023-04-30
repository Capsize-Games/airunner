from PyQt6.QtGui import QColor, QPen, QPainter


class CanvasGridMixin:
    @property
    def active_grid_area_selected(self):
        return self.settings_manager.settings.current_tool.get() == "active_grid_area"

    @property
    def grid_size(self):
        return self.settings_manager.settings.size.get()

    def initialize(self):
        # Set the grid line color and thickness
        # convert self.settings_manager.settings.canvas_color.get() to QColor
        self.grid_pen = QPen(
            QColor(self.settings_manager.settings.line_color.get()),
            self.settings_manager.settings.line_width.get()
        )

    def update_grid_pen(self):
        self.grid_pen = QPen(
            QColor(self.settings_manager.settings.line_color.get()),
            self.settings_manager.settings.line_width.get()
        )
        self.update()

    def draw_grid(self, painter):
        if not self.settings_manager.settings.show_grid.get():
            return

        # Define the starting and ending coordinates for the grid lines
        start_x = self.pos_x % self.grid_size
        end_x = self.canvas_container.width()
        start_y = self.pos_y % self.grid_size
        end_y = self.canvas_container.height()

        line_width = self.settings_manager.settings.line_width.get()
        self.grid_pen.setWidth(line_width)
        # Draw horizontal grid lines
        y = start_y
        while y < end_y:
            painter.setPen(self.grid_pen)
            painter.drawLine(0, y, self.canvas_container.width(), y)
            y += self.grid_size

        # Draw vertical grid lines
        x = start_x
        while x < end_x:
            painter.setPen(self.grid_pen)
            painter.drawLine(x, 0, x, self.canvas_container.height())
            x += self.grid_size

    def paintEvent(self, event):
        # Draw the grid and any lines that have been drawn by the user
        # draw grid
        if not self.saving:
            painter = QPainter(self.canvas_container)
            self.draw_grid(painter)
            painter.end()
