from sqlalchemy import Column, Integer, String, Boolean, Text, BigInteger
from sqlalchemy.orm import relationship

from airunner.data.models.base import Base
from airunner.settings import DEFAULT_CHATBOT_GUARDRAILS_PROMPT, DEFAULT_CHATBOT_SYSTEM_PROMPT


class Chatbot(Base):
    __tablename__ = 'chatbots'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="Chatbot")
    botname = Column(String, default="Computer")
    use_personality = Column(Boolean, default=True)
    use_mood = Column(Boolean, default=True)
    use_guardrails = Column(Boolean, default=True)
    use_system_instructions = Column(Boolean, default=True)
    use_datetime = Column(Boolean, default=True)
    assign_names = Column(Boolean, default=True)
    bot_personality = Column(Text, default="happy. He loves {{ username }}")
    prompt_template = Column(Text, default="Mistral 7B Instruct: Default Chatbot")
    use_tool_filter = Column(Boolean, default=False)
    use_gpu = Column(Boolean, default=True)
    skip_special_tokens = Column(Boolean, default=True)
    sequences = Column(Integer, default=1)
    seed = Column(BigInteger, default=42)
    random_seed = Column(Boolean, default=True)
    model_version = Column(String, default="w4ffl35/Mistral-7B-Instruct-v0.3-4bit")
    model_type = Column(String, default="llm")
    dtype = Column(String, default="4bit")
    return_result = Column(Boolean, default=True)
    guardrails_prompt = Column(Text, default=DEFAULT_CHATBOT_GUARDRAILS_PROMPT)
    system_instructions = Column(Text, default=DEFAULT_CHATBOT_SYSTEM_PROMPT)
    top_p = Column(Integer, default=900)
    min_length = Column(Integer, default=1)
    max_new_tokens = Column(Integer, default=1000)
    repetition_penalty = Column(Integer, default=100)
    do_sample = Column(Boolean, default=True)
    early_stopping = Column(Boolean, default=True)
    num_beams = Column(Integer, default=1)
    temperature = Column(Integer, default=1000)
    ngram_size = Column(Integer, default=2)
    top_k = Column(Integer, default=10)
    eta_cutoff = Column(Integer, default=10)
    num_return_sequences = Column(Integer, default=1)
    decoder_start_token_id = Column(Integer, default=None)
    use_cache = Column(Boolean, default=True)
    length_penalty = Column(Integer, default=100)
    backstory = Column(Text, default="")
    use_backstory = Column(Boolean, default=True)
    use_weather_prompt = Column(Boolean, default=False)

    target_files = relationship("TargetFiles", back_populates="chatbot")
    target_directories = relationship("TargetDirectories", back_populates="chatbot")