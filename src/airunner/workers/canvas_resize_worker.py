from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPen

from airunner.aihandler.enums import QueueType
from airunner.workers.worker import Worker


class CanvasResizeWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM
    last_cell_count = (0, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register("canvas_resize_signal", self)
    
    def on_canvas_resize_signal(self, data):
        self.add_to_queue(data)
    
    def handle_message(self, data):
        if data is None:
            return
        settings = data["settings"]
        view_size = data["view_size"]

        cell_size = settings["grid_settings"]["cell_size"]
        line_color = settings["grid_settings"]["line_color"]
        line_width = settings["grid_settings"]["line_width"]

        width_cells = view_size.width() // cell_size
        height_cells = view_size.height() // cell_size

        # Check if the number of cells has changed
        if (width_cells, height_cells) == self.last_cell_count:
            return
        self.last_cell_count = (width_cells, height_cells)

        pen = QPen(
            QBrush(QColor(line_color)),
            line_width,
            Qt.PenStyle.SolidLine
        )
        
        lines_data = []

        # vertical lines
        h = view_size.height() + abs(settings["canvas_settings"]["pos_y"]) % cell_size
        y = 0
        x = settings["canvas_settings"]["pos_x"] % cell_size
        for i in range(width_cells):
            line_data = (x, y, x, h, pen)
            lines_data.append(line_data)
            x += cell_size

        # horizontal lines
        w = view_size.width() + abs(settings["canvas_settings"]["pos_x"]) % cell_size
        x = 0
        y = settings["canvas_settings"]["pos_y"] % cell_size
        for i in range(height_cells):
            line_data = (x, y, w, y, pen)
            lines_data.append(line_data)
            y += cell_size

        self.emit("canvas_clear_lines_signal")

        self.emit("CanvasResizeWorker_response_signal", lines_data)

        self.emit("canvas_do_draw_signal")
