from transformers.generation.streamers import TextIteratorStreamer
from transformers.models.mistral.modeling_mistral import MistralForCausalLM

from airunner.aihandler.llm.agent.ai_runner_agent import AIRunnerAgent
from airunner.aihandler.llm.tokenizer_handler import TokenizerHandler
from airunner.enums import SignalCode
from airunner.enums import LLMActionType
from airunner.utils.get_current_chatbot import get_current_chatbot_property


class CausalLMTransformerBaseHandler(
    TokenizerHandler
):
    auto_class_ = MistralForCausalLM

    def __init__(self, *args, **kwargs):
        self.streamer = None
        self.chat_engine = None
        self.chat_agent = None
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
        self.tools: dict = self.load_tools()
        self.action: LLMActionType = LLMActionType.CHAT
        self.use_personality: bool = False
        self.use_mood: bool = False
        self.use_guardrails: bool = False
        self.use_system_instructions: bool = False
        self.assign_names: bool = False
        self.prompt_template: str = ""
        self.guardrails_prompt: str = ""
        self.system_instructions: str = ""
        self.restrict_tools_to_additional: bool = True
        self.return_agent_code: bool = False
        self.batch_size: int = 1
        self.vision_history: list = []

        super().__init__(*args, **kwargs)

        self.register(SignalCode.LLM_LOAD_SIGNAL, self.on_load_llm_signal)
        self.register(SignalCode.LLM_CLEAR_HISTORY_SIGNAL, self.on_clear_history_signal)
        self.register(SignalCode.INTERRUPT_PROCESS_SIGNAL, self.on_interrupt_process_signal)

    def on_load_llm_signal(self, _message: dict):
        self.load()

    def on_interrupt_process_signal(self, _message: dict):
        if self.chat_agent is not None:
            self.chat_agent.interrupt_process()

    def on_clear_history_signal(self, _message):
        if self.chat_agent is not None:
            self.logger.debug("Clearing chat history")
            self.chat_agent.history = []

    @property
    def is_mistral(self) -> bool:
        return "mistral" in self.model_path

    @property
    def chat_template(self):
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
            # LLMToolName.QUIT_APPLICATION.value: QuitApplicationTool(),
            # LLMToolName.VISION_START_CAPTURE.value: StartVisionCaptureTool(),
            # LLMToolName.VISION_STOP_CAPTURE.value: StopVisionCaptureTool(),
            # LLMToolName.STT_START_CAPTURE.value: StartAudioCaptureTool(),
            # LLMToolName.STT_STOP_CAPTURE.value: StopAudioCaptureTool(),
            # LLMToolName.TTS_ENABLE.value: StartSpeakersTool(),
            # LLMToolName.TTS_DISABLE.value: StopSpeakersTool(),
            # LLMToolName.DESCRIBE_IMAGE.value: ProcessVisionTool,
            # LLMToolName.LLM_PROCESS_STT_AUDIO.value: ProcessAudioTool(),
            # LLMToolName.BASH_EXECUTE.value: BashExecuteTool(),
            # LLMToolName.WRITE_FILE.value: WriteFileTool(),
            #LLMToolName.DEFAULT_TOOL.value: RespondToUserTool(),
        }

    def process_data(self, data):
        super().process_data(data)

        current_bot = self.settings["llm_generator_settings"]["saved_chatbots"][
            self.settings["llm_generator_settings"]["current_chatbot"]]

        self._username = current_bot["username"]
        self._botname = current_bot["botname"]
        self.bot_mood = current_bot["bot_mood"]
        self.bot_personality = current_bot["bot_personality"]
        self.use_personality = current_bot["use_personality"]
        self.use_mood = current_bot["use_mood"]
        self.use_guardrails = current_bot["use_guardrails"]
        self.use_system_instructions = current_bot["use_system_instructions"]
        self.assign_names = current_bot["assign_names"]
        self.prompt_template = current_bot["prompt_template"]
        self.guardrails_prompt = current_bot["guardrails_prompt"]
        self.system_instructions = current_bot["system_instructions"]
        self.batch_size = self.settings["llm_generator_settings"]["batch_size"]
        self.vision_history = data.get("vision_history", [])
        action = self.settings["llm_generator_settings"]["action"]
        for action_type in LLMActionType:
            if action_type.value == action:
                self.action = action_type
                break

    def post_load(self):
        super().post_load()

        do_load_streamer = self.streamer is None
        if do_load_streamer:
            self.load_streamer()

        do_load_agent = self.chat_agent is None
        if do_load_agent:
            self.load_agent()

    def load_agent(self):
        self.logger.debug("Loading agent")
        # query_engine_tool = QueryEngineTool(
        #     query_engine=self.query_engine,
        #     metadata=ToolMetadata(
        #         name="help_agent",
        #         description="Agent that can return help results about the application."
        #     )
        # )
        self.logger.debug("Loading local agent")
        self.chat_agent = AIRunnerAgent(
            model=self.model,
            tokenizer=self.tokenizer,
            streamer=self.streamer,
            tools=self.tools,
            chat_template=self.chat_template,
        )

    def unload_agent(self):
        self.logger.debug("Unloading agent")
        do_clear_memory = False
        if self.chat_agent is not None:
            self.logger.debug("Unloading chat agent")
            self.chat_agent.unload()
            self.chat_agent = None
            do_clear_memory = True
        return do_clear_memory

    def on_llm_process_stt_audio_signal(self):
        print("TODO: on_llm_process_stt_audio_signal")

    def load_streamer(self):
        self.logger.debug("Loading LLM text streamer")
        self.streamer = TextIteratorStreamer(self.tokenizer)

    def unload(self, do_clear_memory = False):
        self.logger.debug("Unloading LLM")
        if self.streamer is not None:
            self.logger.debug("Unloading streamer")
            self.streamer = None
            do_clear_memory = True
        if self.llm_with_tools is not None:
            self.logger.debug("Unloading LLM with tools")
            self.llm_with_tools = None
            do_clear_memory = True
        if self.agent_executor is not None:
            self.logger.debug("Unloading agent executor")
            self.agent_executor = None
            do_clear_memory = True
        if self.embed_model is not None:
            self.logger.debug("Unloading embed model")
            self.embed_model = None
            do_clear_memory = True
        if self.unload_agent():
            do_clear_memory = True

        super().unload(do_clear_memory=do_clear_memory)

    def do_generate(self):
        self.logger.debug("Generating response")
        # self.bot_mood = self.update_bot_mood()
        # self.user_evaluation = self.do_user_evaluation()
        #full_message = self.rag_stream()
        self.emit_signal(SignalCode.VISION_CAPTURE_LOCK_SIGNAL)

        if self.chat_agent is not None:
            if self.action != LLMActionType.GENERATE_IMAGE:
                use_tool_filter = get_current_chatbot_property(self.settings, "use_tool_filter")
                if use_tool_filter:
                    print("USE TOOL FILTER HERE")
                self.chat_agent.run(
                    self.prompt,
                    self.action,
                    vision_history=self.vision_history,
                    **self.override_parameters
                )
            else:
                self.chat_agent.run(
                    self.prompt,
                    LLMActionType.GENERATE_IMAGE
                )

        self.send_final_message()
        self.emit_signal(SignalCode.VISION_CAPTURE_UNLOCK_SIGNAL)

    def emit_streamed_text_signal(self, **kwargs):
        kwargs["name"] = self.botname
        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            kwargs
        )

    def send_final_message(self):
        self.emit_streamed_text_signal(
            message="",
            is_first_message=False,
            is_end_of_message=True
        )

    def load_chat_engine(self):
        self.chat_engine = self.index.as_chat_engine()
