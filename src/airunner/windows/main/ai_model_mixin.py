from airunner.service_locator import ServiceLocator
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data


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
        
        self.register("ai_models_save_or_update_signal", self)
        self.register("ai_model_delete_signal", self)
        self.register("ai_models_create_signal", self)

    def ai_model_get_by_filter(self, filter_dict):
        return [item for item in self.ai_models if all(item.get(k) == v for k, v in filter_dict.items())]

    def on_ai_model_create_signal(self, item):
        settings = self.settings
        settings["ai_models"].append(item)
        self.settings = settings

    def on_ai_models_create_signal(self, models):
        settings = self.settings
        settings["ai_models"] = models
        self.settings = settings
        self.emit("models_changed_signal", "models")

    def ai_model_update(self, item):
        settings = self.settings
        for i, existing_item in enumerate(self.ai_models):
            if existing_item['name'] == item['name']:
                settings["ai_models"][i] = item
                self.settings = settings
                break

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

    def on_ai_models_save_or_update_signal(self, new_models):
        settings = self.settings
        default_models = model_bootstrap_data
        existing_models = settings["ai_models"]

        # Convert list of models to dictionary with model name as key
        model_dict = {model['name']: model for model in default_models}

        # Update the dictionary with existing models
        model_dict.update({model['name']: model for model in existing_models})

        # Update the dictionary with new models
        model_dict.update({model['name']: model for model in new_models})

        # Convert back to list
        merged_models = list(model_dict.values())

        self.emit("ai_models_create_signal", merged_models)
        
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