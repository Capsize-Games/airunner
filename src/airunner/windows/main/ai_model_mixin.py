from airunner.service_locator import ServiceLocator

from PyQt6.QtCore import pyqtSlot


class AIModelMixin:
    def __init__(self):
        services = [
            "ai_model_paths", 
            "ai_models_find", 
            "ai_model_categories", 
            "ai_model_pipeline_actions", 
            "ai_model_versions", 
            "ai_model_get_disabled_default", 
            "ai_model_get_all", 
            "ai_model_update", 
            "ai_model_get_by_filter", 
            "ai_model_names_by_section", 
            "ai_models_by_category", 
            "ai_model_by_name"
        ]

        for service in services:
            ServiceLocator.register(service, getattr(self, service))
        
        self.register("ai_model_save_or_update_signal", self)
        self.register("ai_model_delete_signal", self)
        self.register("ai_model_create_signal", self)

    def ai_model_get_by_filter(self, filter_dict):
        return [item for item in self.ai_models if all(item.get(k) == v for k, v in filter_dict.items())]

    @pyqtSlot(object)
    def on_ai_model_create_signal(self, item):
        settings = self.settings
        settings["ai_models"].append(item)
        self.settings = settings

    def ai_model_update(self, item):
        settings = self.settings
        for i, existing_item in enumerate(self.ai_models):
            if existing_item['name'] == item['name']:
                settings["ai_models"][i] = item
                self.settings = settings
                break

    @pyqtSlot(object)
    def on_ai_model_delete_signal(self, item):
        settings = self.settings
        settings["ai_models"] = [existing_item for existing_item in self.ai_models if existing_item['name'] != item['name']]
        self.settings = settings
    
    def ai_model_names_by_section(self, section):
        return [model["name"] for model in self.ai_models if model["section"] == section]

    def models_by_pipeline_action(self, pipeline_action):
        return [model for model in self.ai_models if model["pipeline_action"] == pipeline_action]
    
    def ai_models_find(self, search="", default=False):
        return [model for model in self.ai_models if model["is_default"] == default and search.lower() in model["name"].lower()]

    def ai_model_get_disabled_default(self):
        return [model for model in self.ai_models if model["is_default"] == True and model["enabled"] == False]

    @pyqtSlot(object)
    def on_ai_model_save_or_update_signal(self, model_data):
        # find the model by name and path, if it exists, update it, otherwise insert it
        existing_model = self.ai_model_get_by_filter({"name": model_data["name"], "path": model_data["path"]})
        if existing_model:
            self.ai_model_update(model_data)
        else:
            self.emit("ai_model_create_signal", model_data)
        
    def ai_model_paths(self, model_type=None, pipeline_action=None):
        models = self.ai_models
        if model_type:
            models = [model for model in models if "model_type" in model and model["model_type"] == model_type]
        if pipeline_action:
            models = [model for model in models if model["pipeline_action"] == pipeline_action]

        return [model["path"] for model in models]

    def ai_model_categories(self):
        return [model["category"] for model in self.ai_models]
    
    def ai_model_pipeline_actions(self):
        return [model["pipeline_action"] for model in self.ai_models]
    
    def ai_model_versions(self):
        return [model["version"] for model in self.ai_models]
    
    def ai_models_by_category(self, category):
        return [model for model in self.ai_models if model["category"] == category]

    def ai_model_by_name(self, name):
        try:
            return [model for model in self.ai_models if model["name"] == name][0]
        except Exception as e:
            self.logger.error(f"Error finding model by name: {name}")
    
    def ai_model_get_all(self):
        return self.ai_models