from transformers import AutoModelForCausalLM
from transformers.generation.streamers import TextIteratorStreamer

from airunner.aihandler.llm.agent.base_agent import BaseAgent
from airunner.aihandler.llm.tokenizer_handler import TokenizerHandler
from airunner.enums import SignalCode, ModelType
from airunner.enums import LLMActionType


class CausalLMTransformerBaseHandler(
    TokenizerHandler
):
    auto_class_ = AutoModelForCausalLM
    model_type = ModelType.LLM

    def __init__(self, agent_class: BaseAgent, *args, **kwargs):
        self.agent_class_ = agent_class if agent_class is not None else BaseAgent
        self.agent_options = kwargs.pop("agent_options", {})
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
        self.model_type = ModelType.LLM
        super().__init__(*args, **kwargs)

    def on_load_llm_signal(self):
        self.load()

    def on_load_model_signal(self):
        self.load_model()

    def on_interrupt_process_signal(self):
        if self.chat_agent is not None:
            self.chat_agent.interrupt_process()

    def on_clear_history_signal(self):
        if self.chat_agent is not None:
            self.logger.debug("Clearing chat history")
            self.chat_agent.clear_history()

    @property
    def is_mistral(self) -> bool:
        path = self.model_path.lower()
        return "mistral" in path

    @property
    def is_llama_instruct(self):
        path = self.model_path.lower()
        if "instruct" in path and "llama" in path:
            return True
        return False

    @property
    def chat_template(self):
        if self.is_mistral:
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
            )
        elif self.is_llama_instruct:
            return (
                "{{ '<|begin_of_text|>' }}"
                "{% for message in messages %}"
                "{{ '<|start_header_id|>' + "
                "message['role'] + '<|end_header_id|>' + '\n\n' + message['content'] + "
                "'<|end_header_id|>\n\n' + message['content'] + '<|eot_id|>' }}"
                "{% endfor %}"
            )

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
            # LLMToolName.STT_START_CAPTURE.value: StartAudioCaptureTool(),
            # LLMToolName.STT_STOP_CAPTURE.value: StopAudioCaptureTool(),
            # LLMToolName.TTS_ENABLE.value: StartSpeakersTool(),
            # LLMToolName.TTS_DISABLE.value: StopSpeakersTool(),
            # LLMToolName.LLM_PROCESS_STT_AUDIO.value: ProcessAudioTool(),
            # LLMToolName.BASH_EXECUTE.value: BashExecuteTool(),
            # LLMToolName.WRITE_FILE.value: WriteFileTool(),
        }

    def process_data(self, data):
        super().process_data(data)
        self._username = self.chatbot.username
        self._botname = self.chatbot.botname
        self.bot_mood = self.chatbot.bot_mood
        self.bot_personality = self.chatbot.bot_personality
        self.use_personality = self.chatbot.use_personality
        self.use_mood = self.chatbot.use_mood
        self.use_guardrails = self.chatbot.use_guardrails
        self.use_system_instructions = self.chatbot.use_system_instructions
        self.assign_names = self.chatbot.assign_names
        self.prompt_template = self.chatbot.prompt_template
        self.guardrails_prompt = self.chatbot.guardrails_prompt
        self.system_instructions = self.chatbot.system_instructions
        self.batch_size = self.llm_generator_settings.batch_size
        action = self.llm_generator_settings.action
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
        self.chat_agent = self.agent_class_(
            model=self.model,
            tokenizer=self.tokenizer,
            streamer=self.streamer,
            tools=self.tools,
            chat_template=self.chat_template,
            is_mistral=self.is_mistral,
        )

    def unload_agent(self):
        self.logger.debug("Unloading agent")
        do_clear_memory = False
        if self.chat_agent is not None:
            self.logger.debug("Unloading chat agent")
            self.chat_agent.unload()
            del self.chat_agent
            self.chat_agent = None
            do_clear_memory = True
        return do_clear_memory

    def on_llm_process_stt_audio_signal(self):
        print("TODO: on_llm_process_stt_audio_signal")

    def load_streamer(self):
        self.logger.debug("Loading LLM text streamer")
        self.streamer = TextIteratorStreamer(self.tokenizer)

    def unload(self):
        self.logger.debug("Unloading LLM")
        self.unload_streamer()
        self.unload_llm_with_tools()
        self.unload_agent_executor()
        self.unload_embed_model()
        self.unload_agent()
        super().unload()

    def unload_streamer(self):
        self.logger.debug("Unloading streamer")
        del self.streamer
        self.streamer = None

    def unload_llm_with_tools(self):
        self.logger.debug("Unloading LLM with tools")
        del self.llm_with_tools
        self.llm_with_tools = None

    def unload_agent_executor(self):
        self.logger.debug("Unloading agent executor")
        del self.agent_executor
        self.agent_executor = None

    def unload_embed_model(self):
        self.logger.debug("Unloading embed model")
        del self.embed_model
        self.embed_model = None

    def do_generate(self, prompt, action):
        self.logger.debug("Generating response")
        if action is LLMActionType.CHAT and self.chatbot.use_mood:
            print("*" * 100)
            print("UPDATE MOOD")
            print("*" * 100)
            action = LLMActionType.UPDATE_MOOD
        self.chat_agent.run(
            prompt,
            action
        )
        self.send_final_message()

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
