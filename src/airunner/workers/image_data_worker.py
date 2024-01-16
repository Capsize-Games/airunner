from PyQt6.QtCore import pyqtSlot, pyqtSignal, QObject

from airunner.utils import auto_export_image
from airunner.aihandler.logger import Logger



class ImageDataWorker(QObject):
    logger = Logger(prefix="ImageDataWorker")
    finished = pyqtSignal()
    stop_progress_bar = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.running = False

    @pyqtSlot()
    def process(self):
        self.running = True
        while self.running:
            item = self.parent.image_data_queue.get()
            self.process_image_data(item)
    
    def stop(self):
        self.logger.info("Stopping")
        self.running = False
        self.finished.emit()
    
    def process_image_data(self, message):
        images = message["images"]
        data = message["data"]
        nsfw_content_detected = message["nsfw_content_detected"]
        self.parent.clear_status_message()
        self.parent.data = data
        if data["action"] == "txt2vid":
            return self.parent.video_handler(data)
        self.stop_progress_bar.emit()
        path = ""
        if self.parent.settings["auto_export_images"]:
            procesed_images = []
            for image in images:
                path, image = auto_export_image(
                    base_path=self.parent.settings["path_settings"]["base_path"],
                    image_path=self.parent.settings["path_settings"]["image_path"],
                    image_export_type=self.parent.settings["image_export_type"],
                    image=image, 
                    data=data, 
                    seed=data["options"]["seed"]
                )
                if path is not None:
                    self.parent.set_status_label(f"Image exported to {path}")
                procesed_images.append(image)
            images = procesed_images
        if nsfw_content_detected and self.parent.settings["nsfw_filter"]:
            self.parent.message_handler({
                "message": "Explicit content detected, try again.",
                "code": MessageCode.ERROR
            })

        images = self.parent.post_process_images(images)
        self.parent.image_data.emit({
            "images": images,
            "path": path,
            "data": data
        })
        self.parent.message_handler("")
        self.parent.ui.layer_widget.show_layers()
        self.parent.image_generated.emit(True)
