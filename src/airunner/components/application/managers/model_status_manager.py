# Status management logic for model managers
from airunner.enums import ModelType, ModelStatus


class StatusManagerMixin:
    def change_model_status(self, model: ModelType, status: ModelStatus):
        if model in self._model_status:
            self._model_status[model] = status
            self.api.change_model_status(model, status)
        else:
            self.logger.warning(
                f"Instance {id(self)}: Attempted to change status for model type {model.name} not defined in this handler's initial status."
            )
