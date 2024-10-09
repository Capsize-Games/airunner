from typing import List

from airunner.enums import SignalCode


class AIModelMixin:
    def ai_model_get_by_filter(self, filter_dict):
        return [item for item in self.ai_models if all(item.get(k) == v for k, v in filter_dict.items())]

    def on_ai_model_delete_signal(self, item: dict):
        self.ai_models = [existing_item for existing_item in self.ai_models if existing_item.name != item.name]
        self.update_settings("ai_models", self.ai_models)

    def ai_model_names_by_section(self, section) -> List[str]:
        return [model.name for model in self.ai_models if model.section == section]

    def models_by_pipeline_action(self, pipeline_action: str):
        val = [model for model in self.ai_models if model.pipeline_action == pipeline_action]
        return val
    
    def ai_models_find(self, search="", default=False):
        return [model for model in self.ai_models if model.is_default == default and search.lower() in model.name.lower()]

    def ai_model_get_disabled_default(self):
        return [model for model in self.ai_models if model.is_default is True and model.enabled is False]

    def on_ai_models_save_or_update_signal(self, data: dict):
        new_models = data.get("models", [])
        default_models = self.ai_models

        # Convert list of models to dictionary with model name as key
        model_dict = {model.name: model for model in default_models}

        # Update the dictionary with existing models
        # model_dict.update({model['name']: model for model in existing_models})

        # Update the dictionary with new models
        model_dict.update({model.name: model for model in new_models})

        # Convert back to list
        merged_models = list(model_dict.values())

        self.update_ai_models(merged_models)
        self.emit_signal(SignalCode.AI_MODELS_CREATE_SIGNAL)
        
    def ai_model_paths(self, model_type=None, pipeline_action=None):
        models = self.ai_models
        if model_type:
            models = [model for model in models if model.model_type == model_type]
        if pipeline_action:
            models = [model for model in models if model.pipeline_action == pipeline_action]

        return [model.path for model in models]

    def ai_model_categories(self):
        return [model.category for model in self.ai_models]
    
    def ai_model_pipeline_actions(self):
        return [model.pipeline_action for model in self.ai_models]
    
    def ai_model_versions(self):
        return [model.version for model in self.ai_models]
    
    def ai_models_by_category(self, category):
        return [model for model in self.ai_models if model.category == category]

    def ai_model_get_all(self):
        return self.ai_models
