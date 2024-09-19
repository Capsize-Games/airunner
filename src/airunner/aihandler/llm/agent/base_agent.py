import datetime
import sqlite3
import time
import traceback
from typing import AnyStr
import torch
from PySide6.QtCore import QObject

from airunner.aihandler.llm.agent.agent_database_handler import AgentDatabaseHandler
from airunner.aihandler.llm.agent.agent_llamaindex_mixin import AgentLlamaIndexMixin
from airunner.aihandler.llm.agent.external_condition_stopping_criteria import ExternalConditionStoppingCriteria
from airunner.aihandler.logger import Logger
from airunner.mediator_mixin import MediatorMixin
from airunner.enums import (
    SignalCode,
    LLMChatRole,
    LLMActionType
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
        self.database_handler = AgentDatabaseHandler()
        self.conversation_id = None
        self.create_conversation()
        self.history = self.database_handler.load_history_from_db(self.conversation_id)  # Load history by conversation ID
        super().__init__(*args, **kwargs)
        self.prompt = ""
        self.thread = None
        self.do_interrupt = False
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
            chatbot_name = self.llm_generator_settings["current_chatbot"]
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
        settings = self.settings
        settings["llm_generator_settings"]["saved_chatbots"][self.chatbot_name]["bot_mood"] = value
        self.settings = settings

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
        self.create_conversation()

    def create_conversation(self):
        # Get the most recent conversation ID
        recent_conversation_id = self.database_handler.get_most_recent_conversation_id()

        # Check if there are messages for the most recent conversation ID
        if recent_conversation_id is not None:
            messages = self.database_handler.load_history_from_db(recent_conversation_id)
            if not messages:
                self.conversation_id = recent_conversation_id
                return

        # If there are messages or no recent conversation ID, create a new conversation
        self.conversation_id = self.database_handler.create_conversation()

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
        previous_date = None
        for message in self.history:
            # Check if the timestamp is a string and convert it to a datetime object if necessary
            if isinstance(message["timestamp"], str):
                current_date = datetime.datetime.strptime(message["timestamp"], "%Y-%m-%d %H:%M:%S").date()
            else:
                current_date = message["timestamp"].date()

            if previous_date is None or current_date != previous_date:
                history += f"\n--- {current_date.strftime('%B %d, %Y')} ---\n"
                previous_date = current_date
            name = ""
            if message["role"] == LLMChatRole.HUMAN.value:
                name = self.username
            elif message["role"] == LLMChatRole.ASSISTANT.value:
                name = self.botname
            history += f"{name}: {message['content']}\n"
        return (
            "------\n"
            "Chat History:\n"
            f"{history}"
        )

    def date_time_prompt(self) -> str:
        if not self.chatbot["use_datetime"]:
            return ""
        current_date = datetime.datetime.now().strftime("%A %b %d, %Y")
        current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
        current_timezone = time.tzname
        prompt = [
            "\n======\n",
            f"Use the following information to help you with your response, but do not include it in your response or reference it directly unless asked.",
            f"Date: {current_date}, Time: {current_time}, Timezone: {current_timezone}",
        ]
        return "\n".join(prompt)

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

        if action is LLMActionType.CHAT:
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
                self.date_time_prompt()
            ]

        elif action is LLMActionType.GENERATE_IMAGE:
            guardrails = self.settings["prompt_templates"]["image"]["guardrails"] if self.settings["prompt_templates"]["image"]["use_guardrails"] else ""
            system_prompt = [
                guardrails,
                self.settings["prompt_templates"]["image"]["system"],
                self.history_prompt()
            ]

        elif action is LLMActionType.APPLICATION_COMMAND:
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

        elif action is LLMActionType.UPDATE_MOOD:
            system_instructions = self.settings["prompt_templates"]["update_mood"]["system"]
            system_prompt = [
                guardrails_prompt,
                system_instructions,
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                self.personality_prompt(bot_personality, use_personality),
                self.history_prompt(),
            ]

        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            system_instructions = self.settings["prompt_templates"]["rag_search"]["system"]
            system_prompt = [
                guardrails_prompt,
                system_instructions,
                self.names_prompt(use_names, botname, username),
                self.mood(botname, bot_mood, use_mood),
                self.personality_prompt(bot_personality, use_personality),
                self.history_prompt(),
            ]

        elif action is LLMActionType.QUIT_APPLICATION:
            self.emit_signal(SignalCode.QUIT_APPLICATION)

        elif action is LLMActionType.TOGGLE_FULLSCREEN:
            self.emit_signal(SignalCode.TOGGLE_FULLSCREEN_SIGNAL)

        elif action is LLMActionType.TOGGLE_TTS:
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
        conversation = self.prepare_messages(action)
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

    @property
    def device(self):
        return get_torch_device(self.settings["memory_settings"]["default_gpu"]["llm"])

    def run(
        self,
        prompt: str,
        action: LLMActionType,
        **kwargs
    ):
        self.action = action
        self.logger.debug("Running...")
        self.prompt = prompt
        streamer = self.streamer

        # Add the user's message to history
        if action is LLMActionType.CHAT:
            self.add_message_to_history(self.prompt, LLMChatRole.HUMAN)

        self.rendered_template = self.get_rendered_template(action)

        model_inputs = self.tokenizer(
            self.rendered_template,
            return_tensors="pt"
        ).to(self.device)

        kwargs.update(
            streamer=streamer,
            action=action,
            do_emit_response=True
        )

        if streamer:
            self.run_with_thread(
                model_inputs,
                **kwargs
            )
        else:
            self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)
            stopping_criteria = ExternalConditionStoppingCriteria(self.do_interrupt_process)
            data = self.prepare_generate_data(model_inputs, stopping_criteria)
            res = self.model.generate(**data)
            response = self.tokenizer.decode(res[0])
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
        action: LLMActionType,
        **kwargs,
    ):
        # Generate the response
        self.logger.debug("Generating...")

        self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)

        stopping_criteria = ExternalConditionStoppingCriteria(self.do_interrupt_process)

        data = self.prepare_generate_data(model_inputs, stopping_criteria)
        streamer = kwargs.get("streamer", self.streamer)
        data["streamer"] = streamer

        # if "attention_mask" in data:
        #     del data["attention_mask"]

        self.do_interrupt = False

        if action is not LLMActionType.PERFORM_RAG_SEARCH:
            try:
                self.response_worker.add_to_queue({
                    "model": self.model,
                    "kwargs": data,
                    "prompt": self.prompt,
                    "botname": self.botname,
                })
            except Exception as e:
                self.logger.error("545: An error occurred in model.generate:")
                self.logger.error(str(e))
                self.logger.error(traceback.format_exc())

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

        if streamer and action in (
            LLMActionType.CHAT,
            LLMActionType.GENERATE_IMAGE,
            LLMActionType.UPDATE_MOOD
        ):
            for new_text in streamer:
                # strip all newlines from new_text
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
                    if action in (
                        LLMActionType.CHAT,
                        LLMActionType.PERFORM_RAG_SEARCH,
                        LLMActionType.GENERATE_IMAGE
                    ):
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
        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            streamed_template = ""
            data = dict(
                **self.generator_settings,
                stopping_criteria=[stopping_criteria]
            )
            data.update(self.override_parameters)
            self.llm.generate_kwargs = data
            response = self.chat_engine.stream_chat(message=self.prompt)
            is_first_message = True
            is_end_of_message = False
            for new_text in response.response_gen:
                streamed_template += new_text

                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message=" " +new_text,
                        is_first_message=is_first_message,
                        is_end_of_message=is_end_of_message,
                        name=self.botname,
                    )
                )
                is_first_message = False

        if streamed_template is not None:
            if action is LLMActionType.CHAT:
                self.add_message_to_history(
                    streamed_template,
                    LLMChatRole.ASSISTANT
                )
            elif action is LLMActionType.UPDATE_MOOD:
                self.bot_mood = streamed_template
                return self.run(
                    prompt=self.prompt,
                    action=LLMActionType.CHAT,
                    **kwargs,
                )

            elif action is LLMActionType.GENERATE_IMAGE:
                self.emit_signal(
                    SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL,
                    {
                        "prompt": streamed_template,
                        "type": "photo"
                    }
                )
            elif action is LLMActionType.APPLICATION_COMMAND:
                index = ''.join(c for c in streamed_template if c.isdigit())
                try:
                    index = int(index)
                except ValueError:
                    index = 0
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

    def get_db_connection(self):
        return sqlite3.connect('agent_history.db')

    def add_message_to_history(
        self,
        content: AnyStr,
        role: LLMChatRole = LLMChatRole.ASSISTANT
    ):
        if content is None:
            return

        name = self.username
        is_bot = False
        if role is LLMChatRole.ASSISTANT and content:
            content = content.replace(f"{self.botname}:", "")
            content = content.replace(f"{self.botname}", "")
            is_bot = True
            name = self.botname

        self.history.append({
            "role": role.value,
            "content": content,
            "name": name,
            "is_bot": is_bot,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "conversation_id": self.conversation_id  # Use the stored conversation ID
        })

        self.database_handler.add_message_to_history(
            content,
            role.value,
            name,
            is_bot,
            self.conversation_id
        )

    def on_load_conversation(self, message):
        self.history = []
        self.conversation_id = message["conversation_id"]
        self.history = self.database_handler.load_history_from_db(self.conversation_id)
        self.emit_signal(SignalCode.SET_CONVERSATION, {
            "messages": self.history
        })

