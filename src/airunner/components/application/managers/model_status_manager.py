# Status management logic for model managers
from airunner.enums import ModelType, ModelStatus


class StatusManagerMixin:
    def change_model_status(self, model: ModelType, status: ModelStatus):
        if model in self._model_status:
            self._model_status[model] = status
            # Notify application-level API if available. Some managers may
            # be constructed in isolation during tests and lack an `api`
            # attribute; guard against that to avoid noisy exceptions.
            try:
                if hasattr(self, "api") and self.api is not None:
                    self.api.change_model_status(model, status)
            except Exception:
                # Swallow errors from callback to avoid breaking manager flow
                pass
        else:
            self.logger.warning(
                f"Instance {id(self)}: Attempted to change status for model type {model.name} not defined in this handler's initial status."
            )
