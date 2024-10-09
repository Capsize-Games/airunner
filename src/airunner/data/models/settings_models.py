import os

from sqlalchemy import create_engine, Column, Integer, String, JSON, Boolean, Float, Text, ForeignKey, LargeBinary, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from airunner.enums import ImageGenerator, GeneratorSection, CanvasToolName, Mode
from airunner.settings import SD_DEFAULT_VAE_PATH, DEFAULT_SCHEDULER, \
    DEFAULT_BRUSH_PRIMARY_COLOR, DEFAULT_BRUSH_SECONDARY_COLOR, BASE_PATH


import datetime

Base = declarative_base()


class ApplicationSettings(Base):
    __tablename__ = 'application_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    use_cuda = Column(Boolean, default=True)
    sd_enabled = Column(Boolean, default=False)
    llm_enabled = Column(Boolean, default=False)
    tts_enabled = Column(Boolean, default=False)
    stt_enabled = Column(Boolean, default=False)
    controlnet_enabled = Column(Boolean, default=False)
    ai_mode = Column(Boolean, default=True)
    active_grid_size_lock = Column(Boolean, default=False)
    installation_path = Column(String, default="~/.local/share/airunner")
    current_layer_index = Column(Integer, default=0)
    paths_initialized = Column(Boolean, default=False)
    trust_remote_code = Column(Boolean, default=False)  # Leave this hardcoded. We will never trust remote code.
    nsfw_filter = Column(Boolean, default=True)
    resize_on_paste = Column(Boolean, default=True)
    image_to_new_layer = Column(Boolean, default=True)
    dark_mode_enabled = Column(Boolean, default=True)
    override_system_theme = Column(Boolean, default=True)
    latest_version_check = Column(Boolean, default=True)
    app_version = Column(String, default="")
    allow_online_mode = Column(Boolean, default=True)
    current_tool = Column(String, default=CanvasToolName.BRUSH.value)
    image_export_type = Column(String, default="png")
    auto_export_images = Column(Boolean, default=True)
    show_active_image_area = Column(Boolean, default=True)
    working_width = Column(Integer, default=512)
    working_height = Column(Integer, default=512)
    current_llm_generator = Column(String, default="causallm")
    current_image_generator = Column(String, default=ImageGenerator.STABLEDIFFUSION.value)
    generator_section = Column(String, default=GeneratorSection.TXT2IMG.value)
    hf_api_key_read_key = Column(String, default="")
    hf_api_key_write_key = Column(String, default="")
    civit_ai_api_key = Column(String, default="")
    is_maximized = Column(Boolean, default=False)
    pivot_point_x = Column(Integer, default=0)
    pivot_point_y = Column(Integer, default=0)
    mode = Column(String, default=Mode.IMAGE.value)
    autoload_sd = Column(Boolean, default=True)
    autoload_llm = Column(Boolean, default=False)
    show_nsfw_warning = Column(Boolean, default=True)
    run_setup_wizard = Column(Boolean, default=True)
    download_wizard_completed = Column(Boolean, default=False)
    stable_diffusion_agreement_checked = Column(Boolean, default=True)
    airunner_agreement_checked = Column(Boolean, default=True)
    user_agreement_checked = Column(Boolean, default=True)
    llama_license_agreement_checked = Column(Boolean, default=True)


class ActiveGridSettings(Base):
    __tablename__ = 'active_grid_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, default=True)
    render_border = Column(Boolean, default=True)
    render_fill = Column(Boolean, default=False)
    border_opacity = Column(Integer, default=50)
    fill_opacity = Column(Integer, default=50)
    border_color = Column(String, default="#00FF00")
    fill_color = Column(String, default="#FF0000")
    pos_x = Column(Integer, default=0)
    pos_y = Column(Integer, default=0)
    width = Column(Integer, default=512)
    height = Column(Integer, default=512)


class ControlnetSettings(Base):
    __tablename__ = 'controlnet_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    image = Column(String, nullable=True)
    generated_image = Column(String, nullable=True)
    enabled = Column(Boolean, default=False)
    use_grid_image_as_input = Column(Boolean, default=False)
    strength = Column(Integer, default=50)
    conditioning_scale = Column(Integer, default=100)
    guidance_scale = Column(Integer, default=750)
    controlnet = Column(String, default="Canny")
    lock_input_image = Column(Boolean, default=False)


class ImageToImageSettings(Base):
    __tablename__ = 'image_to_image_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    image = Column(String, nullable=True)
    enabled = Column(Boolean, default=False)
    use_grid_image_as_input = Column(Boolean, default=False)
    lock_input_image = Column(Boolean, default=False)


class OutpaintSettings(Base):
    __tablename__ = 'outpaint_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    image = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    strength = Column(Integer, default=50)
    mask_blur = Column(Integer, default=0)


class DrawingPadSettings(Base):
    __tablename__ = 'drawing_pad_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    image = Column(String, nullable=True)
    mask = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    enable_automatic_drawing = Column(Boolean, default=False)
    mask_layer_enabled = Column(Boolean, default=False)
    x_pos = Column(Integer, default=0)
    y_pos = Column(Integer, default=0)


class MetadataSettings(Base):
    __tablename__ = 'metadata_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_export_metadata_prompt = Column(Boolean, default=True)
    image_export_metadata_negative_prompt = Column(Boolean, default=True)
    image_export_metadata_scale = Column(Boolean, default=True)
    image_export_metadata_seed = Column(Boolean, default=True)
    image_export_metadata_steps = Column(Boolean, default=True)
    image_export_metadata_ddim_eta = Column(Boolean, default=True)
    image_export_metadata_iterations = Column(Boolean, default=True)
    image_export_metadata_samples = Column(Boolean, default=True)
    image_export_metadata_model = Column(Boolean, default=True)
    image_export_metadata_model_branch = Column(Boolean, default=True)
    image_export_metadata_scheduler = Column(Boolean, default=True)
    image_export_metadata_strength = Column(Boolean, default=True)
    image_export_metadata_clip_skip = Column(Boolean, default=True)
    image_export_metadata_version = Column(Boolean, default=True)
    image_export_metadata_lora = Column(Boolean, default=True)
    image_export_metadata_embeddings = Column(Boolean, default=True)
    image_export_metadata_timestamp = Column(Boolean, default=True)
    image_export_metadata_controlnet = Column(Boolean, default=True)
    export_metadata = Column(Boolean, default=True)
    import_metadata = Column(Boolean, default=True)


class GeneratorSettings(Base):
    __tablename__ = 'generator_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_action = Column(String, default="txt2img")
    generator_name = Column(String, default="stablediffusion")
    quality_effects = Column(String, default="")
    image_preset = Column(String, default="")
    prompt = Column(String, default="")
    negative_prompt = Column(String, default="")
    second_prompt = Column(String, default="")
    second_negative_prompt = Column(String, default="")
    random_seed = Column(Boolean, default=True)
    model_name = Column(String, default="")
    model = Column(Integer, ForeignKey('aimodels.id'), nullable=True)
    aimodel = relationship("AIModels", back_populates="generator_settings")
    vae = Column(String, default=SD_DEFAULT_VAE_PATH)
    scheduler = Column(String, default=DEFAULT_SCHEDULER)
    variation = Column(Boolean, default=False)
    use_prompt_builder = Column(Boolean, default=False)
    version = Column(String, default="SD 1.5")
    is_preset = Column(Boolean, default=False)
    use_compel = Column(Boolean, default=True)

    steps = Column(Integer, default=20)
    ddim_eta = Column(Float, default=0.5)
    scale = Column(Integer, default=750)
    seed = Column(Integer, default=42)
    prompt_triggers = Column(String, default="")
    strength = Column(Integer, default=50)
    n_samples = Column(Integer, default=1)
    clip_skip = Column(Integer, default=0)
    crops_coord_top_left = Column(JSON, default={"x": 0, "y": 0})
    original_size = Column(JSON, default={"width": 512, "height": 512})
    target_size = Column(JSON, default={"width": 1024, "height": 1024})
    negative_original_size = Column(JSON, default={"width": 512, "height": 512})
    negative_target_size = Column(JSON, default={"width": 512, "height": 512})

    lora_scale = Column(Integer, default=100)


class LLMGeneratorSettings(Base):
    __tablename__ = 'llm_generator_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String, default="CHAT")
    use_tool_filter = Column(Boolean, default=False)
    seed = Column(Integer, default=0)
    random_seed = Column(Boolean, default=False)
    model_version = Column(String, default="w4ffl35/Mistral-7B-Instruct-v0.3-4bit")
    dtype = Column(String, default="4bit")
    use_gpu = Column(Boolean, default=True)
    message_type = Column(String, default="chat")
    override_parameters = Column(Boolean, default=True)
    current_chatbot = Column(Integer, default=0)
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


class TTSSettings(Base):
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


class SpeechT5Settings(Base):
    __tablename__ = 'speech_t5_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    datasets_path = Column(String, default="Matthijs/cmu-arctic-xvectors")
    processor_path = Column(String, default="microsoft/speecht5_tts")
    vocoder_path = Column(String, default="microsoft/speecht5_hifigan")
    model_path = Column(String, default="microsoft/speecht5_tts")
    rate = Column(Integer, default=100)
    pitch = Column(Integer, default=100)
    volume = Column(Integer, default=100)


class EspeakSettings(Base):
    __tablename__ = 'espeak_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    gender = Column(String, default="Male")
    voice = Column(String, default="male1")
    language = Column(String, default="en-US")
    rate = Column(Integer, default=100)
    pitch = Column(Integer, default=100)
    volume = Column(Integer, default=100)
    punctuation_mode = Column(String, default="none")


class STTSettings(Base):
    __tablename__ = 'stt_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    duration = Column(Integer, default=10)
    fs = Column(Integer, default=16000)
    channels = Column(Integer, default=1)
    volume_input_threshold = Column(Integer, default=0.08)
    silence_buffer_seconds = Column(Integer, default=1.0)
    chunk_duration = Column(Integer, default=0.03)


class Schedulers(Base):
    __tablename__ = 'schedulers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    display_name = Column(String, nullable=True)


class BrushSettings(Base):
    __tablename__ = 'brush_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    size = Column(Integer, default=75)
    primary_color = Column(String, default=DEFAULT_BRUSH_PRIMARY_COLOR)
    secondary_color = Column(String, default=DEFAULT_BRUSH_SECONDARY_COLOR)
    strength_slider = Column(Integer, default=950)
    strength = Column(Integer, default=950)
    conditioning_scale = Column(Integer, default=550)
    guidance_scale = Column(Integer, default=75)


class GridSettings(Base):
    __tablename__ = 'grid_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cell_size = Column(Integer, default=64)
    line_width = Column(Integer, default=1)
    line_color = Column(String, default="#101010")
    snap_to_grid = Column(Boolean, default=True)
    canvas_color = Column(String, default="#000000")
    show_grid = Column(Boolean, default=True)
    zoom_level = Column(Float, default=1.0)
    zoom_in_step = Column(Float, default=0.1)
    zoom_out_step = Column(Float, default=0.1)


class PathSettings(Base):
    __tablename__ = 'path_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    base_path = Column(String, default=BASE_PATH)
    documents_path = Column(String, default=os.path.expanduser(os.path.join(BASE_PATH, "text/other", "documents")))
    ebook_path = Column(String, default=os.path.expanduser(os.path.join(BASE_PATH, "text/other", "ebooks")))
    image_path = Column(String, default=os.path.expanduser(os.path.join(BASE_PATH, "art/other", "images")))
    llama_index_path = Column(String, default=os.path.expanduser(os.path.join(BASE_PATH, "text/rag", "db")))
    webpages_path = Column(String, default=os.path.expanduser(os.path.join(BASE_PATH, "text/other", "webpages")))
    stt_model_path = Column(String, default=os.path.expanduser(os.path.join(BASE_PATH, "text/models/stt", "models")))
    tts_model_path = Column(String, default=os.path.expanduser(os.path.join(BASE_PATH, "text/models/tts", "models")))


class MemorySettings(Base):
    __tablename__ = 'memory_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
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
    use_tome_sd = Column(Boolean, default=True)
    tome_sd_ratio = Column(Integer, default=600)
    move_unused_model_to_cpu = Column(Boolean, default=False)
    unload_unused_models = Column(Boolean, default=True)
    default_gpu_sd = Column(Integer, default=0)
    default_gpu_llm = Column(Integer, default=0)
    default_gpu_tts = Column(Integer, default=0)
    default_gpu_stt = Column(Integer, default=0)


class Chatbot(Base):
    __tablename__ = 'chatbots'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="Chatbot")
    username = Column(String, default="User")
    botname = Column(String, default="Computer")
    use_personality = Column(Boolean, default=True)
    use_mood = Column(Boolean, default=True)
    use_guardrails = Column(Boolean, default=True)
    use_system_instructions = Column(Boolean, default=True)
    use_datetime = Column(Boolean, default=True)
    assign_names = Column(Boolean, default=True)
    bot_personality = Column(Text, default="happy. He loves {{ username }}")
    bot_mood = Column(Text, default="")
    prompt_template = Column(Text, default="Mistral 7B Instruct: Default Chatbot")
    use_tool_filter = Column(Boolean, default=False)
    use_gpu = Column(Boolean, default=True)
    skip_special_tokens = Column(Boolean, default=True)
    sequences = Column(Integer, default=1)
    seed = Column(Integer, default=42)
    random_seed = Column(Boolean, default=True)
    model_version = Column(String, default="w4ffl35/Mistral-7B-Instruct-v0.3-4bit")
    model_type = Column(String, default="llm")
    dtype = Column(String, default="4bit")
    return_result = Column(Boolean, default=True)
    guardrails_prompt = Column(Text, default=(
        "Always assist with care, respect, and truth. "
        "Respond with utmost utility yet securely. "
        "Avoid harmful, unethical, prejudiced, or negative content. "
        "Ensure replies promote fairness and positivity."
    ))
    system_instructions = Column(Text, default=(
        "You are a dialogue generator. "
        "You will follow all of the rules in order to generate compelling and intriguing dialogue for a given character.\n"
        "The Rules:\n"
        "You will ONLY return dialogue, nothing more.\n"
        "Limit responses to a single sentence.\n"
        "Only generate responses in pure dialogue form without including any actions, descriptions or stage directions in parentheses. Only return spoken words.\n"
        "Do not generate redundant dialogue. Examine the conversation and context close and keep responses interesting and creative.\n"
        "Do not format the response with the character's name or any other text. Only return the dialogue.\n"
        "Respond with dialogue that is appropriate for a character named {{ speaker_name }}.\n"
        "{{ speaker_name }} and {{ listener_name }} are having a conversation. \n"
        "Avoid repeating {{ speaker_name }}'s previous dialogue or {{ listener_name }}'s previous dialogue.\n"
        "You will generate responses which are appropriate for your personality and given character.\n"
        "------\n"
    ))
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
    seed = Column(Integer, default=0)
    random_seed = Column(Boolean, default=False)

    target_files = relationship("TargetFiles", back_populates="chatbot")
    target_directories = relationship("TargetDirectories", back_populates="chatbot")
    messages = relationship("Message", back_populates="chatbot")


class TargetFiles(Base):
    __tablename__ = 'target_files'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(Integer, ForeignKey('chatbots.id'))
    file_path = Column(String)

    chatbot = relationship("Chatbot", back_populates="target_files")


class TargetDirectories(Base):
    __tablename__ = 'target_directories'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chatbot_id = Column(Integer, ForeignKey('chatbots.id'))
    directory_path = Column(String)

    chatbot = relationship("Chatbot", back_populates="target_directories")


class AIModels(Base):
    __tablename__ = 'aimodels'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    version = Column(String, nullable=False)
    category = Column(String, nullable=False)
    pipeline_action = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False)
    model_type = Column(String, nullable=False)
    is_default = Column(Boolean, nullable=False)
    generator_settings = relationship("GeneratorSettings", back_populates="aimodel")


class ShortcutKeys(Base):
    __tablename__ = 'shortcut_keys'
    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(String, nullable=False)
    text = Column(String, nullable=False)
    key = Column(Integer, nullable=False)
    modifiers = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    signal = Column(Integer, nullable=False)


class Lora(Base):
    __tablename__ = 'lora'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    scale = Column(Integer, nullable=False)
    enabled = Column(Boolean, nullable=False)
    loaded = Column(Boolean, default=False, nullable=False)
    trigger_word = Column(String, nullable=True)
    path = Column(String, nullable=True)
    version = Column(String, nullable=True)


class SavedPrompt(Base):
    __tablename__ = "saved_prompts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(String, nullable=True)
    secondary_prompt = Column(String, nullable=True)
    negative_prompt = Column(String, nullable=True)
    secondary_negative_prompt = Column(String, nullable=True)


class Embedding(Base):
    __tablename__ = "embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    version = Column(String, nullable=False)
    tags = Column(String, default="")
    active = Column(Boolean, default=False)
    trigger_word = Column(String, default="")


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String, nullable=False)
    use_guardrails = Column(Boolean, default=True)
    guardrails = Column(Text, default="")
    system = Column(Text, default="")
    use_system_datetime_in_system_prompt = Column(Boolean, default=False)


class ControlnetModel(Base):
    __tablename__ = "controlnet_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    version = Column(String, nullable=False)


class FontSetting(Base):
    __tablename__ = "font_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    font_family = Column(String, nullable=False)
    font_size = Column(Integer, nullable=False)


class PipelineModel(Base):
    __tablename__ = "pipeline_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_action = Column(String, nullable=False)
    version = Column(String, nullable=False)
    category = Column(String, nullable=False)
    classname = Column(String, nullable=False)
    default = Column(Boolean, nullable=False)


class WindowSettings(Base):
    __tablename__ = "window_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    is_maximized = Column(Boolean, default=False)
    is_fullscreen = Column(Boolean, default=False)
    llm_splitter = Column(LargeBinary, nullable=True)
    content_splitter = Column(LargeBinary, nullable=True)
    generator_form_splitter = Column(LargeBinary, nullable=True)
    grid_settings_splitter = Column(LargeBinary, nullable=True)
    tool_tab_widget_index = Column(Integer, default=0)
    width = Column(Integer, default=800)
    height = Column(Integer, default=600)
    x_pos = Column(Integer, default=0)
    y_pos = Column(Integer, default=0)
    mode_tab_widget_index = Column(Integer, default=0)


class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    title = Column(String, nullable=True)  # New column added
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    conversation = relationship("Conversation", back_populates="messages")
    name = Column(String, nullable=True)  # New column added
    is_bot = Column(Boolean, default=False)  # New column added
    chatbot_id = Column(Integer, ForeignKey('chatbots.id'))

    chatbot = relationship("Chatbot", back_populates="messages")


class Summary(Base):
    __tablename__ = 'summaries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    conversation = relationship("Conversation", back_populates="summaries")


Conversation.messages = relationship("Message", order_by=Message.id, back_populates="conversation")
Conversation.summaries = relationship("Summary", order_by=Summary.id, back_populates="conversation")
Message.chatbot = relationship("Chatbot", back_populates="messages")


class ImageFilter(Base):
    __tablename__ = 'image_filter_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    auto_apply = Column(Boolean, default=False)
    filter_class = Column(String, nullable=False)


class ImageFilterValue(Base):
    __tablename__ = 'image_filter_values'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    value_type = Column(String, nullable=False)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    image_filter_id = Column(Integer, ForeignKey('image_filter_settings.id'))
    image_filter = relationship("ImageFilter", back_populates="image_filter_values")

ImageFilter.image_filter_values = relationship("ImageFilterValue", order_by=ImageFilterValue.id, back_populates="image_filter")
ImageFilterValue.image_filter = relationship("ImageFilter", back_populates="image_filter_values")
