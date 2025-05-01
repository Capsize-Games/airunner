from typing import Dict

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.llm.base_llm_node import (
    BaseLLMNode,
)
from airunner.settings import (
    AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT,
    AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT,
    AIRUNNER_DEFAULT_LLM_HF_PATH,
)
from airunner.enums import Gender


class ChatbotNode(BaseLLMNode):
    """
    A node that outputs a Chatbot configuration as a dictionary.

    This node provides input ports for all Chatbot model parameters and outputs
    a dictionary with the chatbot configuration.
    """

    NODE_NAME = "Chatbot"
    _input_ports = [
        dict(name="name", display_name="Name"),
        dict(name="botname", display_name="Bot Name"),
        dict(name="use_personality", display_name="Use Personality"),
        dict(name="use_mood", display_name="Use Mood"),
        dict(name="use_guardrails", display_name="Use Guardrails"),
        dict(
            name="use_system_instructions",
            display_name="Use System Instructions",
        ),
        dict(name="use_datetime", display_name="Use DateTime"),
        dict(name="assign_names", display_name="Assign Names"),
        dict(name="bot_personality", display_name="Bot Personality"),
        dict(name="prompt_template", display_name="Prompt Template"),
        dict(name="use_tool_filter", display_name="Use Tool Filter"),
        dict(name="use_gpu", display_name="Use GPU"),
        dict(name="skip_special_tokens", display_name="Skip Special Tokens"),
        dict(name="sequences", display_name="Sequences"),
        dict(name="seed", display_name="Seed"),
        dict(name="random_seed", display_name="Random Seed"),
        dict(name="model_version", display_name="Model Version"),
        dict(name="model_type", display_name="Model Type"),
        dict(name="dtype", display_name="Data Type"),
        dict(name="return_result", display_name="Return Result"),
        dict(name="guardrails_prompt", display_name="Guardrails Prompt"),
        dict(name="system_instructions", display_name="System Instructions"),
        dict(name="top_p", display_name="Top P"),
        dict(name="min_length", display_name="Min Length"),
        dict(name="max_new_tokens", display_name="Max New Tokens"),
        dict(name="repetition_penalty", display_name="Repetition Penalty"),
        dict(name="do_sample", display_name="Do Sample"),
        dict(name="early_stopping", display_name="Early Stopping"),
        dict(name="num_beams", display_name="Num Beams"),
        dict(name="temperature", display_name="Temperature"),
        dict(name="ngram_size", display_name="Ngram Size"),
        dict(name="top_k", display_name="Top K"),
        dict(name="eta_cutoff", display_name="Eta Cutoff"),
        dict(name="num_return_sequences", display_name="Num Return Sequences"),
        dict(
            name="decoder_start_token_id",
            display_name="Decoder Start Token ID",
        ),
        dict(name="use_cache", display_name="Use Cache"),
        dict(name="length_penalty", display_name="Length Penalty"),
        dict(name="backstory", display_name="Backstory"),
        dict(name="use_backstory", display_name="Use Backstory"),
        dict(name="use_weather_prompt", display_name="Use Weather Prompt"),
        dict(name="gender", display_name="Gender"),
        dict(name="voice_id", display_name="Voice ID"),
    ]
    _output_ports = [
        dict(name="chatbot_config", display_name="Chatbot Config"),
    ]
    _properties = [
        dict(
            name="chatbot_name",
            value="Chatbot",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="basic",
        ),
        dict(
            name="botname",
            value="Computer",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="basic",
        ),
        dict(
            name="bot_personality",
            value="happy. He loves {{ username }}",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT,
            tab="personality",
        ),
        dict(
            name="prompt_template",
            value="Mistral 7B Instruct: Default Chatbot",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="basic",
        ),
        dict(
            name="model_version",
            value=AIRUNNER_DEFAULT_LLM_HF_PATH,
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="model",
        ),
        dict(
            name="model_type",
            value="llm",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="model",
        ),
        dict(
            name="dtype",
            value="4bit",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="model",
        ),
        dict(
            name="guardrails_prompt",
            value=AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT,
            widget_type=NodePropWidgetEnum.QTEXT_EDIT,
            tab="prompts",
        ),
        dict(
            name="system_instructions",
            value=AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT,
            widget_type=NodePropWidgetEnum.QTEXT_EDIT,
            tab="prompts",
        ),
        dict(
            name="backstory",
            value="",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT,
            tab="personality",
        ),
        dict(
            name="gender",
            value="male",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="voice",
        ),
        dict(
            name="use_mood",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="personality",
        ),
        dict(
            name="use_guardrails",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="prompts",
        ),
        dict(
            name="use_system_instructions",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="prompts",
        ),
        dict(
            name="use_datetime",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="basic",
        ),
        dict(
            name="assign_names",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="basic",
        ),
        dict(
            name="use_tool_filter",
            value=False,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="advanced",
        ),
        dict(
            name="use_gpu",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="model",
        ),
        dict(
            name="skip_special_tokens",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="model",
        ),
        dict(
            name="random_seed",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="generation",
        ),
        dict(
            name="return_result",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="basic",
        ),
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
            tab="model",
        ),
        dict(
            name="use_backstory",
            value=True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="personality",
        ),
        dict(
            name="use_weather_prompt",
            value=False,
            widget_type=NodePropWidgetEnum.QCHECK_BOX,
            tab="prompts",
        ),
        dict(
            name="sequences",
            value=1,
            widget_type=NodePropWidgetEnum.INT,
            range=(1, 10),
            tab="generation",
        ),
        dict(
            name="seed",
            value=42,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 999999),
            tab="generation",
        ),
        dict(
            name="top_p",
            value=900,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 1000),
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
            name="max_new_tokens",
            value=1000,
            widget_type=NodePropWidgetEnum.INT,
            range=(1, 2048),
            tab="generation",
        ),
        dict(
            name="repetition_penalty",
            value=100,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 200),
            tab="generation",
        ),
        dict(
            name="num_beams",
            value=1,
            widget_type=NodePropWidgetEnum.INT,
            range=(1, 10),
            tab="generation",
        ),
        dict(
            name="temperature",
            value=1000,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 2000),
            tab="generation",
        ),
        dict(
            name="ngram_size",
            value=2,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 10),
            tab="generation",
        ),
        dict(
            name="top_k",
            value=10,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 100),
            tab="generation",
        ),
        dict(
            name="eta_cutoff",
            value=10,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 100),
            tab="advanced",
        ),
        dict(
            name="num_return_sequences",
            value=1,
            widget_type=NodePropWidgetEnum.INT,
            range=(1, 5),
            tab="generation",
        ),
        dict(
            name="decoder_start_token_id",
            value=None,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 1000),
            tab="advanced",
        ),
        dict(
            name="length_penalty",
            value=100,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 200),
            tab="generation",
        ),
        dict(
            name="voice_id",
            value=None,
            widget_type=NodePropWidgetEnum.INT,
            range=(0, 1000),
            tab="voice",
        ),
    ]

    def execute(self, input_data: Dict):
        """
        Execute the node to create and output a Chatbot configuration dictionary.

        Args:
            input_data: Dictionary containing input values from connected nodes.

        Returns:
            dict: A dictionary with the key 'chatbot_config' containing the chatbot configuration.
        """
        # Get values from inputs or use defaults from widget properties
        chatbot_config = {
            "name": self._get_value(input_data, "name", str),
            "botname": self._get_value(input_data, "botname", str),
            "use_personality": self._get_value(
                input_data, "use_personality", bool
            ),
            "use_mood": self._get_value(input_data, "use_mood", bool),
            "use_guardrails": self._get_value(
                input_data, "use_guardrails", bool
            ),
            "use_system_instructions": self._get_value(
                input_data, "use_system_instructions", bool
            ),
            "use_datetime": self._get_value(input_data, "use_datetime", bool),
            "assign_names": self._get_value(input_data, "assign_names", bool),
            "bot_personality": self._get_value(
                input_data, "bot_personality", str
            ),
            "prompt_template": self._get_value(
                input_data, "prompt_template", str
            ),
            "use_tool_filter": self._get_value(
                input_data, "use_tool_filter", bool
            ),
            "use_gpu": self._get_value(input_data, "use_gpu", bool),
            "skip_special_tokens": self._get_value(
                input_data, "skip_special_tokens", bool
            ),
            "sequences": self._get_value(input_data, "sequences", int),
            "seed": self._get_value(input_data, "seed", int),
            "random_seed": self._get_value(input_data, "random_seed", bool),
            "model_version": self._get_value(input_data, "model_version", str),
            "model_type": self._get_value(input_data, "model_type", str),
            "dtype": self._get_value(input_data, "dtype", str),
            "return_result": self._get_value(
                input_data, "return_result", bool
            ),
            "guardrails_prompt": self._get_value(
                input_data, "guardrails_prompt", str
            ),
            "system_instructions": self._get_value(
                input_data, "system_instructions", str
            ),
            "top_p": self._get_value(input_data, "top_p", int),
            "min_length": self._get_value(input_data, "min_length", int),
            "max_new_tokens": self._get_value(
                input_data, "max_new_tokens", int
            ),
            "repetition_penalty": self._get_value(
                input_data, "repetition_penalty", int
            ),
            "do_sample": self._get_value(input_data, "do_sample", bool),
            "early_stopping": self._get_value(
                input_data, "early_stopping", bool
            ),
            "num_beams": self._get_value(input_data, "num_beams", int),
            "temperature": self._get_value(input_data, "temperature", int),
            "ngram_size": self._get_value(input_data, "ngram_size", int),
            "top_k": self._get_value(input_data, "top_k", int),
            "eta_cutoff": self._get_value(input_data, "eta_cutoff", int),
            "num_return_sequences": self._get_value(
                input_data, "num_return_sequences", int
            ),
            "decoder_start_token_id": self._get_value(
                input_data, "decoder_start_token_id", int
            ),
            "use_cache": self._get_value(input_data, "use_cache", bool),
            "length_penalty": self._get_value(
                input_data, "length_penalty", int
            ),
            "backstory": self._get_value(input_data, "backstory", str),
            "use_backstory": self._get_value(
                input_data, "use_backstory", bool
            ),
            "use_weather_prompt": self._get_value(
                input_data, "use_weather_prompt", bool
            ),
            "gender": self._get_value(input_data, "gender", str),
            "voice_id": self._get_value(input_data, "voice_id", int),
        }

        return {
            "chatbot_config": chatbot_config,
            "_exec_triggered": self.EXEC_OUT_PORT_NAME,
        }

    def _get_value(self, input_data, name, expected_type):
        """
        Get a value from input data or fall back to the node property.

        Args:
            input_data: Dictionary containing input values.
            name: Name of the parameter.
            expected_type: Type to convert the value to.

        Returns:
            The value converted to the expected type.
        """
        if name in input_data and input_data[name] is not None:
            value = input_data[name]
            if expected_type == bool:
                return bool(value)
            elif expected_type == int:
                if value is None:
                    return None  # Allow None values for integers
                return int(value)
            elif expected_type == float:
                return float(value)
            return value
        else:
            # Get from node property
            value = self.get_property(name)
            if expected_type == bool:
                return bool(value)
            elif expected_type == int:
                if value is None:
                    return None  # Allow None values for integers
                return int(value)
            elif expected_type == float:
                return float(value)
            return value
