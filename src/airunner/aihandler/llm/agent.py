import datetime
import json
import time
import traceback
from typing import AnyStr
import torch
from PySide6.QtCore import QObject
from transformers import StoppingCriteria
from airunner.aihandler.logger import Logger
from airunner.json_extractor import JSONExtractor
from airunner.mediator_mixin import MediatorMixin
from airunner.enums import (
    SignalCode,
    LLMChatRole,
    LLMActionType,
    ImageCategory
)
from airunner.utils.get_torch_device import get_torch_device
from airunner.utils.clear_memory import clear_memory
from airunner.utils.create_worker import create_worker
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.workers.agent_worker import AgentWorker


class ExternalConditionStoppingCriteria(StoppingCriteria):
    def __init__(self, external_condition_callable):
        super().__init__()
        self.external_condition_callable = external_condition_callable

    def __call__(self, inputs_ids, scores):
        return self.external_condition_callable()



class AIRunnerAgent(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.action = LLMActionType.CHAT

        self.rendered_template = None
        self.model = kwargs.pop("model", None)
        self.tokenizer = kwargs.pop("tokenizer", None)
        self.streamer = kwargs.pop("streamer", None)
        self.tools = kwargs.pop("tools", None)
        self.chat_template = kwargs.pop("chat_template", "")
        self.is_mistral = kwargs.pop("is_mistral", True)
        self.logger = Logger(prefix=self.__class__.__name__)
        super().__init__(*args, **kwargs)
        self.register(SignalCode.LLM_RESPOND_TO_USER_SIGNAL, self.do_response)
        self.register(SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL, self.add_chatbot_response_to_history)
        self.prompt = ""
        self.history = []
        self.thread = None
        self.do_interrupt = False
        self.response_worker = create_worker(AgentWorker)

    @property
    def llm_generator_settings(self):
        return self.settings["llm_generator_settings"]

    @property
    def chatbot_name(self) -> str:
        if self.action == LLMActionType.APPLICATION_COMMAND:
            chatbot_name = "Agent"
        elif self.action == LLMActionType.CHAT:
            chatbot_name = "Chatbot"
        else:
            chatbot_name = self.llm_generator_settings["current_chatbot"]
        return chatbot_name

    @property
    def chatbot(self) -> dict:
        return self.llm_generator_settings["saved_chatbots"][self.chatbot_name]

    @property
    def username(self) -> str:
        return self.chatbot["username"]

    @property
    def botname(self) -> str:
        return self.chatbot["botname"]

    @property
    def bot_mood(self) -> str:
        return self.chatbot["bot_mood"]

    @property
    def bot_personality(self) -> str:
        return self.chatbot["bot_personality"]

    def unload(self):
        self.model = None
        self.tokenizer = None
        self.thread = None
        clear_memory()

    def interrupt_process(self):
        self.do_interrupt = True

    def do_interrupt_process(self):
        interrupt = self.do_interrupt
        self.do_interrupt = False
        return interrupt

    @property
    def use_cuda(self):
        return torch.cuda.is_available()

    @property
    def cuda_index(self):
        return 0

    def build_system_prompt(
        self,
        action: LLMActionType,
        vision_history: list = []
    ):
        system_instructions = ""
        guardrails_prompt = ""
        use_mood = self.chatbot["use_mood"]
        use_personality = self.chatbot["use_personality"]
        use_names = self.chatbot["assign_names"]
        use_system_instructions = self.chatbot["use_system_instructions"]
        use_guardrails = self.chatbot["use_guardrails"]
        bot_mood = self.chatbot["bot_mood"]
        bot_personality = self.chatbot["bot_personality"]
        username = self.chatbot["username"]
        botname = self.chatbot["botname"]
        if use_system_instructions:
            system_instructions = self.chatbot["system_instructions"]
        if use_guardrails:
            guardrails_prompt = self.chatbot["guardrails_prompt"]

        system_prompt = []

        if action == LLMActionType.CHAT:
            """
            Build the system prompt for chat template
            """
            names = f"Your name is {botname}. \nThe user's name is {username}." if use_names else ""
            mood = (
                f"{botname} is not a computer or a bot, you are a human with emotions. "
                f"{botname}'s mood changes depending on the conversation and other factors.\n"
                f"{botname}'s current mood: {bot_mood}.\n"
                #f"{botname}'s evaluation of {username}: {self.user_evaluation}"
            ) if (use_mood and bot_mood != "") else ""
            personality = (
                f"Your personality: {bot_personality}."
            ) if use_personality else ""

            system_prompt = [
                guardrails_prompt,
                system_instructions,
                names,
                mood,
                personality,
            ]

            """
            If we have a vision history, append it to the prompt
            """
            if len(vision_history) > 0:
                vision_history = vision_history[-10:] if len(vision_history) > 10 else vision_history
                system_prompt.append("\n======\n")
                system_prompt.append((
                    "You have eyes, you can see. You see many things but they "
                    "are no always correct. You must try to determine what you "
                    "are seeing based on these images Try to summarize them to "
                    "determine what is happening. Here is a list of things that "
                    "you currently saw:"
                ))
                system_prompt.append(','.join(vision_history))

            """
            Append the date, time and timezone
            """
            if self.settings["prompt_templates"]["chatbot"]["use_system_datetime_in_system_prompt"]:
                current_date = datetime.datetime.now().strftime("%A %b %d, %Y")
                current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
                current_timezone = time.tzname
                system_prompt.append("\n======\n")
                system_prompt.append(f"Use the following information to help you with your response, but do not include it in your response or reference it directly unless asked.")
                system_prompt.append(f"Date: {current_date}, Time: {current_time}, Timezone: {current_timezone}")

        elif action == LLMActionType.ANALYZE_VISION_HISTORY:
            vision_history = vision_history[-10:] if len(vision_history) > 10 else vision_history
            system_prompt = [
                (
                    "You will be given a list of image captions. Your goal is to "
                    "analyze the captions and determine what is happening in the "
                    "images. The captions won't be entirely accurate, so you must "
                    "infer what you believe is happening in the images. "
                    "After analyzing the captions, you must summarize what you "
                    "believe is happening in the images. "
                    "Here is a list of captions:"
                ),
                ','.join(vision_history),
            ]

        elif action == LLMActionType.GENERATE_IMAGE:
            ", ".join([
                "'%s'" % category.value for category in ImageCategory
            ])
            guardrails = self.settings["prompt_templates"]["image"]["guardrails"] if self.settings["prompt_templates"]["image"]["use_guardrails"] else ""
            system_prompt = [
                guardrails,
                self.settings["prompt_templates"]["image"]["system"]
            ]

        elif action == LLMActionType.APPLICATION_COMMAND:
            system_prompt = [
                (
                    "You will be given some text. Your goal is to determine if the text has a request, goal, need "
                    "desire or command. If it does, you must determine the best course of action to "
                    "fulfill the request based on the list of commands above.\n\n"
                    "------\n"
                    "Rules:\n"
                    "* If the text does not have a request, goal, need, desire or command, you must select 'DO NOTHING'.\n"
                    "* If there is no good course of action, you must also select 'DO NOTHING'.\n"
                    "* When making your choice you MUST return only a number from THE LIST of commands. No other text is allowed.\n"
                    "------\n"
                    "THE LIST of commands you may choose from:\n"
                    "1. QUIT: Quit or close the application.\n"
                    "2. FULL SCREEN: Make the application full screen.\n"
                    "0. DO NOTHING: None of the above commands will accurately fulfill the task at hand.\n"
                )
            ]


        return "\n".join(system_prompt)

    def latest_human_message(
        self,
        action: LLMActionType
    ) -> dict:
        if self.prompt:
            prompt = self.prompt
            if action == LLMActionType.APPLICATION_COMMAND:
                prompt = (
                    f"`{prompt}`\n\n"
                    "Choose an action from THE LIST of commands for the text above. Only return the number of the command."
                )
            return {
                "content": prompt,
                "role": LLMChatRole.HUMAN.value
            }

        return {}

    def prepare_messages(
        self,
        action: LLMActionType,
        vision_history: list = []
    ) -> list:
        messages = [
            {
                "content": self.build_system_prompt(
                    action,
                    vision_history=vision_history
                ),
                "role": LLMChatRole.SYSTEM.value
            }
        ]

        if action == LLMActionType.CHAT:
            messages += self.history

        messages.append(
            self.latest_human_message(action)
        )

        return messages

    @property
    def _chat_template(self):
        return (
            "{% for message in messages %}"
            "{% if message['role'] == 'system' %}"
            "{{ '[INST] <<SYS>>' + message['content'] + ' <</SYS>>[/INST]' }}"
            "{% elif message['role'] == 'user' %}"
            "{{ '[INST]' + message['content'] + ' [/INST]' }}"
            "{% elif message['role'] == 'assistant' %}"
            "{{ message['content'] + eos_token + ' ' }}"
            "{% endif %}"
            "{% endfor %}"
        ) if self.is_mistral else None

    def get_rendered_template(
        self,
        action,
        vision_history
    ):
        conversation = []

        conversation = self.prepare_messages(
            action,
            vision_history=vision_history
        )

        rendered_template = self.tokenizer.apply_chat_template(
            chat_template=self._chat_template,
            conversation=conversation,
            tokenize=False
        )

        # HACK: current version of transformers does not allow us to pass
        # variables to the chat template function, so we apply those here
        variables = {
            "username": self.username,
            "botname": self.botname,
            "bot_mood": self.bot_mood,
            "bot_personality": self.bot_personality,
        }
        for key, value in variables.items():
            value = value or ""
            rendered_template = rendered_template.replace("{{ " + key + " }}", value)
        return rendered_template

    def do_response(self, message):
        self.run(
            prompt=self.prompt,
            action=LLMActionType.CHAT,
            max_new_tokens=message["args"][0]
        )

    @property
    def system_instructions(self):
        return self.chatbot["system_instructions"]

    @property
    def generator_settings(self):
        generator_settings = self.chatbot["generator_settings"]
        generator_settings["temperature"] = generator_settings["temperature"] / 10000
        generator_settings["top_p"] = generator_settings["top_p"] / 1000
        generator_settings["repetition_penalty"] = generator_settings["repetition_penalty"] / 10000
        generator_settings["length_penalty"] = generator_settings["length_penalty"] / 1000
        return generator_settings

    def get_model_inputs(
        self,
        action,
        vision_history,
        **kwargs
    ):
        self.chat_template = kwargs.get("chat_template", self.chat_template)

        conversation = self.prepare_messages(
            action,
            vision_history=vision_history
        )

        self.rendered_template = self.get_rendered_template(
            conversation,
            chat_template=self.chat_template
        )

        # Encode the rendered template
        encoded = self.tokenizer(
            self.rendered_template,
            return_tensors="pt"
        )
        model_inputs = encoded.to(
            get_torch_device(
                self.settings["memory_settings"]["default_gpu"]["llm"]
            )
        )
        return model_inputs

    def run(
        self,
        prompt: str,
        action: LLMActionType = LLMActionType.CHAT,
        vision_history: list = [],
        **kwargs
    ):
        self.logger.debug("Running...")
        self.prompt = prompt
        streamer = self.streamer
        system_instructions = kwargs.get("system_instructions", self.system_instructions)

        return self.do_run(
            action,
            vision_history,
            **kwargs,
            system_instructions=system_instructions,
            do_add_response_to_history=False,
            use_names=True,
            streamer=streamer
        )

    def do_run(
        self,
        prompt: str,
        action: LLMActionType = LLMActionType.CHAT,
        vision_history: list = [],
        do_add_response_to_history: bool = True,
        streamer=None,
        do_emit_response: bool = True,
        use_names: bool = True,
        **kwargs
    ):
        model_inputs = self.get_model_inputs(
            LLMActionType.CHAT,
            vision_history,
            use_names=use_names,
            **kwargs
        )

        if streamer:
            self.run_with_thread(
                model_inputs,
                action=LLMActionType.CHAT,
                do_add_response_to_history=do_add_response_to_history,
                streamer=streamer,
                do_emit_response=do_emit_response,
                **kwargs
            )
        else:
            self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)
            stopping_criteria = ExternalConditionStoppingCriteria(self.do_interrupt_process)
            data = self.prepare_generate_data(model_inputs, stopping_criteria)
            res = self.model.generate(
                **data
            )
            response = self.tokenizer.decode(res[0])
            if do_emit_response:
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message=response,
                        is_first_message=True,
                        is_end_of_message=True,
                        name=self.botname,
                    )
                )
            return response

    def prepare_generate_data(self, model_inputs, stopping_criteria):
        return dict(
            **model_inputs,
            **self.generator_settings,
            stopping_criteria=[stopping_criteria]
        )

    def run_with_thread(
        self,
        model_inputs,
        do_add_response_to_history: bool = True,
        action: LLMActionType = LLMActionType.CHAT,
        **kwargs,
    ):
        # Generate the response
        self.logger.debug("Generating...")

        self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)

        stopping_criteria = ExternalConditionStoppingCriteria(self.do_interrupt_process)

        data = self.prepare_generate_data(model_inputs, stopping_criteria)
        streamer = kwargs.get("streamer", self.streamer)
        data["streamer"] = streamer

        try:
            self.response_worker.add_to_queue({
                "model": self.model,
                "kwargs": data
            })
            self.do_interrupt = False
        except Exception as e:
            print("545: An error occurred in model.generate:")
            print(str(e))
            print(traceback.format_exc())
        # strip all new lines from rendered_template:
        self.rendered_template = self.rendered_template.replace("\n", " ")
        eos_token = self.tokenizer.eos_token
        bos_token = self.tokenizer.bos_token
        if self.is_mistral:
            self.rendered_template = bos_token + self.rendered_template
        skip = True
        streamed_template = ""
        replaced = False
        is_end_of_message = False
        is_first_message = True
        if streamer:
            for new_text in streamer:
                # strip all newlines from new_text
                parsed_new_text = new_text.replace("\n", " ")
                streamed_template += parsed_new_text
                if self.is_mistral:
                    streamed_template = streamed_template.replace(f"{bos_token} [INST]", f"{bos_token}[INST]")
                    streamed_template = streamed_template.replace("  [INST]", " [INST]")
                # iterate over every character in rendered_template and
                # check if we have the same character in streamed_template
                if not replaced:
                    for i, char in enumerate(self.rendered_template):
                        try:
                            if char == streamed_template[i]:
                                skip = False
                            else:
                                skip = True
                                break
                        except IndexError:
                            skip = True
                            break
                if skip:
                    continue
                elif not replaced:
                    replaced = True
                    streamed_template = streamed_template.replace(self.rendered_template, "")
                else:
                    if eos_token in new_text:
                        streamed_template = streamed_template.replace(eos_token, "")
                        new_text = new_text.replace(eos_token, "")
                        is_end_of_message = True
                    # strip botname from new_text
                    new_text = new_text.replace(f"{self.botname}:", "")
                    new_text = new_text.replace(f"{self.botname}", "")
                    self.emit_signal(
                        SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                        dict(
                            message=new_text,
                            is_first_message=is_first_message,
                            is_end_of_message=is_end_of_message,
                            name=self.botname,
                        )
                    )
                    is_first_message = False

        if streamed_template is not None:
            if action == LLMActionType.CHAT:
                if do_add_response_to_history:
                    self.add_message_to_history(
                        streamed_template,
                        LLMChatRole.ASSISTANT
                    )
            elif action == LLMActionType.GENERATE_IMAGE:
                json_objects = self.extract_json_objects(streamed_template)
                if len(json_objects) > 0:
                    self.emit_signal(
                        SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL,
                        json_objects[0]
                    )
                else:
                    self.logger.error("No JSON object found in the response.")

        return streamed_template

    def add_chatbot_response_to_history(self, response: dict):
        if response["message"] is None:
            return
        self.add_message_to_history(
            response["message"],
            response["role"]
        )

    def extract_json_objects(self, s):
        extractor = JSONExtractor()
        try:
            extractor.decode(s)
        except json.JSONDecodeError:
            pass
        return extractor.json_objects

    def add_message_to_history(
        self,
        content: AnyStr,
        role: LLMChatRole = LLMChatRole.ASSISTANT
    ):
        if role == LLMChatRole.ASSISTANT and content:
            content = content.replace(f"{self.botname}:", "")
            content = content.replace(f"{self.botname}", "")

        last_item = self.history.pop() if len(self.history) > 0 else {}
        last_item_role = last_item.get("role", None)
        last_item_role_is_current_role = last_item_role == role.value

        # if the last_item is of the same role as the current message, append the content to the last_item
        if not last_item_role_is_current_role and len(last_item.keys()) > 0:
            self.history.append(last_item)

        if last_item_role_is_current_role:
            item = {
                "role": role.value,
                "content": content
            }
            item["content"] += last_item.get("content", "") + "\n" + content
            self.history.append(item)
        else:
            self.history.append({
                "role": role.value,
                "content": content
            })
