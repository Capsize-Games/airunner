import base64
import datetime
import io
import os

from PIL import Image
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, JSON, UniqueConstraint, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex

from airunner.settings import BASE_PATH


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


class Embedding(Base):
    __tablename__ = 'embeddings'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    tags = Column(String)
    active = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint('name', 'path', name='name_path_unique'),
    )


class Scheduler(Base):
    __tablename__ = "schedulers"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    display_name = Column(String)


class ActionScheduler(Base):
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


class PromptStyleCategory(Base):
    __tablename__ = 'prompt_style_category'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    negative_prompt = Column(String)


class PromptStyle(Base):
    __tablename__ = 'prompt_style'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    style_category_id = Column(Integer, ForeignKey('prompt_style_category.id'))
    style_category = relationship("PromptStyleCategory", backref="styles")


class PromptCategory(Base):
    __tablename__ = 'prompt_category'

    id = Column(Integer, primary_key=True)
    name = Column(String)


class PromptVariableCategory(Base):
    __tablename__ = 'prompt_variable_category'

    id = Column(Integer, primary_key=True)
    name = Column(String)


class PromptVariableCategoryWeight(Base):
    __tablename__ = 'prompt_variable_category_weight'

    id = Column(Integer, primary_key=True)
    weight = Column(Float)
    prompt_category_id = Column(Integer, ForeignKey('prompt_category.id'))
    prompt_category = relationship("PromptCategory", backref="weights")
    variable_category_id = Column(Integer, ForeignKey('prompt_variable_category.id'))
    variable_category = relationship("PromptVariableCategory", backref="weights")


class PromptVariable(Base):
    __tablename__ = 'prompt_variables'

    id = Column(Integer, primary_key=True)
    value = Column(String)
    prompt_category_id = Column(Integer, ForeignKey('prompt_category.id'))
    prompt_category = relationship("PromptCategory", backref="variables")
    variable_category_id = Column(Integer, ForeignKey('prompt_variable_category.id'))
    variable_category = relationship("PromptVariableCategory", backref="variables")


class PromptOption(Base):
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


class Prompt(Base):
    __tablename__ = 'prompts'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    category_id = Column(Integer, ForeignKey('prompt_category.id'))
    category = relationship("PromptCategory", backref="prompts")
    options = relationship("PromptOption", backref="prompts")


class SavedPrompt(Base):
    __tablename__ = 'saved_prompts'

    id = Column(Integer, primary_key=True)
    prompt = Column(String)
    negative_prompt = Column(String)

    __table_args__ = (
        UniqueConstraint('prompt', 'negative_prompt', name='prompt_negative_prompt_unique'),
    )


class ControlnetModel(Base):
    __tablename__ = 'controlnet_models'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    path = Column(String)
    default = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)

    def __repr__(self):
        return f"<ControlnetModel(name='{self.name}', path='{self.path}', default='{self.is_default}')>"


class AIModel(Base):
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


class Pipeline(Base):
    __tablename__ = 'pipelines'

    id = Column(Integer, primary_key=True)
    category = Column(String)
    version = Column(String)
    pipeline_action = Column(String)
    classname = Column(String)
    singlefile_classname = Column(String)
    default = Column(Boolean, default=True)


class SplitterSection(Base):
    __tablename__ = 'splitter_section'

    id = Column(Integer, primary_key=True)
    settings_id = Column(Integer, ForeignKey('settings.id'))
    name = Column(String)
    order = Column(Integer)
    size = Column(Integer)


class Lora(Base):
    __tablename__ = 'loras'

    id = Column(Integer, primary_key=True)
    settings_id = Column(Integer, ForeignKey('settings.id'))
    name = Column(String)
    path = Column(String)
    scale = Column(Float)
    enabled = Column(Boolean, default=True)
    loaded = Column(Boolean, default=False)
    trigger_word = Column(String, default="")

    @classmethod
    def get_all(cls, session):
        return session.query(cls).all()

    __table_args__ = (
        UniqueConstraint('name', 'path', name='name_path_unique'),
    )


class GeneratorSetting(Base):
    __tablename__ = 'generator_settings'

    id = Column(Integer, primary_key=True)
    section = Column(String)
    generator_name = Column(String)
    settings_id = Column(Integer, ForeignKey('settings.id'))
    prompt = Column(String, default="")
    negative_prompt = Column(String, default="")
    steps = Column(Integer, default=20)
    ddim_eta = Column(Float, default=0.5)
    height = Column(Integer, default=512)
    width = Column(Integer, default=512)
    scale = Column(Integer, default=750)
    seed = Column(Integer, default=42)
    latents_seed = Column(Integer, default=84)
    random_seed = Column(Boolean, default=True)
    random_latents_seed = Column(Boolean, default=True)
    model = Column(String, default="")
    scheduler = Column(String, default="")
    prompt_triggers = Column(String, default="")
    strength = Column(Integer, default=50)
    image_guidance_scale = Column(Integer, default=150)
    n_samples = Column(Integer, default=1)
    controlnet = Column(String, default="")
    enable_controlnet = Column(Boolean, default=False)
    enable_input_image = Column(Boolean, default=False)
    controlnet_guidance_scale = Column(Integer, default=50)
    clip_skip = Column(Integer, default=0)
    variation = Column(Boolean, default=False)
    input_image_use_imported_image = Column(Boolean, default=False)
    input_image_use_grid_image = Column(Boolean, default=True)
    input_image_recycle_grid_image = Column(Boolean, default=True)
    input_image_mask_use_input_image = Column(Boolean, default=True)
    input_image_mask_use_imported_image = Column(Boolean, default=False)
    controlnet_input_image_link_to_input_image = Column(Boolean, default=True)
    controlnet_input_image_use_imported_image = Column(Boolean, default=False)
    controlnet_use_grid_image = Column(Boolean, default=False)
    controlnet_recycle_grid_image = Column(Boolean, default=False)
    controlnet_mask_link_input_image = Column(Boolean, default=False)
    controlnet_mask_use_imported_image = Column(Boolean, default=False)
    use_prompt_builder = Column(Boolean, default=False)
    active_grid_border_color = Column(String, default="#00FF00")
    active_grid_fill_color = Column(String, default="#FF0000")


class PromptGeneratorSetting(Base):
    __tablename__ = 'prompt_generator_settings'

    id = Column(Integer, primary_key=True)
    settings_id = Column(Integer, ForeignKey('settings.id'))
    name = Column(String, default="")
    advanced_mode = Column(Boolean, default=False)
    category = Column(String, default="")
    prompt_blend_type = Column(Integer, default=0)
    prompt = Column(String, default="")
    weighted_values = Column(JSON, default={})
    prompt_genre = Column(String, default="")
    prompt_color = Column(String, default="")
    prompt_style = Column(String, default="")
    prefix = Column(String, default="")
    suffix = Column(String, default="")
    negative_prefix = Column(String, default="")
    negative_suffix = Column(String, default="")
    active = Column(Boolean, default=False)


class GridSettings(Base):
    __tablename__ = 'grid_settings'

    id = Column(Integer, primary_key=True)
    show_grid = Column(Boolean, default=True)
    snap_to_grid = Column(Boolean, default=True)
    size = Column(Integer, default=64)
    line_width = Column(Integer, default=1)
    canvas_color = Column(String, default="#000000")
    line_color = Column(String, default="#121212")
    settings = relationship("Settings", back_populates="grid_settings")


class DeterministicSettings(Base):
    __tablename__ = 'deterministic_settings'

    id = Column(Integer, primary_key=True)
    batch_size = Column(Integer, default=1)
    style = Column(String, default="")
    seed = Column(Integer, default=42)
    settings = relationship("Settings", back_populates="deterministic_settings")


class MetadataSettings(Base):
    __tablename__ = 'metadata_settings'

    id = Column(Integer, primary_key=True)
    image_export_metadata_prompt = Column(Boolean, default=False)
    image_export_metadata_negative_prompt = Column(Boolean, default=False)
    image_export_metadata_scale = Column(Boolean, default=False)
    image_export_metadata_seed = Column(Boolean, default=False)
    image_export_metadata_steps = Column(Boolean, default=False)
    image_export_metadata_ddim_eta = Column(Boolean, default=False)
    image_export_metadata_iterations = Column(Boolean, default=False)
    image_export_metadata_samples = Column(Boolean, default=False)
    image_export_metadata_model = Column(Boolean, default=False)
    image_export_metadata_model_branch = Column(Boolean, default=False)
    image_export_metadata_scheduler = Column(Boolean, default=False)
    export_metadata = Column(Boolean, default=False)
    import_metadata = Column(Boolean, default=False)
    settings = relationship("Settings", back_populates="metadata_settings")


class MemorySettings(Base):
    __tablename__ = "memory_settings"

    id = Column(Integer, primary_key=True)
    use_last_channels = Column(Boolean, default=True)
    use_attention_slicing = Column(Boolean, default=False)
    use_tf32 = Column(Boolean, default=False)
    use_enable_vae_slicing = Column(Boolean, default=True)
    use_accelerated_transformers = Column(Boolean, default=True)
    use_tiled_vae = Column(Boolean, default=True)
    enable_model_cpu_offload = Column(Boolean, default=False)
    use_enable_sequential_cpu_offload = Column(Boolean, default=False)
    use_cudnn_benchmark = Column(Boolean, default=True)
    use_torch_compile = Column(Boolean, default=False)
    settings = relationship("Settings", back_populates="memory_settings")


MODELS_PATH = os.path.join(BASE_PATH, "models")
DEFAULT_PATHS = {
    "base": BASE_PATH,
    "models": {
        "txt2img": "",
        "depth2img": "",
        "pix2pix": "",
        "inpaint": "",
        "upscale": "",
        "txt2vid": "",
        "embeddings": "",
        "lora": "",
    },
    "other": {
        "images": "",
        "gifs": "",
        "videos": "",
    },
}
for k,v in DEFAULT_PATHS["models"].items():
    DEFAULT_PATHS["models"][k] = os.path.join(MODELS_PATH, k)
for k,v in DEFAULT_PATHS["other"].items():
    DEFAULT_PATHS["other"][k] = os.path.join(BASE_PATH, k)

class PathSettings(Base):
    __tablename__ = 'path_settings'

    id = Column(Integer, primary_key=True)
    hf_cache_path = Column(String, default="")
    base_path = Column(String, default=DEFAULT_PATHS["base"])
    txt2img_model_path = Column(String, default=DEFAULT_PATHS["models"]["txt2img"])
    depth2img_model_path = Column(String, default=DEFAULT_PATHS["models"]["depth2img"])
    pix2pix_model_path = Column(String, default=DEFAULT_PATHS["models"]["pix2pix"])
    inpaint_model_path = Column(String, default=DEFAULT_PATHS["models"]["inpaint"])
    upscale_model_path = Column(String, default=DEFAULT_PATHS["models"]["upscale"])
    txt2vid_model_path = Column(String, default=DEFAULT_PATHS["models"]["txt2vid"])
    embeddings_model_path = Column(String, default=os.path.join(MODELS_PATH, "embeddings"))
    lora_model_path = Column(String, default=os.path.join(MODELS_PATH, "lora"))
    image_path = Column(String, default=os.path.join(BASE_PATH, "images"))
    gif_path = Column(String, default=os.path.join(BASE_PATH, "gifs"))
    video_path = Column(String, default=os.path.join(BASE_PATH, "videos"))
    settings = relationship("Settings", back_populates="path_settings")

    @property
    def embeddings_path(self):
        return self.embeddings_model_path

    @embeddings_path.setter
    def embeddings_path(self, value):
        self.embeddings_model_path = value

    @property
    def lora_path(self):
        return self.lora_model_path

    @lora_path.setter
    def lora_path(self, value):
        self.lora_model_path = value

    @property
    def model_base_path(self):
        return self.txt2img_model_path

    @model_base_path.setter
    def model_base_path(self, value):
        self.base_path = value

    @property
    def outpaint_model_path(self):
        return self.inpaint_model_path

    @outpaint_model_path.setter
    def outpaint_model_path(self, value):
        self.inpaint_model_path = value


    def reset_paths(self):
        self.hf_cache_path = ""
        self.base_path = DEFAULT_PATHS["base"]
        self.txt2img_model_path = DEFAULT_PATHS["models"]["txt2img"]
        self.depth2img_model_path = DEFAULT_PATHS["models"]["depth2img"]
        self.pix2pix_model_path = DEFAULT_PATHS["models"]["pix2pix"]
        self.inpaint_model_path = DEFAULT_PATHS["models"]["inpaint"]
        self.upscale_model_path = DEFAULT_PATHS["models"]["upscale"]
        self.txt2vid_model_path = DEFAULT_PATHS["models"]["txt2vid"]
        self.embeddings_model_path = DEFAULT_PATHS["models"]["embeddings"]
        self.lora_model_path = DEFAULT_PATHS["models"]["lora"]
        self.image_path = DEFAULT_PATHS["other"]["image"]
        self.gif_path = DEFAULT_PATHS["other"]["gif"]
        self.video_path = DEFAULT_PATHS["other"]["video"]
        from airunner.utils import save_session
        save_session()


class BrushSettings(Base):
    __tablename__ = 'brush_settings'

    id = Column(Integer, primary_key=True)
    size = Column(Integer, default=10)
    primary_color = Column(String, default="#FF0000")
    secondary_color = Column(String, default="#000000")
    settings = relationship("Settings", back_populates="brush_settings")


class ImageFilter(Base):
    __tablename__ = 'image_filter'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    display_name = Column(String)
    image_filter_values = relationship("ImageFilterValue", back_populates="image_filter", lazy='joined')
    auto_apply = Column(Boolean, default=False)
    filter_class = Column(String, default="")


class ImageFilterValue(Base):
    __tablename__ = 'image_filter_value'

    id = Column(Integer, primary_key=True)
    image_filter_id = Column(Integer, ForeignKey('image_filter.id'))
    image_filter = relationship("ImageFilter", back_populates="image_filter_values")
    name = Column(String)
    value = Column(String)
    value_type = Column(String, default="int")
    min_value = Column(Integer, default=0)
    max_value = Column(Integer, default=100)


class ActiveGridSettings(Base):
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
    settings = relationship("Settings", back_populates="active_grid_settings")


class Settings(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    nsfw_filter = Column(Boolean, default=True)
    allow_hf_downloads = Column(Boolean, default=True)
    dark_mode_enabled = Column(Boolean, default=False)
    resize_on_paste = Column(Boolean, default=False)
    allow_online_mode = Column(Boolean, default=True)

    current_tool = Column(String, default="")

    image_to_new_layer = Column(Boolean, default=False)
    latest_version_check = Column(Boolean, default=True)
    primary_color = Column(String, default="#000000")
    secondary_color = Column(String, default="#000000")

    working_width = Column(Integer, default=512)
    working_height = Column(Integer, default=512)
    hf_api_key_read_key = Column(String, default="")
    hf_api_key_write_key = Column(String, default="")
    hf_username = Column(String, default="")

    mode = Column(String, default="art")

    brush_settings_id = Column(Integer, ForeignKey('brush_settings.id'))
    brush_settings = relationship("BrushSettings", back_populates="settings")

    path_settings_id = Column(Integer, ForeignKey('path_settings.id'))
    path_settings = relationship("PathSettings", back_populates="settings")

    grid_settings_id = Column(Integer, ForeignKey('grid_settings.id'))
    grid_settings = relationship("GridSettings", back_populates="settings")

    metadata_settings_id = Column(Integer, ForeignKey('metadata_settings.id'))
    metadata_settings = relationship("MetadataSettings", back_populates="settings")

    memory_settings_id = Column(Integer, ForeignKey('memory_settings.id'))
    memory_settings = relationship("MemorySettings", back_populates="settings")

    deterministic_settings_id = Column(Integer, ForeignKey('deterministic_settings.id'))
    deterministic_settings = relationship("DeterministicSettings", back_populates="settings", uselist=False)

    active_grid_settings_id = Column(Integer, ForeignKey('active_grid_settings.id'))
    active_grid_settings = relationship("ActiveGridSettings", back_populates="settings", uselist=False)

    force_reset = Column(Boolean, default=False)
    auto_export_images = Column(Boolean, default=False)
    image_export_type = Column(String, default="png")

    show_active_image_area = Column(Boolean, default=True)
    use_interpolation = Column(Boolean, default=False)
    is_maximized = Column(Boolean, default=False)
    splitter_sizes = relationship("SplitterSection", backref="settings")
    prompt_generator_settings = relationship("PromptGeneratorSetting", backref="settings")

    # generator tab sections
    current_tab = Column(String, default="stablediffusion")
    current_section_stablediffusion = Column(String, default="txt2img")
    current_section_kandinsky = Column(String, default="txt2img")
    current_section_shapegif = Column(String, default="txt2img")
    generator_settings = relationship("GeneratorSetting", backref="settings")

    # tool and bottom panel tab sections
    current_tool_tab = Column(String, default="brush")
    current_bottom_panel_tab = Column(String, default="model_manager")


class LayerImage(Base):
    __tablename__ = "layer_images"

    @property
    def image(self):
        # convert base64 image to pil image
        if self.base_64_image:
            decoded_image = base64.b64decode(self.base_64_image)
            bytes_image = io.BytesIO(decoded_image)
            # convert bytes to PIL iamge:
            image = Image.open(bytes_image)
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

    id = Column(Integer, primary_key=True)
    layer_id = Column(Integer, ForeignKey('layers.id'))
    layer = relationship("Layer", backref="image_data")
    base_64_image = Column(String, default="")
    pos_x = Column(Integer, default=0)
    pos_y = Column(Integer, default=0)
    pivot_point_x = Column(Integer, default=0)
    pivot_point_y = Column(Integer, default=0)
    root_point_x = Column(Integer, default=0)
    root_point_y = Column(Integer, default=0)
    order = Column(Integer, default=0)
    opacity = Column(Float, default=100)
    visible = Column(Boolean, default=True)


class Layer(Base):
    __tablename__ = 'layers'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))
    document = relationship("Document", backref="layers")
    name = Column(String)
    visible = Column(Boolean, default=True)
    opacity = Column(Float, default=100)
    position = Column(Integer, default=0)


class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    settings_id = Column(Integer, ForeignKey('settings.id'))
    settings = relationship("Settings", backref="document")
    active = Column(Boolean, default=False)


class TabSection(Base):
    __tablename__ = 'active_tab'

    id = Column(Integer, primary_key=True)
    panel = Column(String)
    active_tab = Column(String)


class PromptBuilder(Base):
    __tablename__ = 'prompt_builder'

    id = Column(Integer, primary_key=True)
    # document_id = Column(Integer, ForeignKey('documents.id'))
    # document = relationship("Document", backref="prompt_builder")
    name = Column(String, default="")
    active = Column(Boolean, default=False)
    auto_prompt_weight = Column(Float, default=0.5)
    text_prompt_weight = Column(Float, default=0.5)
    negative_auto_prompt_weight = Column(Float, default=0.5)
    negative_text_prompt_weight = Column(Float, default=0.5)


class CanvasSettings(Base):
    __tablename__ = "canvas_settings"

    id = Column(Integer, primary_key=True)
    pos_x = Column(Integer, default=0)
    pos_y = Column(Integer, default=0)


class LLMGenerator(Base):
    __tablename__ = 'llm_generator'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String)
    username = Column(String)
    botname = Column(String)
    model_versions = relationship('LLMModelVersion', back_populates='generator')
    generator_settings = relationship('LLMGeneratorSetting', back_populates='generator')
    prefix = Column(String, default="")
    suffix = Column(String, default="")
    message_type = Column(String, default="chat")
    bot_personality = Column(String, default="Nice")


class LLMGeneratorSetting(Base):
    __tablename__ = 'llm_generator_setting'
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
    early_stopping = Column(Boolean, default=False)
    random_seed = Column(Boolean, default=False)
    model_version = Column(String, default="google/flan-t5-xl")
    generator_id = Column(Integer, ForeignKey('llm_generator.id'))
    generator = relationship('LLMGenerator', back_populates='generator_settings')
    dtype = Column(String, default="4bit")


class LLMModelVersion(Base):
    __tablename__ = 'llm_model_version'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String)
    generator_id = Column(Integer, ForeignKey('llm_generator.id'))
    generator = relationship('LLMGenerator', back_populates='model_versions')


class Conversation(Base):
    __tablename__ = 'conversation'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship('Message', back_populates='conversation')

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String)
    message = Column(String)
    conversation_id = Column(Integer, ForeignKey('conversation.id'))
    conversation = relationship('Conversation', back_populates='messages')