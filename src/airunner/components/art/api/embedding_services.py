from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.enums import SignalCode


class EmbeddingAPIServices(APIServiceBase):
    def delete(self, embedding_widget):
        self.emit_signal(
            SignalCode.EMBEDDING_DELETE_SIGNAL,
            {"embedding_widget": embedding_widget},
        )

    def update(self):
        self.emit_signal(SignalCode.EMBEDDING_UPDATE_SIGNAL)

    def get_all_results(self, embeddings):
        self.emit_signal(
            SignalCode.EMBEDDING_GET_ALL_RESULTS_SIGNAL,
            {"embeddings": embeddings},
        )
