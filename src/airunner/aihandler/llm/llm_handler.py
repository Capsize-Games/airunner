from airunner.aihandler.llm.casual_lm_transfformer_base_handler import CasualLMTransformerBaseHandler


class LLMHandler(CasualLMTransformerBaseHandler):
    def clear_history(self):
        self.history = []