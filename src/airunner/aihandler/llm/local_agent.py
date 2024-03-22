from transformers import LocalAgent as LocalAgentBase, StoppingCriteriaList
from transformers.tools.agents import StopSequenceCriteria

from airunner.utils import clear_memory


class LocalAgent(LocalAgentBase):
    def __init__(self, *args, **kwargs):
        self.restrict_tools_to_additional = kwargs.pop("restrict_tools_to_additional", False)
        super().__init__(
            *args,
            **kwargs,
        )
        if self.restrict_tools_to_additional:
            self._toolbox = kwargs.get("additional_tools")

    def clean_code_for_run(self, result):
        explanation, code = super().clean_code_for_run(result)
        code = code.replace("```", "").replace("</s>", "")
        code = code.replace("<|endoftext|>", "")
        return explanation, code

    def format_prompt(self, task, chat_mode=False):
        task = super().format_prompt(task, chat_mode=chat_mode)
        task = task.replace("</s>", "")
        return task

    def generate_one(self, prompt, stop):
        encoded_inputs = self.tokenizer(prompt, return_tensors="pt").to(self._model_device)
        src_len = encoded_inputs["input_ids"].shape[1]
        stopping_criteria = StoppingCriteriaList([StopSequenceCriteria(stop, self.tokenizer)])
        outputs = self.model.generate(
            encoded_inputs["input_ids"],
            max_new_tokens=200,
            stopping_criteria=stopping_criteria
        )

        result = self.tokenizer.decode(outputs[0].tolist()[src_len:])
        # Inference API returns the stop sequence
        for stop_seq in stop:
            if result.endswith(stop_seq):
                result = result[: -len(stop_seq)]
        return result

    def unload(self):
        self.model = None
        self.tokenizer = None
        clear_memory()

