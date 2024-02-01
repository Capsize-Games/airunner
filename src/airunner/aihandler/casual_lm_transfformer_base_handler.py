from typing import Any, Generator
from typing import AnyStr

from transformers import AutoModelForCausalLM, TextIteratorStreamer
from transformers import pipeline as hf_pipeline

from airunner.aihandler.local_agent import LocalAgent
from airunner.aihandler.llm_tools import QuitApplicationTool, StartVisionCaptureTool, StopVisionCaptureTool
from airunner.aihandler.tokenizer_handler import TokenizerHandler
from airunner.enums import SignalCode, LLMAction, LLMChatRole, LLMToolName

VALID_TASKS = ("text2text-generation", "text-generation", "summarization")
DEFAULT_BATCH_SIZE = 4


class CasualLMTransformerBaseHandler(TokenizerHandler):
    auto_class_ = AutoModelForCausalLM

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamer = None
        self.llm = None
        self.llm_with_tools = None
        self.agent_executor = None
        self.embed_model = None
        self.service_context_model = None
        self.use_query_engine: bool = False
        self.use_chat_engine: bool = True
        self._username: str = ""
        self._botname: str = ""
        self.bot_mood: str = ""
        self.bot_personality: str = ""
        self.user_evaluation: str = ""
        self.register(SignalCode.LLM_CLEAR_HISTORY, self.on_clear_history_signal)
        self.use_personality: bool = False
        self.use_mood: bool = False
        self.use_guardrails: bool = False
        self.use_system_instructions: bool = False
        self.assign_names: bool = False
        self.prompt_template: str = ""
        self.guardrails_prompt: str = ""
        self.system_instructions: str = ""
        self.agent = None
        #self.register(SignalCode.LLM_RESPOND_TO_USER, self.on_llm_respond_to_user_signal)

    @property
    def username(self):
        if self.assign_names:
            return self._username
        return "User"

    @property
    def botname(self):
        if self.assign_names:
            return self._botname
        return "Assistant"

    def on_clear_history_signal(self):
        self.history = []

    def process_data(self, data):
        super().process_data(data)
        self._username = self.request_data.get("username", "")
        self._botname = self.request_data.get("botname", "")
        self.bot_mood = self.request_data.get("bot_mood", "")
        self.bot_personality = self.request_data.get("bot_personality", "")
        self.use_personality = self.request_data.get("use_personality", False)
        self.use_mood = self.request_data.get("use_mood", False)
        self.use_guardrails = self.request_data.get("use_guardrails", False)
        self.use_system_instructions = self.request_data.get("use_system_instructions", False)
        self.assign_names = self.request_data.get("assign_names", False)
        self.prompt_template = self.request_data.get("prompt_template", "")
        self.guardrails_prompt = self.request_data.get("guardrails_prompt", "")
        self.system_instructions = self.request_data.get("system_instructions", "")

    def post_load(self):
        super().post_load()

        do_load_streamer = self.streamer is None
        if do_load_streamer:
            self.load_streamer()

        do_load_llm = self.llm is None
        if do_load_llm:
            self.load_llm()

        do_load_agent = self.agent is None
        if do_load_agent:
            self.load_agent()

    def load_agent(self):
        self.logger.info("Loading agent")
        # query_engine_tool = QueryEngineTool(
        #     query_engine=self.query_engine,
        #     metadata=ToolMetadata(
        #         name="help_agent",
        #         description="Agent that can return help results about the application."
        #     )
        # )
        tools = {
            LLMToolName.QUIT_APPLICATION.value: QuitApplicationTool(),
            LLMToolName.VISION_START_CAPTURE.value: StartVisionCaptureTool(),
            LLMToolName.VISION_STOP_CAPTURE.value: StopVisionCaptureTool(),
        }
        self.agent = LocalAgent(
            model=self.model,
            tokenizer=self.tokenizer,
            additional_tools=tools
        )
        self.agent._toolbox = tools

    def chat(self, prompt: AnyStr) -> AnyStr:
        self.logger.info("Chat Stream")
        res = self.agent.chat(
            task=self.prompt,
            return_code=False
            #task="add 5 and 5"
            #message=prompt,
            #chat_history=self.prepare_messages(LLMAction.CHAT),
            #task=LLMToolName.ADD.value
        )
        # self.stream_text(
        #     self.streamer,
        #     LLMAction.CHAT
        # )
        print("RES FROM AGENT: ", res)
        if not res:
            return "No response"
        # self.emit_streamed_text_signal(
        #     message=res,
        #     is_first_message=True,
        #     is_end_of_message=True
        # )
        return res
        # return self.stream_text(
        #     response=self.streamer,
        #     action=action
        # )

        # res = self.agent.chat(
        #     message=self.prompt,
        #     chat_history=self.prepare_messages(LLMAction.CHAT),
        #     tool_choice="help_agent"
        # )
        # self.emit_streamed_text_signal(
        #     message=res.response,
        #     is_first_message=True,
        #     is_end_of_message=True
        # )
        # return res.response

    def on_llm_respond_to_user_signal(self, message):
        self.logger.info("Responding to user")
        self.prompt = message
        self.llm.stream_chat(
            self.prepare_messages()
        )

        full_message = self.stream_text(
            response=self.streamer,
            action=LLMAction.CHAT
        )

        self.add_message_to_history(
            self.prompt,
            LLMChatRole.HUMAN
        )
        self.add_message_to_history(
            full_message,
            LLMChatRole.ASSISTANT
        )
        self.send_final_message()

    def load_streamer(self):
        self.logger.info("Loading LLM text streamer")
        self.streamer = TextIteratorStreamer(self.tokenizer)

    def load_llm(self):
        self.logger.info("Loading RAG")
        self.llm = hf_pipeline(
            task="text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            batch_size=DEFAULT_BATCH_SIZE,
            use_fast=True,
            **dict(),
        )

    def do_generate(self):
        self.logger.info("Generating response")
        # self.bot_mood = self.update_bot_mood()
        # self.user_evaluation = self.do_user_evaluation()
        full_message = self.chat(
            self.prompt
        )
        #full_message = self.rag_stream()
        self.add_message_to_history(
            self.prompt,
            LLMChatRole.HUMAN
        )
        self.add_message_to_history(
            full_message,
            LLMChatRole.ASSISTANT
        )
        self.send_final_message()

    def build_system_prompt(self):
        # if action == LLMAction.CHAT:
        guardrails = self.guardrails_prompt if self.use_guardrails else ""
        system_instructions = self.system_instructions if self.use_system_instructions else ""
        names = f"Your name is {self.botname}. \nThe user's name is {self.username}."
        mood = (
            f"{self.botname} is not a computer or a bot, you are a human with emotions. "
            f"{self.botname}'s mood changes depending on the conversation and other factors.\n"
            f"{self.botname}'s current mood: {self.bot_mood}.\n"
            f"{self.botname}'s evaluation of {self.username}: {self.user_evaluation}"
        ) if self.use_mood else ""
        personality = (
            f"Your personality: {self.bot_personality}."
        ) if self.use_personality else ""
        system_prompt = [
            guardrails,
            system_instructions,
            names,
            mood,
            personality,
        ]
        # elif action == LLMAction.RAG:
        #     system_prompt = [
        #         (
        #             f"Based on the context, provide an accurate response to the "
        #             f"user's message."
        #         )
        #     ]

        return "\n".join(system_prompt)

    def prepare_messages(self):
        messages = [
            # dict(
            #     content=self.build_system_prompt(),
            #     role=LLMChatRole.SYSTEM.value
            # )
        ]

        messages += self.history

        if self.prompt:
            messages.append(
                dict(
                    content=self.prompt,
                    role=LLMChatRole.HUMAN.value
                )
            )

        return messages

    def standard_text(
        self,
        response,
        action: LLMAction
    ):
        response_parser = self.parse_chat_response

        if action == LLMAction.RAG:
            response_parser = self.parse_rag_response

        content, is_end_of_message, full_message = response_parser(
            content=response,
            full_message=""
        )
        return content

    def stream_text(
        self,
        response: Generator,
        action: LLMAction,
        is_first_message: bool = True,
        full_message: str = "",
        do_emit_streamed_text_signal: bool = True
    ):
        response_parser = self.parse_chat_response

        for chat_response in response:
            content, is_end_of_message, full_message = response_parser(
                content=chat_response,
                full_message=full_message
            )
            if do_emit_streamed_text_signal:
                self.emit_streamed_text_signal(
                    message=content,
                    is_first_message=is_first_message,
                    is_end_of_message=is_end_of_message
                )
            is_first_message = False
        return full_message

    def parse_chat_response(
        self,
        content: Any,
        full_message: str = ""
    ):
        content, is_end_of_message = self.is_end_of_message(content)
        content = content.replace(full_message, "")
        full_message += content
        return content, is_end_of_message, full_message

    @staticmethod
    def is_end_of_message(content: str) -> (str, bool):
        if "</s>" in content:
            content = content.replace("</s>", "")
            return content, True
        return content, False

    def emit_streamed_text_signal(self, **kwargs):
        kwargs["name"] = self.botname
        self.emit(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            kwargs
        )

    def add_message_to_history(
        self,
        content: AnyStr,
        role: LLMChatRole = LLMChatRole.ASSISTANT
    ):
        self.history.append({
            'content': content,
            'role': role.value
        })

    def send_final_message(self):
        self.emit_streamed_text_signal(
            message="",
            is_first_message=False,
            is_end_of_message=True
        )

    def load_chat_engine(self):
        self.chat_engine = self.index.as_chat_engine()
