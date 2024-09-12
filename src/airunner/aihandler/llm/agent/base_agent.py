import datetime
import time
import traceback
from typing import AnyStr
import torch
from PySide6.QtCore import QObject

from airunner.aihandler.llm.agent.agent_llamaindex_mixin import AgentLlamaIndexMixin
from airunner.aihandler.llm.agent.external_condition_stopping_criteria import ExternalConditionStoppingCriteria
from airunner.aihandler.logger import Logger
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
from airunner.utils.prepare_llm_generate_kwargs import prepare_llm_generate_kwargs
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.workers.agent_worker import AgentWorker


class BaseAgent(
    QObject,
    MediatorMixin,
    SettingsMixin,
    AgentLlamaIndexMixin,
):
    def __init__(self, *args, **kwargs):
        self.logger = Logger(prefix=self.__class__.__name__)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.model = kwargs.pop("model", None)
        AgentLlamaIndexMixin.__init__(self)
        self._chatbot = None
        self._bot_mood = None
        self.action = LLMActionType.CHAT
        self.rendered_template = None
        self.tokenizer = kwargs.pop("tokenizer", None)
        self.streamer = kwargs.pop("streamer", None)
        self.tools = kwargs.pop("tools", None)
        self.chat_template = kwargs.pop("chat_template", "")
        self.is_mistral = kwargs.pop("is_mistral", True)
        super().__init__(*args, **kwargs)
        self.prompt = ""
        self.history = []
        self.thread = None
        self.do_interrupt = False
        self.register(SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL, self.add_chatbot_response_to_history)
        self.response_worker = create_worker(AgentWorker)
        self.load_rag(model=self.model, tokenizer=self.tokenizer)

    @property
    def available_actions(self):
        return {
            0: LLMActionType.DO_NOT_RESPOND,
            1: LLMActionType.QUIT_APPLICATION,
            2: LLMActionType.TOGGLE_FULLSCREEN,
            3: LLMActionType.TOGGLE_TTS,
            4: LLMActionType.UPDATE_MOOD,
            5: LLMActionType.GENERATE_IMAGE,
            6: LLMActionType.PERFORM_RAG_SEARCH,
            7: LLMActionType.CHAT,
        }

    @property
    def llm_generator_settings(self):
        return self.settings["llm_generator_settings"]

    @property
    def chatbot_name(self) -> str:
        if self.action == LLMActionType.APPLICATION_COMMAND:
            chatbot_name = "Agent"
        else:
            chatbot_name = "Chatbot"
        return chatbot_name

    @property
    def chatbot(self) -> dict:
        if self._chatbot and self.action != LLMActionType.APPLICATION_COMMAND:
            return self._chatbot
        return self.llm_generator_settings["saved_chatbots"][self.chatbot_name]

    @property
    def username(self) -> str:
        return self.chatbot["username"]

    @property
    def botname(self) -> str:
        return self.chatbot["botname"]

    @property
    def bot_mood(self) -> str:
        return self.chatbot["bot_mood"] if self._bot_mood is None else self._bot_mood

    @bot_mood.setter
    def bot_mood(self, value: str):
        self._bot_mood = value

    @property
    def bot_personality(self) -> str:
        return self.chatbot["bot_personality"]

    def unload(self):
        self.model = None
        self.tokenizer = None
        self.thread = None
        clear_memory()

    def clear_history(self):
        self.history = []
        self.reload_rag()

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

    def mood(self, botname: str, bot_mood: str, use_mood: bool) -> str:
        return (
            f"{botname} is not a computer or a bot, you are a human with emotions. "
            f"{botname}'s mood changes depending on the conversation and other factors.\n"
            f"{botname}'s current mood: {bot_mood}."
            #f"{botname}'s evaluation of {username}: {self.user_evaluation}"
        ) if (use_mood and bot_mood != "") else ""

    def history_prompt(self) -> str:
        history = ""
        for message in self.history:
            if message["role"] == LLMChatRole.HUMAN.value:
                history += f"{self.username}: {message['content']}\n"
            elif message["role"] == LLMChatRole.ASSISTANT.value:
                history += f"{self.botname}: {message['content']}\n"
        return (
            "------\n"
            "Chat History:\n"
            f"{history}"
        )

    def append_date_time_timezone(self, system_prompt: list) -> list:
        current_date = datetime.datetime.now().strftime("%A %b %d, %Y")
        current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
        current_timezone = time.tzname
        system_prompt.append("\n======\n")
        system_prompt.append(
            f"Use the following information to help you with your response, but do not include it in your response or reference it directly unless asked.")
        system_prompt.append(f"Date: {current_date}, Time: {current_time}, Timezone: {current_timezone}")
        return system_prompt

    def build_system_prompt(
        self,
        action
    ):
        system_instructions = ""
        guardrails_prompt = ""
        use_mood = self.chatbot["use_mood"]
        use_personality = self.chatbot["use_personality"]
        use_names = self.chatbot["assign_names"]
        use_system_instructions = self.chatbot["use_system_instructions"]
        use_guardrails = self.chatbot["use_guardrails"]
        bot_mood = self.bot_mood
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
            system_prompt = [
                guardrails_prompt,
                system_instructions,
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                self.personality_prompt(bot_personality, use_personality),
                self.history_prompt(),
            ]

            if self.chatbot["use_datetime"]:
                system_prompt = self.append_date_time_timezone(system_prompt)

        elif action == LLMActionType.GENERATE_IMAGE:
            guardrails = self.settings["prompt_templates"]["image"]["guardrails"] if self.settings["prompt_templates"]["image"]["use_guardrails"] else ""
            system_prompt = [
                guardrails,
                self.settings["prompt_templates"]["image"]["system"],
                self.history_prompt()
            ]

        elif action == LLMActionType.APPLICATION_COMMAND:
            system_instructions = self.settings["prompt_templates"]["application_command"]["system"]

            # Create a list of commands that the bot can choose from
            for index, action in self.available_actions.items():
                system_instructions += f"{index}: {action.value}\n"

            system_prompt = [
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                self.history_prompt(),
                system_instructions
            ]

        elif action == LLMActionType.UPDATE_MOOD:
            system_instructions = self.settings["prompt_templates"]["update_mood"]["system"]
            system_prompt = [
                guardrails_prompt,
                system_instructions,
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                self.personality_prompt(bot_personality, use_personality),
                self.history_prompt(),
            ]

        elif action == LLMActionType.PERFORM_RAG_SEARCH:
            system_instructions = self.settings["prompt_templates"]["rag_search"]["system"]
            system_prompt = [
                guardrails_prompt,
                system_instructions,
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                self.personality_prompt(bot_personality, use_personality),
                self.history_prompt(),
            ]

        elif action == LLMActionType.QUIT_APPLICATION:
            self.emit_signal(SignalCode.QUIT_APPLICATION)

        elif action == LLMActionType.TOGGLE_FULLSCREEN:
            self.emit_signal(SignalCode.TOGGLE_FULLSCREEN_SIGNAL)

        elif action == LLMActionType.TOGGLE_TTS:
            self.emit_signal(SignalCode.TOGGLE_TTS_SIGNAL)

        return "\n".join(system_prompt)

    def names_prompt(self, use_names: bool, botname: str, username: str) -> str:
        return f"Your name is {botname}. \nThe user's name is {username}." if use_names else ""

    def personality_prompt(self, bot_personality: str, use_personality: bool) -> str:
        return (
            f"Your personality: {bot_personality}."
        ) if use_personality else ""

    def prepare_messages(
        self,
        action
    ) -> list:
        system_prompt = self.build_system_prompt(action)
        if action == LLMActionType.APPLICATION_COMMAND:
            prompt = (
                "Choose an action from THE LIST of commands for the text above. "
                "Only return the number of the command."
            )
        elif action == LLMActionType.GENERATE_IMAGE:
            prompt = (
                "Generate an image based on the user's request.\n"
                "You will return a JSON string which matches the following data structure:\n"
                "```json\n{\n"
                "    \"prompt\": \"[PLACEHOLDER]\",\n"
                "    \"secondary_prompt\": \"[PLACEHOLDER]\",\n"
                "    \"negative_prompt\": \"[PLACEHOLDER]\",\n"
                "    \"secondary_negative_prompt\": \"[PLACEHOLDER]\",\n"
                "}```\n"
                f"Replace the [PLACEHOLDER] with the appropriate text basd on {self.username}'s request.\n"
            )
        else:
            prompt = f"Respond to {self.username}"
        messages = [
            {
                "content": system_prompt,
                "role": LLMChatRole.SYSTEM.value
            },
            {
                "content": prompt,
                "role": LLMChatRole.HUMAN.value
            }
        ]
        return messages

    def get_rendered_template(
        self,
        action: LLMActionType
    ) -> str:
        conversation = self.prepare_messages(
            action
        )

        rendered_template = self.tokenizer.apply_chat_template(
            chat_template=self.chat_template,
            conversation=conversation,
            tokenize=False
        )

        # HACK: current version of transformers does not allow us to pass
        # variables to the chat template function, so we apply those here
        variables = {
            "speaker_name": self.botname,
            "listener_name": self.username,
            "username": self.username,
            "botname": self.botname,
            "bot_mood": self.bot_mood,
            "bot_personality": self.bot_personality,
        }
        for key, value in variables.items():
            value = value or ""
            rendered_template = rendered_template.replace("{{ " + key + " }}", value)
        return rendered_template

    @property
    def override_parameters(self):
        generate_kwargs = prepare_llm_generate_kwargs(self.settings["llm_generator_settings"])
        return generate_kwargs if self.settings["llm_generator_settings"]["override_parameters"] else {}

    @property
    def system_instructions(self):
        return self.chatbot["system_instructions"]

    @property
    def generator_settings(self):
        return prepare_llm_generate_kwargs(self.chatbot)

    def get_model_inputs(
        self,
        action: LLMActionType,
        **kwargs
    ):
        self.rendered_template = self.get_rendered_template(
            action
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
        action: str,
        **kwargs
    ):
        self.action = action
        self.logger.debug("Running...")
        self.prompt = prompt
        streamer = self.streamer
        system_instructions = kwargs.get("system_instructions", self.system_instructions)

        return self.do_run(
            action,
            **kwargs,
            system_instructions=system_instructions,
            use_names=True,
            streamer=streamer
        )

    def do_run(
        self,
        action: LLMActionType,
        streamer=None,
        do_emit_response: bool = True,
        use_names: bool = True,
        **kwargs
    ):
        if action == LLMActionType.PERFORM_RAG_SEARCH:
            self.emit_signal(SignalCode.LLM_RAG_SEARCH_SIGNAL, {
                "message": self.prompt,
            })
            return

        # Add the user's message to history
        self.add_message_to_history(self.prompt, LLMChatRole.HUMAN)

        model_inputs = self.get_model_inputs(
            action,
            use_names=use_names,
            **kwargs
        )

        if streamer:
            self.run_with_thread(
                model_inputs,
                action=action,
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
        data = dict(
            **model_inputs,
            **self.generator_settings,
            stopping_criteria=[stopping_criteria]
        )
        data.update(self.override_parameters)
        return data

    def run_with_thread(
        self,
        model_inputs,
        action,
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
            from transformers import BitsAndBytesConfig

            if "attention_mask" in data:
                del data["attention_mask"]
            self.response_worker.add_to_queue({
                "model": self.model,
                "kwargs": data,
                "prompt": self.prompt,
                "botname": self.botname
            })
            self.do_interrupt = False
        except Exception as e:
            print("545: An error occurred in model.generate:")
            print(str(e))
            print(traceback.format_exc())
        # strip all new lines from rendered_template:
        #self.rendered_template = self.rendered_template.replace("\n", " ")
        eos_token = self.tokenizer.eos_token
        bos_token = self.tokenizer.bos_token
        if self.is_mistral:
            self.rendered_template = bos_token + self.rendered_template
        skip = True
        streamed_template = ""
        replaced = False
        is_end_of_message = False
        is_first_message = True
        response = ""
        if action == LLMActionType.GENERATE_IMAGE:
            self.emit_signal(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                dict(
                    message="Generating image prompt.\n",
                    is_first_message=is_first_message,
                    is_end_of_message=False,
                    name=self.botname,
                )
            )
            is_first_message = False
        if streamer:
            for new_text in streamer:
                # strip all newlines from new_text
                #parsed_new_text = new_text.replace("\n", " ")
                streamed_template += new_text
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
                    if action == LLMActionType.CHAT or action == LLMActionType.GENERATE_IMAGE:
                        self.emit_signal(
                            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                            dict(
                                message=new_text,
                                is_first_message=is_first_message,
                                is_end_of_message=is_end_of_message,
                                name=self.botname,
                            )
                        )
                    else:
                        self.emit_signal(
                            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                            dict(
                                message="",
                                is_first_message=is_first_message,
                                is_end_of_message=is_end_of_message,
                                name=self.botname,
                            )
                        )
                    is_first_message = False

        if streamed_template is not None:
            if action == LLMActionType.CHAT:
                self.add_message_to_history(
                    streamed_template,
                    LLMChatRole.ASSISTANT
                )

                return self.run_with_thread(
                    model_inputs,
                    LLMActionType.UPDATE_MOOD,
                    **kwargs,
                )

            elif action == LLMActionType.GENERATE_IMAGE:
                self.emit_signal(
                    SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL,
                    {
                        "prompt": streamed_template,
                        "type": "photo"
                    }
                )

            elif action == LLMActionType.UPDATE_MOOD:
                self.bot_mood = streamed_template

            elif action == LLMActionType.APPLICATION_COMMAND:
                print("APPLICATION COMMAND:")
                index = ''.join(c for c in streamed_template if c.isdigit())
                print(f"index: {index}")
                try:
                    index = int(index)
                except ValueError:
                    index = 0
                print("RESPONSE:", index)
                action = self.available_actions[index]

                if action is not None:
                    return self.run(
                        prompt=self.prompt,
                        action=action,
                    )

        return streamed_template

    def add_chatbot_response_to_history(self, response: dict):
        self.add_message_to_history(
            response["message"],
            response["role"]
        )

    def add_message_to_history(
        self,
        content: AnyStr,
        role: LLMChatRole = LLMChatRole.ASSISTANT
    ):
        if content is None:
            return

        if role == LLMChatRole.ASSISTANT and content:
            content = content.replace(f"{self.botname}:", "")
            content = content.replace(f"{self.botname}", "")

        last_item = self.history.pop() if len(self.history) > 0 else {}
        last_item_role = last_item.get("role", None)
        last_item_role_is_current_role = last_item_role == role.value

        # if the last_item is of the same role as the current message, append the content to the last_item
        if not last_item_role_is_current_role and len(last_item.keys()) > 0:
            item = last_item
        elif last_item_role_is_current_role:
            item = {
                "role": role.value,
                "content": content
            }
            item["content"] += last_item.get("content", "") + "\n" + content
        else:
            item = {
                "role": role.value,
                "content": content
            }
        self.history.append(item)
