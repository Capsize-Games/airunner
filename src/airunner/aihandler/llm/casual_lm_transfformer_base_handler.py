from airunner.aihandler.llm.agent import AIRunnerAgent
from airunner.aihandler.llm.local_agent import LocalAgent
from transformers import AutoModelForCausalLM, TextIteratorStreamer
from transformers import pipeline as hf_pipeline

from airunner.aihandler.llm.llm_tools import QuitApplicationTool, StartVisionCaptureTool, StopVisionCaptureTool, \
    StartAudioCaptureTool, StopAudioCaptureTool, StartSpeakersTool, StopSpeakersTool, ProcessVisionTool, \
    ProcessAudioTool
from airunner.aihandler.llm.tokenizer_handler import TokenizerHandler
from airunner.enums import SignalCode, LLMToolName, LLMActionType


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
        self.chat_engine = None
        self.action: LLMActionType = LLMActionType.CHAT
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
        self.chat_agent = None
        self.tool_agent = None
        self.tools: dict = self.load_tools()
        self.restrict_tools_to_additional: bool = True
        self.return_agent_code: bool = False
        self.batch_size: int = 1
        self.vision_history: list = []

    @property
    def is_mistral(self) -> bool:
        return "mistral" in self.model_path.lower()

    @property
    def chat_template(self):
        return (
            "{% for message in messages %}"
            "{% if message['role'] == 'system' %}"
            "{{ '[INST] <<SYS>>' + message['content'] + ' <</SYS>>[/INST]' }}"
            "{% elif message['role'] == 'user' %}"
            "{{ '[INST]{{ username }}: ' + message['content'] + ' [/INST]' }}"
            "{% elif message['role'] == 'assistant' %}"
            "{{ botname }}: {{ message['content'] + eos_token + ' ' }}"
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
            #LLMToolName.DEFAULT_TOOL.value: RespondToUserTool(),
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
        self.vision_history = self.request_data.get("vision_history", [])
        action = self.request_data.get("action", LLMActionType.CHAT.value)
        for action_type in LLMActionType:
            if action_type.value == action:
                self.action = action_type
                break

    def post_load(self):
        super().post_load()

        do_load_streamer = self.streamer is None
        if do_load_streamer:
            self.load_streamer()

        do_load_llm = self.llm is None
        if do_load_llm:
            self.load_llm()

        do_load_agent = self.chat_agent is None
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
        self.logger.info("Loading local agent")
        self.tool_agent = LocalAgent(
            model=self.model,
            tokenizer=self.tokenizer,
            additional_tools=self.tools,
            restrict_tools_to_additional=self.restrict_tools_to_additional,
        )
        self.logger.info("Loading chat agent")
        self.chat_agent = AIRunnerAgent(
            model=self.model,
            tokenizer=self.tokenizer,
            streamer=self.streamer,
            tools=self.tools,
            chat_template=self.chat_template,
            username=self.username,
            botname=self.botname,
            bot_mood=self.bot_mood,
            bot_personality=self.bot_personality,
            min_length=self.min_length,
            max_length=self.max_length,
            num_beams=self.num_beams,
            do_sample=self.do_sample,
            top_k=self.top_k,
            eta_cutoff=self.eta_cutoff,
            sequences=self.sequences,
            early_stopping=self.early_stopping,
            repetition_penalty=self.repetition_penalty,
            temperature=self.temperature,
            is_mistral=self.is_mistral,
            top_p=self.top_p,
            guardrails_prompt=self.guardrails_prompt,
            use_guardrails=self.use_guardrails,
            system_instructions=self.system_instructions,
            use_system_instructions=self.use_system_instructions,
            user_evaluation=self.user_evaluation,
            use_mood=self.use_mood,
            use_personality=self.use_personality
        )

    def on_llm_process_stt_audio_signal(self):
        print("TODO: on_llm_process_stt_audio_signal")

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
        #full_message = self.rag_stream()

        if self.action == LLMActionType.CHAT:
            if self.settings["llm_generator_settings"]["use_tool_filter"]:
                self.tool_agent.run(self.prompt)
            self.chat_agent.run(self.prompt, LLMActionType.CHAT, vision_history=self.vision_history)
        elif self.action == LLMActionType.GENERATE_IMAGE:
            self.chat_agent.run(self.prompt, LLMActionType.GENERATE_IMAGE)

        self.send_final_message()

    def emit_streamed_text_signal(self, **kwargs):
        kwargs["name"] = self.botname
        self.emit(
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
