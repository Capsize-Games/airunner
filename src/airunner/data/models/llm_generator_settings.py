from sqlalchemy import Column, Integer, Boolean, String, BigInteger

from airunner.data.models.base import Base


class LLMGeneratorSettings(Base):
    __tablename__ = 'llm_generator_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String, default="CHAT")
    use_tool_filter = Column(Boolean, default=False)
    seed = Column(BigInteger, default=0)
    random_seed = Column(Boolean, default=False)
    model_version = Column(String, default="w4ffl35/Mistral-7B-Instruct-v0.3-4bit")
    dtype = Column(String, default="4bit")
    use_gpu = Column(Boolean, default=True)
    message_type = Column(String, default="chat")
    override_parameters = Column(Boolean, default=True)
    current_chatbot = Column(Integer, default=1)
    prompt_template = Column(String, default="Mistral 7B Instruct: Default Chatbot")
    batch_size = Column(Integer, default=1)
    use_api = Column(Boolean, default=False)
    api_key = Column(String, nullable=True)
    api_model = Column(String, nullable=True)
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
    sequences = Column(Integer, default=1)
    decoder_start_token_id = Column(Integer, nullable=True)
    use_cache = Column(Boolean, default=True)
    length_penalty = Column(Integer, default=100)