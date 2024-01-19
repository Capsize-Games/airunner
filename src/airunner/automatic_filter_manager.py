class FilterData:
    class_name = None
    filter_object = None
    options = {}

    def __init__(self, class_name, options):
        self.class_name = class_name
        self.options = options
        self.filter_object = class_name(**options)

    def apply_filter(self, image):
        return self.filter_object.filter(image)


class AutomaticFilterManager:
    registered_filters = []

    def register_filter(self, class_name, **options):
        self.registered_filters.append(FilterData(class_name, options))

    def apply_filters(self, images: list):
        return list(map(self.apply_filters_to_image, images))

    def apply_filters_to_image(self, image):
        for filter_data in self.registered_filters:
            image = filter_data.apply_filter(image)
        return image
