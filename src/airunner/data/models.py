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
from airunner.utils import default_hf_cache_dir
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


class PromptStyleCategoryModel(ModelBase):
    _headers = [
        {
            "display_name": "ID",
            "column_name": "id"
        },
        {
            "display_name": "Name",
            "column_name": "name"
        },
        {
            "display_name": "Negative Prompt",
            "column_name": "negative_prompt"
        }
    ]


class PromptStyleCategory(BaseModel):
    __tablename__ = 'prompt_style_category'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    negative_prompt = Column(String)


class PromptStyle(BaseModel):
    __tablename__ = 'prompt_style'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    style_category_id = Column(Integer, ForeignKey('prompt_style_category.id'))
    style_category = relationship("PromptStyleCategory", backref="styles")


class PromptCategory(BaseModel):
    __tablename__ = 'prompt_category'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    negative_prompt = Column(String)


class PromptVariableCategory(BaseModel):
    __tablename__ = 'prompt_variable_category'

    id = Column(Integer, primary_key=True)
    name = Column(String)


class PromptVariableCategoryWeight(BaseModel):
    __tablename__ = 'prompt_variable_category_weight'

    id = Column(Integer, primary_key=True)
    weight = Column(Float)
    prompt_category_id = Column(Integer, ForeignKey('prompt_category.id'))
    prompt_category = relationship("PromptCategory", backref="weights")
    variable_category_id = Column(Integer, ForeignKey('prompt_variable_category.id'))
    variable_category = relationship("PromptVariableCategory", backref="weights")


class PromptVariable(BaseModel):
    __tablename__ = 'prompt_variables'

    id = Column(Integer, primary_key=True)
    value = Column(String)
    prompt_category_id = Column(Integer, ForeignKey('prompt_category.id'))
    prompt_category = relationship("PromptCategory", backref="variables")
    variable_category_id = Column(Integer, ForeignKey('prompt_variable_category.id'))
    variable_category = relationship("PromptVariableCategory", backref="variables")


class PromptOption(BaseModel):
    __tablename__ = 'prompt_option'

    id = Column(Integer, primary_key=True)
    prompt_id = Column(Integer, ForeignKey('prompts.id'))
    text = Column(String, default="")
    cond = Column(String, default="")
    else_cond = Column(String, default="")
    or_cond = Column(String, default="")

    next_cond_id = Column(Integer, ForeignKey('prompt_option.id'), nullable=True)
    next_cond = Column(Integer, ForeignKey('prompt_option.id'), nullable=True)

    next = relationship(
        "PromptOption",
        backref="prev",
        remote_side=[id],
        foreign_keys=[next_cond_id]
    )


class Prompt(BaseModel):
    __tablename__ = 'prompts'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    category_id = Column(Integer, ForeignKey('prompt_category.id'))
    category = relationship("PromptCategory", backref="prompts")
    options = relationship("PromptOption", backref="prompts")


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


class SplitterSection(BaseModel):
    __tablename__ = 'splitter_section'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    order = Column(Integer)
    size = Column(Integer)


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


class MetadataSettings(BaseModel):
    __tablename__ = 'metadata_settings'

    id = Column(Integer, primary_key=True)
    image_export_metadata_prompt = Column(Boolean, default=True)
    image_export_metadata_negative_prompt = Column(Boolean, default=True)
    image_export_metadata_scale = Column(Boolean, default=True)
    image_export_metadata_seed = Column(Boolean, default=True)
    image_export_metadata_latents_seed = Column(Boolean, default=True)
    image_export_metadata_steps = Column(Boolean, default=True)
    image_export_metadata_ddim_eta = Column(Boolean, default=True)
    image_export_metadata_iterations = Column(Boolean, default=True)
    image_export_metadata_samples = Column(Boolean, default=True)
    image_export_metadata_model = Column(Boolean, default=True)
    image_export_metadata_model_branch = Column(Boolean, default=True)
    image_export_metadata_scheduler = Column(Boolean, default=True)
    export_metadata = Column(Boolean, default=True)
    import_metadata = Column(Boolean, default=True)
    

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


class ActiveGridSettings(BaseModel):
    __tablename__ = 'active_grid_settings'

    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=True)
    render_border = Column(Boolean, default=True)
    render_fill = Column(Boolean, default=True)
    border_opacity = Column(Integer, default=50)
    fill_opacity = Column(Integer, default=50)
    pos_x = Column(Integer, default=0)
    pos_y = Column(Integer, default=0)
    width = Column(Integer, default=512)
    height = Column(Integer, default=512)


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


class LLMGenerator(BaseModel):
    __tablename__ = 'llm_generator'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String, default="casuallm")
    username = Column(String, default="User")
    botname = Column(String, default="Bot")
    model_versions = relationship('LLMModelVersion', back_populates='generator')
    message_type = Column(String, default="chat")
    bot_personality = Column(String, default="Nice")
    override_parameters = Column(Boolean, default=False)
    prompt_template = Column(String, default=prompt_template_seed_data[0]["name"])


class LLMGeneratorSetting(BaseModel):
    __tablename__ = 'llm_generator_settings'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    top_p = Column(Integer, default=90)
    max_length = Column(Integer, default=50)
    repetition_penalty = Column(Integer, default=100)
    min_length = Column(Integer, default=10)
    length_penalty = Column(Integer, default=100)
    num_beams = Column(Integer, default=1)
    ngram_size = Column(Integer, default=0)
    temperature = Column(Integer, default=100)
    sequences = Column(Integer, default=1)
    top_k = Column(Integer, default=0)
    seed = Column(Integer, default=0)
    do_sample = Column(Boolean, default=False)
    eta_cutoff = Column(Integer, default=10)
    early_stopping = Column(Boolean, default=False)
    random_seed = Column(Boolean, default=False)
    model_version = Column(String, default="google/flan-t5-xl")
    generator_id = Column(Integer, ForeignKey('llm_generator.id'))
    dtype = Column(String, default="4bit")
    use_gpu = Column(Boolean, default=True)


class LLMModelVersion(BaseModel):
    __tablename__ = 'llm_model_version'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String)
    generator_id = Column(Integer, ForeignKey('llm_generator.id'))
    generator = relationship('LLMGenerator', back_populates='model_versions')


class LLMPromptTemplate(BaseModel):
    __tablename__ = 'llm_prompt_templates'
    name = Column(String, default="")
    template = Column(String, default="")


class Conversation(BaseModel):
    __tablename__ = 'conversation'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship('Message', back_populates='conversation')


class Message(BaseModel):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String)
    message = Column(String)
    conversation_id = Column(Integer, ForeignKey('conversation.id'))
    conversation = relationship('Conversation', back_populates='messages')

