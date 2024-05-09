from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class RagSearchWorker(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent = None
        self.register(SignalCode.LLM_RAG_SEARCH_SIGNAL, self.rag_search_request)

    def initialize(self, agent, model, tokenizer):
        self.agent = agent
        self.agent.load_rag(model, tokenizer)

    def rag_search_request(self, data: dict):
        self.add_to_queue(data)

    def handle_message(self, data: dict):
        self.logger.debug("RAG Search Worker is handling a message.")
        self.agent.perform_rag_search(
            prompt=data["message"],
            streaming=True
        )

