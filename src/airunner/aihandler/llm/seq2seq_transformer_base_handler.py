from transformers import AutoModelForSeq2SeqLM

from airunner.aihandler.llm.transformer_base_handler import TransformerBaseHandler


class Seq2SeqTransformerBaseHandler(TransformerBaseHandler):
    def do_generate(self, prompt, chat_template):
        pass

    auto_class_ = AutoModelForSeq2SeqLM
