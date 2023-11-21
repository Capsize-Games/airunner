from airunner.widgets.base_widget import BaseWidget


class CanvasBaseWidget(BaseWidget):
    image = None
    image_backup = None

    def current_image(self):
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
        self.image_backup = image.copy()
        if self.filter_with_filter:
            filtered_image = filter.filter(image)
        else:
            filtered_image = image.filter(filter)
        self.load_image_from_object(image=filtered_image)
    
    def cancel_filter(self):
        print("CANCEL")
        if self.image_backup:
            self.load_image_from_object(image=self.image_backup)
            self.image_backup = None
    
    def apply_filter(self, filter):
        pass

    def load_image_from_object(self, image):
        pass
