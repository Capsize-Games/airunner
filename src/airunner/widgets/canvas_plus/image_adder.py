from PyQt6.QtCore import QThread, pyqtSignal


class ImageAdder(QThread):
    finished = pyqtSignal()

    def __init__(self, widget, image, is_outpaint, image_root_point):
        super().__init__()
        self.widget = widget
        self.image = image
        self.is_outpaint = is_outpaint
        self.image_root_point = image_root_point
        

    def run(self):
        self.widget.current_active_image = self.image
        # with self.widget.current_layer() as layer:
        #     if self.image_root_point is not None:
        #         layer.pos_x = self.image_root_point.x()
        #         layer.pos_y = self.image_root_point.y()
        #     elif not self.is_outpaint:
        #         layer.current_layer.pos_x = self.widget.active_grid_area_rect.x()
        #         layer.current_layer.pos_y = self.widget.active_grid_area_rect.y()
        self.widget.do_draw()
        self.finished.emit()

