"""External condition stopping criteria for HuggingFace transformers."""

from transformers.generation.stopping_criteria import StoppingCriteria


class ExternalConditionStoppingCriteria(StoppingCriteria):
    """Stopping criteria that checks an external condition via a callable.

    This allows interrupting generation based on external state (e.g., user interrupt).
    """

    def __init__(self, external_condition_callable):
        """Initialize with a callable that returns True when generation should stop.

        Args:
            external_condition_callable: A callable that returns bool indicating
                whether generation should stop.
        """
        super().__init__()
        self.external_condition_callable = external_condition_callable

    def __call__(self, input_ids, scores, **kwargs):
        """Check if generation should stop.

        Args:
            input_ids: The input token IDs
            scores: The model scores
            **kwargs: Additional keyword arguments

        Returns:
            bool: True if generation should stop, False otherwise
        """
        return self.external_condition_callable()
