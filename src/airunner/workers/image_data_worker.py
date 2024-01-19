from airunner.utils import auto_export_image
from airunner.workers.worker import Worker


class ImageDataWorker(Worker):
    def __init__(self, prefix):
        super().__init__(prefix=prefix)
        self.running = False

    def handle_message(self, message):
        images = message["images"]
        data = message["data"]
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
                procesed_images.append(image)
            images = procesed_images

        #images = self.post_process_images(images)
        super().handle_message(dict(
            images=images,
            path=path,
            data=data,
            nsfw_content_detected=message["nsfw_content_detected"],
        ))
        
    def post_process_images(self, images):
        #return self.automatic_filter_manager.apply_filters(images)
        return images
