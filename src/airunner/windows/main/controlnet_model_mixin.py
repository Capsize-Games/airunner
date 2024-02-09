class ControlnetModelMixin:
    def __init__(self):
        self.data = None

    def controlnet_model_get_by_filter(self, filter_dict):
        return [item for item in self.data if all(item.get(k) == v for k, v in filter_dict.items())]

    def controlnet_model_create(self, item):
        controlnet_data = self.settings["controlnet"]
        controlnet_data.append(item)
        self.settings["controlnet"] = controlnet_data

    def controlnet_model_update(self, item):
        controlnet_data = self.settings["controlnet"]
        for i, existing_item in enumerate(controlnet_data):
            if existing_item['name'] == item['name']:
                controlnet_data[i] = item
                break
        self.settings["controlnet"] = controlnet_data

    def controlnet_model_delete(self, item):
        controlnet_data = self.settings["controlnet"]
        updated_data = [existing_item for existing_item in controlnet_data if existing_item['name'] != item['name']]
        self.settings["controlnet"] = updated_data
    
    def controlnet_model_by_name(self, name):
        controlnet_data = self.settings["controlnet"]
        return [item for item in controlnet_data if item["name"] == name.lower()][0]