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
    _input_ports = [
        dict(name="do_sample", display_name="Do Sample"),
        dict(name="early_stopping", display_name="Early Stopping"),
        dict(name="eta_cutoff", display_name="ETA Cutoff"),
        dict(name="length_penalty", display_name="Length Penalty"),
        dict(name="max_new_tokens", display_name="Max New Tokens"),
        dict(name="min_length", display_name="Min Length"),
        dict(name="no_repeat_ngram_size", display_name="No Repeat Ngram Size"),
        dict(name="num_beams", display_name="Num Beams"),
        dict(name="num_return_sequences", display_name="Num Return Sequences"),
        dict(name="repetition_penalty", display_name="Repetition Penalty"),
        dict(name="temperature", display_name="Temperature"),
        dict(name="top_k", display_name="Top K"),
        dict(name="top_p", display_name="Top P"),
        dict(name="use_cache", display_name="Use Cache"),
        dict(name="do_tts_reply", display_name="Do TTS Reply"),
        dict(
            name="decoder_start_token_id",
            display_name="Decoder Start Token ID",
        ),
        dict(name="use_memory", display_name="Use Memory"),
    ]
    _output_ports = [
        dict(name="llm_request", display_name="LLM Request"),
    ]
    _properties = [
        dict(
            name="do_sample",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="generation",
        ),
        dict(
            name="early_stopping",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="generation",
        ),
        dict(
            name="use_cache",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="generation",
        ),
        dict(
            name="do_tts_reply",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="generation",
        ),
        dict(
            name="eta_cutoff",
            value=200,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 1000),
            tab="advanced",
        ),
        dict(
            name="max_new_tokens",
            value=200,
            widget_type=NodePropWidgetEnum.INT,
            range=(1, 2048),
            tab="generation",
        ),
        dict(
            name="min_length",
            value=1,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 100),
            tab="generation",
        ),
        dict(
            name="no_repeat_ngram_size",
            value=2,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 10),
            tab="advanced",
        ),
        dict(
            name="num_beams",
            value=1,
            widget_type=NodePropWidgetEnum.INT,
            range=(1, 10),
            tab="generation",
        ),
        dict(
            name="num_return_sequences",
            value=1,
            widget_type=NodePropWidgetEnum.INT,
            range=(1, 5),
            tab="generation",
        ),
        dict(
            name="repetition_penalty",
            value=1.0,
            widget_type=NodePropWidgetEnum.FLOAT,
            range=(0.0, 5.0),
            tab="advanced",
        ),
        dict(
            name="temperature",
            value=1.0,
            widget_type=NodePropWidgetEnum.FLOAT,
            range=(0.0, 2.0),
            tab="generation",
        ),
        dict(
            name="top_k",
            value=50,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 100),
            tab="advanced",
        ),
        dict(
            name="top_p",
            value=0.9,
            widget_type=NodePropWidgetEnum.FLOAT,
            range=(0.0, 1.0),
            tab="advanced",
        ),
        dict(
            name="decoder_start_token_id",
            value=None,  # Default to None
            widget_type=NodePropWidgetEnum.INT,
            range=(-1, 100000),  # Allow -1 or None equivalent for optionality
            tab="advanced",
        ),
        dict(
            name="use_memory",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="advanced",
        ),
        dict(
            name="use_tts_reply",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="advanced",
        ),
    ]

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
