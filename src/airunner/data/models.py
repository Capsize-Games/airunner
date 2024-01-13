import base64
import datetime
import io
import os

from PIL import Image
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, UniqueConstraint, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex

from airunner.settings import BASE_PATH
from airunner.data.bootstrap.prompt_templates import prompt_template_seed_data


DEFAULT_PATHS = {
    "art": {
        "models": {
            "txt2img": "",
            "depth2img": "",
            "pix2pix": "",
            "inpaint": "",
            "upscale": "",
            "txt2vid": "",
            "embeddings": "",
            "lora": "",
            "vae": "",
        },
        "other": {
            "images": "",
            "videos": "",
        },
    },
    "text": {
        "models": {
            "casuallm": "",
            "seq2seq": "",
            "visualqa": "",
        }
    }
}

for k, v in DEFAULT_PATHS.items():
    for k2, v2 in v.items():
        if isinstance(v2, dict):
            for k3, v3 in v2.items():
                path = os.path.join(BASE_PATH, k, k2, k3)
                DEFAULT_PATHS[k][k2][k3] = path
                #check if path exists, if not, create it:
                if not os.path.exists(path):
                    print("creating path: ", path)
                    os.makedirs(path)
        else:
            path = os.path.join(BASE_PATH, k, k2)
            DEFAULT_PATHS[k][k2] = path
            #check if path exists, if not, create it:
            if not os.path.exists(path):
                print("creating path: ", path)
                os.makedirs(path)


class ModelBase(QAbstractTableModel):
    _headers = []

    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            attr = self._headers[col]["column_name"]
            if hasattr(self._data[row], attr):
                return getattr(self._data[row], attr)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]["display_name"]
        return None


Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Embedding(BaseModel):
    __tablename__ = 'embeddings'

    name = Column(String)
    path = Column(String)
    tags = Column(String)
    active = Column(Boolean, default=True)
    version = Column(String, default="SD 1.5")

    __table_args__ = (
        UniqueConstraint('name', 'path', name='name_path_unique'),
    )


class Scheduler(BaseModel):
    __tablename__ = "schedulers"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    display_name = Column(String)


class ActionScheduler(BaseModel):
    __tablename__ = "action_schedulers"

    id = Column(Integer, primary_key=True)
    section = Column(String)
    generator_name = Column(String)
    scheduler_id = Column(Integer, ForeignKey('schedulers.id'))
    scheduler = relationship("Scheduler", backref="action_schedulers")


class SavedPrompt(BaseModel):
    __tablename__ = 'saved_prompts'

    id = Column(Integer, primary_key=True)
    prompt = Column(String)
    negative_prompt = Column(String)

    __table_args__ = (
        UniqueConstraint('prompt', 'negative_prompt', name='prompt_negative_prompt_unique'),
    )


class ControlnetModel(BaseModel):
    __tablename__ = 'controlnet_models'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    default = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)

    def __repr__(self):
        return f"<ControlnetModel(name='{self.name}', path='{self.path}', default='{self.is_default}')>"


class AIModel(BaseModel):
    __tablename__ = 'ai_models'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    branch = Column(String)
    version = Column(String)
    category = Column(String)
    pipeline_action = Column(String)
    enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=True)
    model_type = Column(String, default="art")


class Pipeline(BaseModel):
    __tablename__ = 'pipelines'

    id = Column(Integer, primary_key=True)
    category = Column(String)
    version = Column(String)
    pipeline_action = Column(String)
    classname = Column(String)
    singlefile_classname = Column(String)
    default = Column(Boolean, default=True)


class Lora(BaseModel):
    __tablename__ = 'loras'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    scale = Column(Float)
    enabled = Column(Boolean, default=True)
    loaded = Column(Boolean, default=False)
    trigger_word = Column(String, default="")
    version = Column(String, default="SD 1.5")

    @classmethod
    def get_all(cls, session):
        return session.query(cls).all()

    __table_args__ = (
        UniqueConstraint('name', 'path', name='name_path_unique'),
    )


class Brush(BaseModel):
    __tablename__ = 'brushes'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    thumbnail = Column(String, nullable=False)
    

class ImageFilter(BaseModel):
    __tablename__ = 'image_filter'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    display_name = Column(String)
    image_filter_values = relationship("ImageFilterValue", back_populates="image_filter", lazy='joined')
    auto_apply = Column(Boolean, default=False)
    filter_class = Column(String, default="")


class ImageFilterValue(BaseModel):
    __tablename__ = 'image_filter_value'

    id = Column(Integer, primary_key=True)
    image_filter_id = Column(Integer, ForeignKey('image_filter.id'))
    image_filter = relationship("ImageFilter", back_populates="image_filter_values")
    name = Column(String)
    value = Column(String)
    value_type = Column(String, default="int")
    min_value = Column(Integer, default=0)
    max_value = Column(Integer, default=100)


class StandardImageWidgetSettings(BaseModel):
    __tablename__ = 'standard_image_widget_settings'

    image_similarity = Column(Integer, default=1000)
    controlnet = Column(String, default="Canny")
    prompt = Column(String, default="")
    negative_prompt = Column(String, default="")
    upscale_model = Column(String, default="RealESRGAN_x4plus")
    face_enhance = Column(Boolean, default=False)


class Layer(BaseModel):
    __tablename__ = 'layers'

    @property
    def image(self):
        # convert base64 image to pil image
        if self.base_64_image:
            decoded_image = base64.b64decode(self.base_64_image)
            bytes_image = io.BytesIO(decoded_image)
            # convert bytes to PIL iamge:
            image = Image.open(bytes_image)
            image = image.convert("RGBA")
            return image
        return None

    @image.setter
    def image(self, value):
        # convert to base 64
        if value:
            buffered = io.BytesIO()
            value.save(buffered, format="PNG")
            self.base_64_image = base64.b64encode(buffered.getvalue())
        else:
            self.base_64_image = ""

    document_id = Column(Integer, ForeignKey('documents.id'))
    document = relationship("Document", backref="layers")
    name = Column(String)
    visible = Column(Boolean, default=True)
    opacity = Column(Integer, default=10000)
    position = Column(Integer, default=0)
    base_64_image = Column(String, default="")
    pos_x = Column(Integer, default=0)
    pos_y = Column(Integer, default=0)
    pivot_point_x = Column(Integer, default=0)
    pivot_point_y = Column(Integer, default=0)
    root_point_x = Column(Integer, default=0)
    root_point_y = Column(Integer, default=0)


class Document(BaseModel):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    active = Column(Boolean, default=False)


class LLMModelVersion(BaseModel):
    __tablename__ = 'llm_model_version'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String)


class LLMPromptTemplate(BaseModel):
    __tablename__ = 'llm_prompt_templates'
    name = Column(String, default="Mistral 7B Instruct: Default Chatbot")
    system_instructions = Column(String, default="""You are {{ botname }}. You are having a conversation with {{ username }}. {{ username }} is the user and you are the assistant. You should stay in character and respond as {{ botname }}.
DO NOT use emojis.
DO NOT use actions (e.g. *action here*).
DO NOT talk like this is a chat room or instant messenger, talk like you are having a conversation in real life.
Always respond in a way that is appropriate to the conversation and sounds like something {{ botname }} would really say.
{{ botname }}'s mood is {{ bot_mood }}
{{ botname }}'s personality is {{ bot_personality }}""")
    model = Column(String, default="mistralai/Mistral-7B-Instruct-v0.1")
    llm_category = Column(String, default="casuallm")
    template = Column(String, default="""###

Previous Conversation:
'''
{{ history }}
'''

{{ username }}: '{{ input }}'
{{ botname }}: 
""")



# class Conversation(BaseModel):
#     __tablename__ = 'conversation'
#     id = Column(Integer, primary_key=True)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     messages = relationship('Message', back_populates='conversation')


# class Message(BaseModel):
#     __tablename__ = 'messages'
#     id = Column(Integer, primary_key=True)
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)
#     name = Column(String)
#     message = Column(String)
#     conversation_id = Column(Integer, ForeignKey('conversation.id'))
#     conversation = relationship('Conversation', back_populates='messages')

