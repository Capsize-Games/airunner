from sqlalchemy import Column, Integer, Boolean, String

from airunner.data.models.base import BaseModel


class TTSSettings(BaseModel):
    __tablename__ = 'tts_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tts_model = Column(String, default="SpeechT5")
    use_cuda = Column(Boolean, default=True)
    use_sentence_chunks = Column(Boolean, default=True)
    use_word_chunks = Column(Boolean, default=False)
    cuda_index = Column(Integer, default=0)
    word_chunks = Column(Integer, default=1)
    sentence_chunks = Column(Integer, default=1)
    model = Column(String, default="SpeechT5")