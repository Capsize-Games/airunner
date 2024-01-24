from airunner.aihandler.transformer_base_handler import CasualLMTransformerBaseHandler


class LLMHandler(CasualLMTransformerBaseHandler):
    def clear_history(self):
        self.history = []
