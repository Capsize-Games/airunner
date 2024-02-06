from PyQt6.QtCore import QObject

from airunner.mediator_mixin import MediatorMixin
from airunner.utils import parse_template
from airunner.windows.main.settings_mixin import SettingsMixin


class LLMRequest(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        QObject.__init__(self, *args, **kwargs)

    def __call__(
        self,
        settings,
        prompt: str,
        conversation_history: list,
        generator_name: str = "casuallm"
    ):
        llm_generator_settings = settings["llm_generator_settings"]
        current_bot = settings["llm_generator_settings"]["saved_chatbots"][
            settings["llm_generator_settings"]["current_chatbot"]]
        current_bot_name = settings["llm_generator_settings"]["current_chatbot"]
        template_name = settings["llm_generator_settings"]["saved_chatbots"][current_bot_name]["prompt_template"]
        parsed_template = ""
        if template_name in settings["llm_templates"]:
            prompt_template = settings["llm_templates"][template_name]
            parsed_template = parse_template(prompt_template)
        return {
            "llm_request": True,
            "request_data": {
                "unload_unused_model": settings["memory_settings"]["unload_unused_models"],
                "move_unused_model_to_cpu": settings["memory_settings"]["move_unused_model_to_cpu"],
                "generator_name": generator_name,
                "model_path": "mistralai/Mistral-7B-Instruct-v0.1", #llm_generator_settings["model_version"],
                "stream": True,
                "prompt": prompt,
                "do_summary": False,
                "is_bot_alive": True,
                "conversation_history": conversation_history,
                "generator": settings["llm_generator_settings"],
                "prefix": "",
                "suffix": "",
                "dtype": llm_generator_settings["dtype"],
                "use_gpu": llm_generator_settings["use_gpu"],
                "request_type": "image_caption_generator",
                "template": parsed_template,
                "hf_api_key_read_key": settings["hf_api_key_read_key"],
                "parameters": {
                    "override_parameters": settings["llm_generator_settings"]["override_parameters"],
                    "top_p": llm_generator_settings["top_p"] / 100.0,
                    "max_length": llm_generator_settings["max_length"],
                    "repetition_penalty": llm_generator_settings["repetition_penalty"] / 100.0,
                    "min_length": llm_generator_settings["min_length"],
                    "length_penalty": llm_generator_settings["length_penalty"] / 100,
                    "num_beams": llm_generator_settings["num_beams"],
                    "ngram_size": llm_generator_settings["ngram_size"],
                    "temperature": llm_generator_settings["temperature"] / 10000.0,
                    "sequences": llm_generator_settings["sequences"],
                    "top_k": llm_generator_settings["top_k"],
                    "eta_cutoff": llm_generator_settings['eta_cutoff'] / 100.0,
                    "seed": llm_generator_settings["do_sample"],
                    "early_stopping": llm_generator_settings["early_stopping"],
                },
                "image": None,
                "callback": None,
                "tts_settings": settings["tts_settings"],
                "username": current_bot["username"],
                "botname": current_bot["botname"],
                "use_personality": current_bot["use_personality"],
                "use_mood": current_bot["use_mood"],
                "use_guardrails": current_bot["use_guardrails"],
                "use_system_instructions": current_bot["use_system_instructions"],
                "assign_names": current_bot["assign_names"],
                "bot_personality": current_bot["bot_personality"],
                "bot_mood": current_bot["bot_mood"],
                "prompt_template": current_bot["prompt_template"],
                "guardrails_prompt": current_bot["guardrails_prompt"],
                "system_instructions": current_bot["system_instructions"],
            }
        }