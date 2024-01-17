class AIModelMixin:
    def __init__(self, settings):
        super().__init__(settings["image_filters"])

    def ai_model_get_by_filter(self, filter_dict):
        return [item for item in self.settings["ai_models"] if all(item.get(k) == v for k, v in filter_dict.items())]

    def ai_model_create(self, item):
        settings = self.settings
        settings["ai_models"].append(item)
        self.settings = settings

    def ai_model_update(self, item):
        settings = self.settings
        for i, existing_item in enumerate(self.settings["ai_models"]):
            if existing_item['name'] == item['name']:
                settings["ai_models"][i] = item
                self.settings = settings
                break

    def ai_model_delete(self, item):
        settings = self.settings
        settings["ai_models"] = [existing_item for existing_item in self.settings["ai_models"] if existing_item['name'] != item['name']]
        self.settings = settings
    
    def available_model_names_by_section(self, section):
        return [model["name"] for model in self.settings["ai_models"] if model["section"] == section]

    def models_by_pipeline_action(self, pipeline_action):
        return [model for model in self.settings["ai_models"] if model["pipeline_action"] == pipeline_action]
    
    def find_models(self, search="", default=False):
        return [model for model in self.settings["ai_models"] if model["is_default"] == default and search.lower() in model["name"].lower()]

    def ai_model_get_disabled_default(self):
        return [model for model in self.settings["ai_models"] if model["is_default"] == True and model["enabled"] == False]

    def ai_model_save_or_update(self, model_data):
        # find the model by name and path, if it exists, update it, otherwise insert it
        existing_model = self.ai_model_get_by_filter({"name": model_data["name"], "path": model_data["path"]})
        if existing_model:
            self.ai_model_update(model_data)
        else:
            self.ai_model_create(model_data)
        
    def ai_model_paths(self):
        return [model["path"] for model in self.settings["ai_models"]]

    def ai_model_categories(self):
        return [model["category"] for model in self.settings["ai_models"]]
    
    def ai_model_pipeline_actions(self):
        return [model["pipeline_action"] for model in self.settings["ai_models"]]
    
    def ai_model_versions(self):
        return [model["version"] for model in self.settings["ai_models"]]
    
    def ai_model_available_models_by_category(self, category):
        return [model for model in self.settings["ai_models"] if model["category"] == category]

    def ai_model_by_name(self, name):
        return [model for model in self.settings["ai_models"] if model["name"] == name]