"""Canonical application settings model (QSettings-aware)."""

from sqlalchemy import Column, Integer, String, Boolean

from airunner_services.database.base import BaseModel
from airunner_services.contract_enums import (
    DEFAULT_IMAGE_GENERATOR,
    AvailableLanguage,
    GeneratorSection,
    CanvasToolName,
    Mode,
)


def _qsettings_value(
    key: str,
    default,
    group: str = "application_settings",
    value_type=None,
):
    """Read a value from QSettings, falling back to the provided default."""
    try:
        from PySide6.QtCore import QSettings
        from airunner.utils.settings.get_qsettings import get_qsettings

        settings = get_qsettings()
        settings.beginGroup(group)
        val = settings.value(key, default)
        settings.endGroup()
        if value_type is not None and val is not None:
            return value_type(val)
        return val
    except ImportError:
        return default


def _set_qsettings_value(key: str, value, group: str = "application_settings"):
    """Write a value to QSettings when PySide6 is available."""
    try:
        from airunner.utils.settings.get_qsettings import get_qsettings

        settings = get_qsettings()
        settings.beginGroup(group)
        settings.setValue(key, value)
        settings.endGroup()
    except ImportError:
        pass


class ApplicationSettings(BaseModel):
    """Persisted global AIRunner application settings."""

    __tablename__ = "application_settings"

    # --- database columns (post-migration) ---
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
    document_width = Column(Integer, default=1024)
    document_height = Column(Integer, default=1024)
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
    openai_api_key = Column(String, default="")
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
    privacy_service_consent = Column(String, default="{}")
    dark_mode_enabled_db = Column(Boolean, default=True)
    theme_name = Column(String, default="dark")

    # --- image storage & export columns ---
    store_images_in_db = Column(Boolean, default=True)
    store_images_locally = Column(Boolean, default=True)
    image_export_folder = Column(String, default="")
    metadata_export_flags = Column(String, default="{}")

    # ------------------------------------------------------------------
    # QSettings-backed properties (replaces dropped DB columns)
    # ------------------------------------------------------------------

    @property
    def active_grid_size_lock(self):
        return _qsettings_value(
            "active_grid_size_lock", False, value_type=bool
        )

    @active_grid_size_lock.setter
    def active_grid_size_lock(self, value):
        _set_qsettings_value("active_grid_size_lock", bool(value))

    @property
    def current_layer_index(self):
        return _qsettings_value(
            "current_layer_index", 0, value_type=int
        )

    @current_layer_index.setter
    def current_layer_index(self, value):
        _set_qsettings_value("current_layer_index", int(value))

    @property
    def paths_initialized(self):
        return _qsettings_value(
            "paths_initialized", False, value_type=bool
        )

    @paths_initialized.setter
    def paths_initialized(self, value):
        _set_qsettings_value("paths_initialized", bool(value))

    @property
    def resize_on_paste(self):
        return _qsettings_value(
            "resize_on_paste", True, value_type=bool
        )

    @resize_on_paste.setter
    def resize_on_paste(self, value):
        _set_qsettings_value("resize_on_paste", bool(value))

    @property
    def image_to_new_layer(self):
        return _qsettings_value(
            "image_to_new_layer", True, value_type=bool
        )

    @image_to_new_layer.setter
    def image_to_new_layer(self, value):
        _set_qsettings_value("image_to_new_layer", bool(value))

    @property
    def dark_mode_enabled(self):
        return _qsettings_value(
            "dark_mode_enabled", True, value_type=bool
        )

    @dark_mode_enabled.setter
    def dark_mode_enabled(self, value):
        _set_qsettings_value("dark_mode_enabled", bool(value))

    @property
    def override_system_theme(self):
        return _qsettings_value(
            "override_system_theme", True, value_type=bool
        )

    @override_system_theme.setter
    def override_system_theme(self, value):
        _set_qsettings_value("override_system_theme", bool(value))

    @property
    def latest_version_check(self):
        return _qsettings_value(
            "latest_version_check", True, value_type=bool
        )

    @latest_version_check.setter
    def latest_version_check(self, value):
        _set_qsettings_value("latest_version_check", bool(value))

    @property
    def current_tool(self):
        return _qsettings_value(
            "current_tool", CanvasToolName.BRUSH.value
        )

    @current_tool.setter
    def current_tool(self, value):
        _set_qsettings_value("current_tool", value)

    @property
    def show_active_image_area(self):
        return _qsettings_value(
            "show_active_image_area", True, value_type=bool
        )

    @show_active_image_area.setter
    def show_active_image_area(self, value):
        _set_qsettings_value("show_active_image_area", bool(value))

    @property
    def generator_section(self):
        return _qsettings_value(
            "generator_section", GeneratorSection.TXT2IMG.value
        )

    @generator_section.setter
    def generator_section(self, value):
        _set_qsettings_value("generator_section", value)

    @property
    def is_maximized(self):
        return _qsettings_value(
            "is_maximized", False,
            group="window_settings", value_type=bool,
        )

    @is_maximized.setter
    def is_maximized(self, value):
        _set_qsettings_value(
            "is_maximized", bool(value), group="window_settings"
        )

    @property
    def pivot_point_x(self):
        return _qsettings_value("pivot_point_x", 0, value_type=int)

    @pivot_point_x.setter
    def pivot_point_x(self, value):
        _set_qsettings_value("pivot_point_x", int(value))

    @property
    def pivot_point_y(self):
        return _qsettings_value("pivot_point_y", 0, value_type=int)

    @pivot_point_y.setter
    def pivot_point_y(self, value):
        _set_qsettings_value("pivot_point_y", int(value))

    @property
    def run_setup_wizard(self):
        return _qsettings_value(
            "run_setup_wizard", True, value_type=bool
        )

    @run_setup_wizard.setter
    def run_setup_wizard(self, value):
        _set_qsettings_value("run_setup_wizard", bool(value))

    @property
    def download_wizard_completed(self):
        return _qsettings_value(
            "download_wizard_completed", False, value_type=bool
        )

    @download_wizard_completed.setter
    def download_wizard_completed(self, value):
        _set_qsettings_value("download_wizard_completed", bool(value))

    @property
    def stable_diffusion_agreement_checked(self):
        return _qsettings_value(
            "stable_diffusion_agreement_checked", True, value_type=bool
        )

    @stable_diffusion_agreement_checked.setter
    def stable_diffusion_agreement_checked(self, value):
        _set_qsettings_value(
            "stable_diffusion_agreement_checked", bool(value)
        )

    @property
    def airunner_agreement_checked(self):
        return _qsettings_value(
            "airunner_agreement_checked", True, value_type=bool
        )

    @airunner_agreement_checked.setter
    def airunner_agreement_checked(self, value):
        _set_qsettings_value("airunner_agreement_checked", bool(value))

    @property
    def user_agreement_checked(self):
        return _qsettings_value(
            "user_agreement_checked", True, value_type=bool
        )

    @user_agreement_checked.setter
    def user_agreement_checked(self, value):
        _set_qsettings_value("user_agreement_checked", bool(value))

    @property
    def age_agreement_checked(self):
        return _qsettings_value(
            "age_agreement_checked", True, value_type=bool
        )

    @age_agreement_checked.setter
    def age_agreement_checked(self, value):
        _set_qsettings_value("age_agreement_checked", bool(value))

    @property
    def llama_license_agreement_checked(self):
        return _qsettings_value(
            "llama_license_agreement_checked", True, value_type=bool
        )

    @llama_license_agreement_checked.setter
    def llama_license_agreement_checked(self, value):
        _set_qsettings_value(
            "llama_license_agreement_checked", bool(value)
        )


__all__ = ["ApplicationSettings"]