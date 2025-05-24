# Status management logic for model managers
from airunner.enums import ModelType, ModelStatus


class StatusManagerMixin:
    def change_model_status(self, model: ModelType, status: ModelStatus):
        self.logger.debug(
            f"Instance {id(self)}: Attempting to change status for {model.name} to {status.name}"
        )
        if model in self._model_status:
            old_status = self._model_status.get(model, ModelStatus.UNLOADED)
            self._model_status[model] = status
            self.logger.info(
                f"Instance {id(self)}: Model {model.name} status changed from {old_status.name} to {status.name}"
            )
            self.api.change_model_status(model, status)
            self.logger.debug(
                f"Instance {id(self)}: Current status dict: {self._model_status}"
            )
        else:
            self.logger.warning(
                f"Instance {id(self)}: Attempted to change status for model type {model.name} not defined in this handler's initial status."
            )
