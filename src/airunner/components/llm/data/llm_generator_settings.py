from sqlalchemy import Column, Integer, Boolean, String, BigInteger
import os

from airunner.components.data.models.base import BaseModel
from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH
from airunner.enums import ModelService


class LLMGeneratorSettings(BaseModel):
    __tablename__ = "llm_generator_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String, default="CHAT")
    use_tool_filter = Column(Boolean, default=False)
    seed = Column(BigInteger, default=0)
    random_seed = Column(Boolean, default=False)
    model_version = Column(String, default=AIRUNNER_DEFAULT_LLM_HF_PATH)
    dtype = Column(String, default="4bit")
    use_gpu = Column(Boolean, default=True)
    message_type = Column(String, default="chat")
    override_parameters = Column(Boolean, default=True)
    prompt_template = Column(
        String, default="Ministral 8B Instruct: Default Chatbot"
    )
    batch_size = Column(Integer, default=1)
    use_api = Column(Boolean, default=False)
    api_key = Column(String, nullable=True)
    api_model = Column(String, nullable=True)
    top_p = Column(Integer, default=950)  # Qwen3 thinking mode: 0.95
    min_length = Column(Integer, default=1)
    max_new_tokens = Column(Integer, default=32768)  # Qwen3 recommended output length
    repetition_penalty = Column(Integer, default=100)
    do_sample = Column(
        Boolean, default=True
    )  # Changed from False - required for temperature to work
    early_stopping = Column(Boolean, default=True)
    num_beams = Column(Integer, default=1)
    temperature = Column(
        Integer, default=7000
    )  # Changed from 1000 -> 0.7 for natural conversation
    ngram_size = Column(Integer, default=0)
    top_k = Column(Integer, default=20)  # Qwen3 recommended value
    eta_cutoff = Column(Integer, default=10)
    sequences = Column(Integer, default=1)
    decoder_start_token_id = Column(Integer, nullable=True)
    use_cache = Column(Boolean, default=True)
    length_penalty = Column(Integer, default=900)
    model_service = Column(String, default=ModelService.LOCAL.value)
    model_path = Column(String, default=AIRUNNER_DEFAULT_LLM_HF_PATH)
    model_id = Column(String, nullable=True)  # Provider config model ID (e.g., "qwen3-8b")
    auto_extract_knowledge = Column(Boolean, default=True)

    # Mode-based routing settings
    use_mode_routing = Column(Boolean, default=False)
    mode_override = Column(String, nullable=True)
    enable_trajectory_logging = Column(Boolean, default=False)

    # Qwen3 thinking mode (enables <think>...</think> reasoning)
    enable_thinking = Column(Boolean, default=True)
