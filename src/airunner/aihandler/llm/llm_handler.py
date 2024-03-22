from airunner.aihandler.llm.casual_lm_transfformer_base_handler import CausalLMTransformerBaseHandler


class LLMHandler(CausalLMTransformerBaseHandler):
    def clear_history(self):
        self.history = []