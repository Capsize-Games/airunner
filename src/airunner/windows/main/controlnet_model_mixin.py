class ControlnetModelMixin:
    def __init__(self):
        self.data = None

    def controlnet_model_get_all(self):
        return self.settings["controlnet"]

    def controlnet_model_get_by_filter(self, filter_dict):
        return [item for item in self.data if all(item.get(k) == v for k, v in filter_dict.items())]

    def controlnet_model_create(self, item):
        self.data.append(item)

    def controlnet_model_update(self, item):
        for i, existing_item in enumerate(self.data):
            if existing_item['name'] == item['name']:
                self.data[i] = item
                break

    def controlnet_model_delete(self, item):
        self.data = [existing_item for existing_item in self.data if existing_item['name'] != item['name']]
    
    def controlnet_model_by_name(self, name):
        return [item for item in self.data if item["name"] == name][0]