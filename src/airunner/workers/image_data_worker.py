from airunner.utils import auto_export_image
from airunner.workers.worker import Worker


class ImageDataWorker(Worker):
    def __init__(self, prefix):
        super().__init__(prefix=prefix)
        self.running = False

    def handle_message(self, incoming_message):
        auto_export_images = incoming_message["auto_export_images"]
        base_path = incoming_message["base_path"]
        image_path = incoming_message["image_path"]
        image_export_type = incoming_message["image_export_type"]
        message = incoming_message["image_data"]
        images = message["images"]
        data = message["data"]
        path = ""
        if auto_export_images:
            procesed_images = []
            for image in images:
                path, image = auto_export_image(
                    base_path=base_path,
                    image_path=image_path,
                    image_export_type=image_export_type,
                    image=image["image"], 
                    data=data, 
                    seed=data["options"]["seed"]
                )
                procesed_images.append(image)
            images = procesed_images

        #images = self.post_process_images(images)
        super().handle_message({
            'images': images,
            'path': path,
            'data': data,
            'nsfw_content_detected': message["nsfw_content_detected"],
        })
        
    def post_process_images(self, images):
        #return self.automatic_filter_manager.apply_filters(images)
        return images
