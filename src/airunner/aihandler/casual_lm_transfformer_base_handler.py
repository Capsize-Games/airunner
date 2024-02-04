import torch
import threading
from typing import Any, Generator
from typing import AnyStr

from transformers import AutoModelForCausalLM, TextIteratorStreamer, MistralForCausalLM
from transformers import pipeline as hf_pipeline

from airunner.aihandler.local_agent import LocalAgent
from airunner.aihandler.llm_tools import QuitApplicationTool, StartVisionCaptureTool, StopVisionCaptureTool, \
    StartAudioCaptureTool, StopAudioCaptureTool, StartSpeakersTool, StopSpeakersTool, ProcessVisionTool, \
    ProcessAudioTool, RespondToUserTool
from airunner.aihandler.tokenizer_handler import TokenizerHandler
from airunner.enums import SignalCode, LLMAction, LLMChatRole, LLMToolName


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
        self.tools: dict = self.load_tools()
        self.restrict_tools_to_additional: bool = True
        self.return_agent_code: bool = False
        self.batch_size: int = 1

        self.register(
            SignalCode.LLM_RESPOND_TO_USER_SIGNAL,
            self.llm_stream
        )

    @property
    def is_mistral(self) -> bool:
        return self.model_path == "mistralai/Mistral-7B-Instruct-v0.1"

    @property
    def chat_template(self):
        return (
            "{{ bos_token }}"
            "{% for message in messages %}"
            "{% if message['role'] == 'system' %}"
            "{{ '[INST] <<SYS>>' + message['content'] + ' <</SYS>>[/INST]' }}"
            "{% elif message['role'] == 'user' %}"
            "{{ '[INST] ' + message['content'] + ' [/INST]' }}"
            "{% elif message['role'] == 'assistant' %}"
            "{{ message['content'] + eos_token + ' ' }}"
            "{% endif %}"
            "{% endfor %}"
        ) if self.is_mistral else None

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

    @staticmethod
    def load_tools() -> dict:
        return {
            LLMToolName.QUIT_APPLICATION.value: QuitApplicationTool(),
            LLMToolName.VISION_START_CAPTURE.value: StartVisionCaptureTool(),
            LLMToolName.VISION_STOP_CAPTURE.value: StopVisionCaptureTool(),
            LLMToolName.STT_START_CAPTURE.value: StartAudioCaptureTool(),
            LLMToolName.STT_STOP_CAPTURE.value: StopAudioCaptureTool(),
            LLMToolName.TTS_ENABLE.value: StartSpeakersTool(),
            LLMToolName.TTS_DISABLE.value: StopSpeakersTool(),
            LLMToolName.DESCRIBE_IMAGE.value: ProcessVisionTool,
            LLMToolName.LLM_PROCESS_STT_AUDIO.value: ProcessAudioTool(),
            LLMToolName.DEFAULT_TOOL.value: RespondToUserTool(),
        }

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
        self.batch_size = self.request_data.get("batch_size", 1)

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
        self.agent = LocalAgent(
            model=self.model,
            tokenizer=self.tokenizer,
            additional_tools=self.tools,
            restrict_tools_to_additional=self.restrict_tools_to_additional
        )

    def chat(self):
        return self.agent_chat(self.prompt)
        return self.llm_stream()

    def on_llm_process_stt_audio_signal(self):
        self.llm_stream()

    def get_rendered_template(self, use_latest_human_message: bool = True):
        rendered_template = self.tokenizer.apply_chat_template(
            chat_template=self.chat_template,
            conversation=self.prepare_messages(use_latest_human_message),
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
            rendered_template = rendered_template.replace("{{ " + key + " }}", value)
        return rendered_template

    def llm_stream(self):
        rendered_template = self.get_rendered_template()

        # Encode the rendered template
        encoded = self.tokenizer(rendered_template, return_tensors="pt")
        model_inputs = encoded.to("cuda" if torch.cuda.is_available() else "cpu")

        # Generate the response
        self.logger.info("Generating...")
        self.thread = threading.Thread(target=self.model.generate, kwargs=dict(
            model_inputs,
            min_length=self.min_length,
            max_length=self.max_length,
            num_beams=self.num_beams,
            do_sample=True,
            top_k=self.top_k,
            eta_cutoff=self.eta_cutoff,
            top_p=self.top_p,
            num_return_sequences=self.sequences,
            eos_token_id=self.tokenizer.eos_token_id,
            early_stopping=True,
            repetition_penalty=self.repetition_penalty,
            temperature=self.temperature,
            streamer=self.streamer
        ))
        self.thread.start()
        # strip all new lines from rendered_template:
        rendered_template = rendered_template.replace("\n", " ")
        if self.is_mistral:
            rendered_template = "<s>" + rendered_template
        skip = True
        streamed_template = ""
        replaced = False
        is_end_of_message = False
        is_first_message = True
        for new_text in self.streamer:
            # strip all newlines from new_text
            parsed_new_text = new_text.replace("\n", " ")
            streamed_template += parsed_new_text
            if self.is_mistral:
                streamed_template = streamed_template.replace("<s> [INST]", "<s>[INST]")
                streamed_template = streamed_template.replace("  [INST]", " [INST]")
            # iterate over every character in rendered_template and
            # check if we have the same character in streamed_template
            if not replaced:
                for i, char in enumerate(rendered_template):
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
                streamed_template = streamed_template.replace(rendered_template, "")
            else:
                if self.is_mistral:
                    if "</s>" in new_text:
                        streamed_template = streamed_template.replace("</s>", "")
                        new_text = new_text.replace("</s>", "")
                        is_end_of_message = True
                self.emit(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message=new_text,
                        is_first_message=is_first_message,
                        is_end_of_message=is_end_of_message,
                        name=self.botname,
                    )
                )
                is_first_message = False
        return streamed_template

    def agent_chat(self, prompt: AnyStr) -> AnyStr:
        self.logger.info("Chat Stream")
        res = self.agent.run(
            prompt
        )

        # if not res:
        #     return "No response"
        #
        # if "</s>" in res:
        #     res = res.replace("</s>", "")
        #
        # self.emit(
        #     SignalCode.LLM_TEXT_STREAMED_SIGNAL,
        #     dict(
        #         message=res,
        #         is_first_message=True,
        #         is_end_of_message=True,
        #         name=self.botname,
        #     )
        # )
        # return res
        return ""

    # def on_llm_respond_to_user_signal(self, message):
    #     self.logger.info("Responding to user")
    #     self.prompt = message
    #     self.llm.stream_chat(
    #         self.prepare_messages()
    #     )
    #
    #     full_message = self.stream_text(
    #         response=self.streamer,
    #         action=LLMAction.CHAT
    #     )
    #
    #     self.add_message_to_history(
    #         self.prompt,
    #         LLMChatRole.HUMAN
    #     )
    #     self.add_message_to_history(
    #         full_message,
    #         LLMChatRole.ASSISTANT
    #     )
    #     self.send_final_message()

    def load_streamer(self):
        self.logger.info("Loading LLM text streamer")
        self.streamer = TextIteratorStreamer(self.tokenizer)

    def load_llm(self):
        self.logger.info("Loading RAG")
        self.llm = hf_pipeline(
            task="text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            batch_size=self.batch_size,
            use_fast=True,
            **dict(),
        )

    def do_generate(self):
        self.logger.info("Generating response")
        # self.bot_mood = self.update_bot_mood()
        # self.user_evaluation = self.do_user_evaluation()
        full_message = self.chat()
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

    def latest_human_message(self) -> dict:
        return {} if not self.prompt else {
            "content": self.prompt,
            "role": LLMChatRole.HUMAN.value
        }

    def prepare_messages(
        self,
        use_latest_human_message: bool = True
    ) -> list:
        messages = [
            {
                "content": self.build_system_prompt(),
                "role": LLMChatRole.SYSTEM.value
            }
        ]

        messages += self.history

        if use_latest_human_message:
            messages.append(
                self.latest_human_message()
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
