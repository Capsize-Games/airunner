from airunner.enums import SignalCode, GeneratorSection, ImageGenerator, StableDiffusionVersion
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data


class AIModelMixin:
    def __init__(self):
        self.settings = None
        self.settings = None
        self.settings = None
        self.settings = None

    def ai_model_get_by_filter(self, filter_dict):
        return [item for item in self.settings["ai_models"] if all(item.get(k) == v for k, v in filter_dict.items())]

    def on_ai_model_create_signal(self, item):
        settings = self.settings
        settings["ai_models"].append(item)
        self.settings = settings

    def on_ai_models_create_signal(self, data: dict):
        models = data["models"]
        settings = self.settings
        settings["ai_models"] = models
        self.settings = settings
        self.emit_signal(SignalCode.APPLICATION_MODELS_CHANGED_SIGNAL, data)

    def ai_model_update(self, item):
        settings = self.settings
        for i, existing_item in enumerate(self.settings["ai_models"]):
            if existing_item['name'] == item['name']:
                settings["ai_models"][i] = item
                self.settings = settings
                break

    def on_ai_model_delete_signal(self, item: dict):
        settings = self.settings
        settings["ai_models"] = [existing_item for existing_item in self.settings["ai_models"] if existing_item['name'] != item['name']]
        self.settings = settings
    
    def ai_model_names_by_section(self, section):
        return [model["name"] for model in self.settings["ai_models"] if model["section"] == section]

    def models_by_pipeline_action(self, pipeline_action):
        val = [model for model in self.settings["ai_models"] if model.get("pipeline_action", ImageGenerator.STABLEDIFFUSION) == pipeline_action]
        return val
    
    def ai_models_find(self, search="", default=False):
        return [model for model in self.settings["ai_models"] if model.get("is_default", False) == default and search.lower() in model["name"].lower()]

    def ai_model_get_disabled_default(self):
        return [model for model in self.settings["ai_models"] if model.get("is_default", False) == True and model["enabled"] == False]

    def on_ai_models_save_or_update_signal(self, data: dict):
        new_models = data.get("models", [])
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

        settings["ai_models"] = merged_models
        self.settings = settings

        self.emit_signal(SignalCode.AI_MODELS_CREATE_SIGNAL, {
            "models": merged_models
        })
        
    def ai_model_paths(self, model_type=None, pipeline_action=None):
        models = self.settings["ai_models"]
        if model_type:
            models = [model for model in models if "model_type" in model and model["model_type"] == model_type]
        if pipeline_action:
            models = [model for model in models if model["pipeline_action"] == pipeline_action]

        return [model["path"] for model in models]

    def ai_model_categories(self):
        return [model.get("category", ImageGenerator.STABLEDIFFUSION) for model in self.settings["ai_models"]]
    
    def ai_model_pipeline_actions(self):
        return [model.get("pipeline_action", GeneratorSection.TXT2IMG) for model in self.settings["ai_models"]]
    
    def ai_model_versions(self):
        return [model.get("version", StableDiffusionVersion.SD1_5) for model in self.settings["ai_models"]]
    
    def ai_models_by_category(self, category):
        return [model for model in self.settings["ai_models"] if model["category"] == category]

    def ai_model_get_all(self):
        return self.settings["ai_models"]
