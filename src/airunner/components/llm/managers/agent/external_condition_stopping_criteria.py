from transformers.generation.stopping_criteria import StoppingCriteria


class ExternalConditionStoppingCriteria(StoppingCriteria):
    def __init__(self, external_condition_callable):
        super().__init__()
        self.external_condition_callable = external_condition_callable

    def __call__(self, inputs_ids, scores):
        return self.external_condition_callable()
