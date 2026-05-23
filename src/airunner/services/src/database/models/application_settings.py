"""Service-owned application settings model."""

from sqlalchemy import Column, Integer, String, Boolean

from airunner_services.database.base import BaseModel
from airunner_services.contract_enums import (
    DEFAULT_IMAGE_GENERATOR,
    AvailableLanguage,
    Mode,
)


class ApplicationSettings(BaseModel):
    """Persisted global AIRunner application settings."""

    __tablename__ = "application_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    use_cuda = Column(Boolean, default=True)
    sd_enabled = Column(Boolean, default=False)
    llm_enabled = Column(Boolean, default=False)
    tts_enabled = Column(Boolean, default=False)
    stt_enabled = Column(Boolean, default=False)
    controlnet_enabled = Column(Boolean, default=False)
    nsfw_filter = Column(Boolean, default=True)
    ai_mode = Column(Boolean, default=True)
    installation_path = Column(String, default="~/.local/share/airunner")
    trust_remote_code = Column(Boolean, default=False)
    app_version = Column(String, default="")
    image_export_type = Column(String, default="png")
    auto_export_images = Column(Boolean, default=True)
    working_width = Column(Integer, default=1024)
    working_height = Column(Integer, default=1024)
    current_llm_generator = Column(String, default="causallm")
    current_image_generator = Column(
        String,
        default=DEFAULT_IMAGE_GENERATOR.value,
    )
    hf_api_key_read_key = Column(String, default="")
    hf_api_key_write_key = Column(String, default="")
    civit_ai_api_key = Column(String, default="")
    mode = Column(String, default=Mode.IMAGE.value)
    autoload_sd = Column(Boolean, default=True)
    autoload_llm = Column(Boolean, default=False)
    detected_language = Column(String, default=AvailableLanguage.EN.value)
    use_detected_language = Column(Boolean, default=True)
    run_in_background = Column(Boolean, default=False)
    start_at_login = Column(Boolean, default=False)
    http_server_enabled = Column(Boolean, default=True)
    http_server_host = Column(String, default="127.0.0.1")
    http_server_port = Column(Integer, default=5005)
    lna_enabled = Column(Boolean, default=False)
    knowledge_migrated = Column(Boolean, default=False)


__all__ = ["ApplicationSettings"]