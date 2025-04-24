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

    def __init__(self):
        super().__init__()

        # Add inputs for Chatbot parameters
        self.add_input("name", display_name=True)
        self.add_input("botname", display_name=True)
        self.add_input("use_personality", display_name=True)
        self.add_input("use_mood", display_name=True)
        self.add_input("use_guardrails", display_name=True)
        self.add_input("use_system_instructions", display_name=True)
        self.add_input("use_datetime", display_name=True)
        self.add_input("assign_names", display_name=True)
        self.add_input("bot_personality", display_name=True)
        self.add_input("prompt_template", display_name=True)
        self.add_input("use_tool_filter", display_name=True)
        self.add_input("use_gpu", display_name=True)
        self.add_input("skip_special_tokens", display_name=True)
        self.add_input("sequences", display_name=True)
        self.add_input("seed", display_name=True)
        self.add_input("random_seed", display_name=True)
        self.add_input("model_version", display_name=True)
        self.add_input("model_type", display_name=True)
        self.add_input("dtype", display_name=True)
        self.add_input("return_result", display_name=True)
        self.add_input("guardrails_prompt", display_name=True)
        self.add_input("system_instructions", display_name=True)
        self.add_input("top_p", display_name=True)
        self.add_input("min_length", display_name=True)
        self.add_input("max_new_tokens", display_name=True)
        self.add_input("repetition_penalty", display_name=True)
        self.add_input("do_sample", display_name=True)
        self.add_input("early_stopping", display_name=True)
        self.add_input("num_beams", display_name=True)
        self.add_input("temperature", display_name=True)
        self.add_input("ngram_size", display_name=True)
        self.add_input("top_k", display_name=True)
        self.add_input("eta_cutoff", display_name=True)
        self.add_input("num_return_sequences", display_name=True)
        self.add_input("decoder_start_token_id", display_name=True)
        self.add_input("use_cache", display_name=True)
        self.add_input("length_penalty", display_name=True)
        self.add_input("backstory", display_name=True)
        self.add_input("use_backstory", display_name=True)
        self.add_input("use_weather_prompt", display_name=True)
        self.add_input("gender", display_name=True)
        self.add_input("voice_id", display_name=True)

        # Add output port for the Chatbot dictionary
        self.add_output("chatbot_config")

        # String parameters
        self.create_property(
            "chatbot_name",
            "Chatbot",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

        self.create_property(
            "botname",
            "Computer",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

        self.create_property(
            "bot_personality",
            "happy. He loves {{ username }}",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="personality",
        )

        self.create_property(
            "prompt_template",
            "Mistral 7B Instruct: Default Chatbot",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

        self.create_property(
            "model_version",
            AIRUNNER_DEFAULT_LLM_HF_PATH,
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="model",
        )

        self.create_property(
            "model_type",
            "llm",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="model",
        )

        self.create_property(
            "dtype",
            "4bit",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="model",
        )

        self.create_property(
            "guardrails_prompt",
            AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT,
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="prompts",
        )

        self.create_property(
            "system_instructions",
            AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT,
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="prompts",
        )

        self.create_property(
            "backstory",
            "",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="personality",
        )

        self.create_property(
            "gender",
            Gender.MALE.value,
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="voice",
        )

        # Boolean parameters
        self.create_property(
            "use_personality",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="personality",
        )

        self.create_property(
            "use_mood",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="personality",
        )

        self.create_property(
            "use_guardrails",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="prompts",
        )

        self.create_property(
            "use_system_instructions",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="prompts",
        )

        self.create_property(
            "use_datetime",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="basic",
        )

        self.create_property(
            "assign_names",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="basic",
        )

        self.create_property(
            "use_tool_filter",
            False,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="advanced",
        )

        self.create_property(
            "use_gpu",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="model",
        )

        self.create_property(
            "skip_special_tokens",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="model",
        )

        self.create_property(
            "random_seed",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="generation",
        )

        self.create_property(
            "return_result",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="basic",
        )

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
            tab="model",
        )

        self.create_property(
            "use_backstory",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="personality",
        )

        self.create_property(
            "use_weather_prompt",
            False,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="prompts",
        )

        # Integer parameters
        self.create_property(
            "sequences",
            1,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(1, 10),
            tab="generation",
        )

        self.create_property(
            "seed",
            42,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 999999),
            tab="generation",
        )

        self.create_property(
            "top_p",
            900,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 1000),
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
            "max_new_tokens",
            1000,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(1, 2048),
            tab="generation",
        )

        self.create_property(
            "repetition_penalty",
            100,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 200),
            tab="generation",
        )

        self.create_property(
            "num_beams",
            1,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(1, 10),
            tab="generation",
        )

        self.create_property(
            "temperature",
            1000,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 2000),
            tab="generation",
        )

        self.create_property(
            "ngram_size",
            2,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 10),
            tab="generation",
        )

        self.create_property(
            "top_k",
            10,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 100),
            tab="generation",
        )

        self.create_property(
            "eta_cutoff",
            10,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 100),
            tab="advanced",
        )

        self.create_property(
            "num_return_sequences",
            1,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(1, 5),
            tab="generation",
        )

        self.create_property(
            "decoder_start_token_id",
            None,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 1000),
            tab="advanced",
        )

        self.create_property(
            "length_penalty",
            100,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 200),
            tab="generation",
        )

        self.create_property(
            "voice_id",
            None,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 1000),
            tab="voice",
        )

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
