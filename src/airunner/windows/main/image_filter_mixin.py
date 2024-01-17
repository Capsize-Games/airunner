class ImageFilterMixin:
    def __init__(self, settings):
        super().__init__(settings["image_filters"])
    
    def image_filter_get_all(self):
        return self.settings["image_filters"]

    def image_filter_get_by_filter(self, filter_dict):
        return [item for item in self.data if all(item.get(k) == v for k, v in filter_dict.items())]

    def image_filter_create(self, item):
        self.data.append(item)

    def image_filter_update(self, item):
        for i, existing_item in enumerate(self.data):
            if existing_item['name'] == item['name']:
                self.data[i] = item
                break

    def image_filter_delete(self, item):
        self.data = [existing_item for existing_item in self.data if existing_item['name'] != item['name']]
    
    def image_filter_by_name(self, name):
        return [item for item in self.data if item["name"] == name][0]