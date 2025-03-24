import os
from sqlalchemy import Column, Integer, String

from airunner.data.models.base import BaseModel
from airunner.settings import AIRUNNER_BASE_PATH


class PathSettings(BaseModel):
    __tablename__ = 'path_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    base_path = Column(String, default=AIRUNNER_BASE_PATH)
    documents_path = Column(String, default=os.path.expanduser(os.path.join(AIRUNNER_BASE_PATH, "text/other", "documents")))
    ebook_path = Column(String, default=os.path.expanduser(os.path.join(AIRUNNER_BASE_PATH, "text/other", "ebooks")))
    image_path = Column(String, default=os.path.expanduser(os.path.join(AIRUNNER_BASE_PATH, "art/other", "images")))
    llama_index_path = Column(String, default=os.path.expanduser(os.path.join(AIRUNNER_BASE_PATH, "text/rag", "db")))
    webpages_path = Column(String, default=os.path.expanduser(os.path.join(AIRUNNER_BASE_PATH, "text/other", "webpages")))
    stt_model_path = Column(String, default=os.path.expanduser(os.path.join(AIRUNNER_BASE_PATH, "text/models/stt")))
    tts_model_path = Column(String, default=os.path.expanduser(os.path.join(AIRUNNER_BASE_PATH, "text/models/tts")))

    def tts_processor_path(self) -> str:
        return os.path.join(self.tts_model_path, "processor")
