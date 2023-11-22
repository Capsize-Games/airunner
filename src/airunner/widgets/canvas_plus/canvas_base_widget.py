from airunner.widgets.base_widget import BaseWidget


class CanvasBaseWidget(BaseWidget):
    image = None
    image_backup = None
    previewing_filter = False

    def current_image(self):
        if self.previewing_filter:
            return self.image_backup.copy()
        return self.image
    
    def filter_with_filter(self, filter):
        return type(filter).__name__ in [
            "SaturationFilter", 
            "ColorBalanceFilter", 
            "RGBNoiseFilter", 
            "PixelFilter", 
            "HalftoneFilter", 
            "RegistrationErrorFilter"]

    def preview_filter(self, filter):
        image = self.current_image()
        if not image:
            return
        if not self.previewing_filter:
            self.image_backup = image.copy()
            self.previewing_filter = True
        else:
            image = self.image_backup.copy()
        if self.filter_with_filter:
            filtered_image = filter.filter(image)
        else:
            filtered_image = image.filter(filter)
        self.load_image_from_object(image=filtered_image)
    
    def cancel_filter(self):
        if self.image_backup:
            self.load_image_from_object(image=self.image_backup)
            self.image_backup = None
        self.previewing_filter = False
    
    def apply_filter(self, filter):
        self.previewing_filter = False
        self.image_backup = None

    def load_image_from_object(self, image):
        pass
