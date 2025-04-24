from typing import Dict, Optional
import inspect

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.llm.base_llm_node import (
    BaseLLMNode,
)
from airunner.handlers.llm.llm_request import LLMRequest


class LLMRequestNode(BaseLLMNode):
    """
    A node that outputs an LLMRequest object with configurable parameters.

    This node provides input ports for all LLMRequest parameters and outputs
    a properly constructed LLMRequest object.
    """

    NODE_NAME = "LLM Request"
    has_exec_in_port: bool = False
    has_exec_out_port: bool = False

    def __init__(self):
        super().__init__()

        # Add inputs for all LLMRequest parameters
        self.add_input("do_sample", display_name=True)
        self.add_input("early_stopping", display_name=True)
        self.add_input("eta_cutoff", display_name=True)
        self.add_input("length_penalty", display_name=True)
        self.add_input("max_new_tokens", display_name=True)
        self.add_input("min_length", display_name=True)
        self.add_input("no_repeat_ngram_size", display_name=True)
        self.add_input("num_beams", display_name=True)
        self.add_input("num_return_sequences", display_name=True)
        self.add_input("repetition_penalty", display_name=True)
        self.add_input("temperature", display_name=True)
        self.add_input("top_k", display_name=True)
        self.add_input("top_p", display_name=True)
        self.add_input("use_cache", display_name=True)
        self.add_input("do_tts_reply", display_name=True)
        self.add_input("decoder_start_token_id", display_name=True)
        self.add_input("use_memory", display_name=True)

        # Add output port for the LLMRequest object
        self.add_output("llm_request")

        # Boolean parameters using built-in checkbox widget
        self.create_property(
            "do_sample",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="generation",
        )

        self.create_property(
            "early_stopping",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="generation",
        )

        self.create_property(
            "use_cache",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="generation",
        )

        self.create_property(
            "do_tts_reply",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="generation",
        )

        # Integer parameters using built-in integer widget
        self.create_property(
            "eta_cutoff",
            200,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 1000),
            tab="advanced",
        )

        self.create_property(
            "max_new_tokens",
            200,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(1, 2048),
            tab="generation",
        )

        self.create_property(
            "min_length",
            1,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 100),
            tab="generation",
        )

        self.create_property(
            "no_repeat_ngram_size",
            2,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 10),
            tab="advanced",
        )

        self.create_property(
            "num_beams",
            1,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(1, 10),
            tab="generation",
        )

        self.create_property(
            "num_return_sequences",
            1,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(1, 5),
            tab="generation",
        )

        self.create_property(
            "top_k",
            50,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 100),
            tab="advanced",
        )

        self.create_property(
            "decoder_start_token_id",
            None,  # Default to None
            widget_type=NodePropWidgetEnum.INT.value,
            range=(-1, 100000),  # Allow -1 or None equivalent for optionality
            tab="advanced",
        )

        self.create_property(
            "use_memory",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="advanced",
        )

        # Float parameters using built-in float widget
        self.create_property(
            "length_penalty",
            1.0,
            widget_type=NodePropWidgetEnum.FLOAT.value,
            range=(0.0, 5.0),
            tab="advanced",
        )

        self.create_property(
            "repetition_penalty",
            1.0,
            widget_type=NodePropWidgetEnum.FLOAT.value,
            range=(0.0, 5.0),
            tab="advanced",
        )

        self.create_property(
            "temperature",
            1.0,
            widget_type=NodePropWidgetEnum.FLOAT.value,
            range=(0.0, 2.0),
            tab="generation",
        )

        self.create_property(
            "top_p",
            0.9,
            widget_type=NodePropWidgetEnum.FLOAT.value,
            range=(0.0, 1.0),
            tab="advanced",
        )

    def execute(self, input_data: Dict):
        """
        Execute the node to create and output an LLMRequest object.

        Args:
            input_data: Dictionary containing input values from connected nodes.

        Returns:
            dict: A dictionary with the key 'llm_request' containing the LLMRequest object.
        """
        # Get values from inputs or use defaults from widget properties
        do_sample = self._get_value(input_data, "do_sample", bool)
        early_stopping = self._get_value(input_data, "early_stopping", bool)
        eta_cutoff = self._get_value(input_data, "eta_cutoff", int)
        length_penalty = self._get_value(input_data, "length_penalty", float)
        max_new_tokens = self._get_value(input_data, "max_new_tokens", int)
        min_length = self._get_value(input_data, "min_length", int)
        no_repeat_ngram_size = self._get_value(
            input_data, "no_repeat_ngram_size", int
        )
        num_beams = self._get_value(input_data, "num_beams", int)
        num_return_sequences = self._get_value(
            input_data, "num_return_sequences", int
        )
        repetition_penalty = self._get_value(
            input_data, "repetition_penalty", float
        )
        temperature = self._get_value(input_data, "temperature", float)
        top_k = self._get_value(input_data, "top_k", int)
        top_p = self._get_value(input_data, "top_p", float)
        use_cache = self._get_value(input_data, "use_cache", bool)
        do_tts_reply = self._get_value(input_data, "do_tts_reply", bool)
        decoder_start_token_id = self._get_value(
            input_data, "decoder_start_token_id", int, allow_none=True
        )
        use_memory = self._get_value(input_data, "use_memory", bool)

        # Instead of passing all parameters, filter to only those accepted by LLMRequest
        llm_request_args = inspect.signature(LLMRequest.__init__).parameters
        llm_request_kwargs = {
            k: v
            for k, v in {
                "do_sample": do_sample,
                "early_stopping": early_stopping,
                "eta_cutoff": eta_cutoff,
                "length_penalty": length_penalty,
                "max_new_tokens": max_new_tokens,
                "min_length": min_length,
                "no_repeat_ngram_size": no_repeat_ngram_size,
                "num_beams": num_beams,
                "num_return_sequences": num_return_sequences,
                "repetition_penalty": repetition_penalty,
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "use_cache": use_cache,
                "do_tts_reply": do_tts_reply,
                "decoder_start_token_id": decoder_start_token_id,
                "use_memory": use_memory,
            }.items()
            if k in llm_request_args
        }
        llm_request = LLMRequest(**llm_request_kwargs)

        return {"llm_request": llm_request}

    def _get_value(self, input_data, name, expected_type, allow_none=False):
        """
        Get a value from input data or fall back to the node property.

        Args:
            input_data: Dictionary containing input values.
            name: Name of the parameter.
            expected_type: Type to convert the value to.
            allow_none: If True, allow None as a valid value.

        Returns:
            The value converted to the expected type, or None if allowed.
        """
        if name in input_data and input_data[name] is not None:
            value = input_data[name]
            if allow_none and value is None:
                return None
            # Handle potential string representation of None from input
            if isinstance(value, str) and value.lower() == "none":
                if allow_none:
                    return None
                else:  # Fallback to property if None is not allowed but received
                    value = self.get_property(name)
            elif expected_type == bool:
                return bool(value)
            elif expected_type == int:
                # Allow -1 from property to represent None if allow_none is True
                val_int = int(value)
                if allow_none and val_int == -1:
                    return None
                return val_int
            elif expected_type == float:
                return float(value)
            return value  # Return as is if no specific type conversion needed or already handled
        else:  # Value not in input_data or is None
            value = self.get_property(name)
            if allow_none and (
                value is None or (expected_type == int and value == -1)
            ):
                return None
            if expected_type == bool:
                return bool(value)
            elif expected_type == int:
                # Convert property value, handling potential None or -1 for optional int
                val_int = (
                    int(value) if value is not None else -1
                )  # Default to -1 if property is None
                if allow_none and val_int == -1:
                    return None
                return val_int
            elif expected_type == float:
                return (
                    float(value) if value is not None else 0.0
                )  # Default float if property is None
            return value
