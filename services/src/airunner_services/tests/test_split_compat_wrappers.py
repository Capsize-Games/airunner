"""Compatibility tests for service-owned split modules."""

import re
from pathlib import Path


_FORBIDDEN_IMPORT_PATTERNS = (
    re.compile(r"\b(?:from|import)\s+airunner\.settings\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.enums\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.utils\.application\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.utils\.db\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.utils\.data\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.utils\.job_tracker\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.utils\.memory\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.utils\.path_policy\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.utils\.settings\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.dev_build_token\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.shared_qsettings\b"),
    re.compile(r"\b(?:from|import)\s+airunner_shared\.shared_qsettings\b"),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.application\."
        r"api\.api\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.application\."
        r"workers\.worker\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.application\."
        r"workers\.civit_ai_download_worker\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.application\.gui\."
        r"windows\.llm_huggingface_download_dialog\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.settings\."
        r"data\.path_settings\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\.data\."
        r"bootstrap\.controlnet_bootstrap_data\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\.data\."
        r"bootstrap\.sd_file_bootstrap_data\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\.data\."
        r"bootstrap\.imagefilter_bootstrap_data\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\.data\."
        r"bootstrap\.rmbg_bootstrap_data\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.data\."
        r"bootstrap\.pipeline_bootstrap_data\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.data\."
        r"bootstrap\.unified_model_files\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.llm\.data\."
        r"bootstrap\.prompt_templates_bootstrap_data\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.llm\.data\."
        r"bootstrap\.llm_file_bootstrap_data\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.settings\."
        r"data\.bootstrap\.font_settings_bootstrap_data\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.llm\."
        r"utils\.language\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\."
        r"utils\.model_file_checker\b"
    ),
    re.compile(r"\b(?:from|import)\s+airunner\.components\.agents\b"),
    re.compile(r"\b(?:from|import)\s+airunner\.components\.eval\b"),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.tools\."
        r"(?:base_tool|url_safety|web_content_extractor|search_tool|"
        r"search_providers|scrapy)\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.stt\.executors\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.tts\.managers\."
        r"(?:espeak_model_manager|openvoice_model_manager|"
        r"tts_model_manager)\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.utils\."
        r"(?:application\.(?:get_version|platform_info|random_seed)|"
        r"audio\.sound_device_manager|crypto\.data_encryption|gguf_ops|"
        r"image(?:\.|\b)|location(?:\.|\b)|memory\.is_ampere_or_newer|"
        r"model_dtype_utils\b|model_optimizer\b|model_utils(?:\.|\b)|"
        r"os(?:\.|\b)|text\.(?:formatter|formatter_extended)\b|"
        r"vram_utils\b|zip_utils\b)"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\."
        r"config\.image_generator_capabilities\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\."
        r"managers\.stablediffusion\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\."
        r"managers\.zimage\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\."
        r"pipelines\.z_image\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\."
        r"schedulers\.flow_match_scheduler_factory\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.art\."
        r"utils\.nsfw_checker\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.tts\."
        r"managers\.tts_model_manager\b"
    ),
    re.compile(
        r"\b(?:from|import)\s+airunner\.components\.llm\."
        r"utils\.text_preprocessing\b"
    ),
)


def _find_gui_root_imports() -> list[str]:
    """Return service files that still import shared code from the GUI tree."""
    root = Path(__file__).resolve().parents[1]
    current_file = Path(__file__).resolve()
    matches = []
    for path in root.rglob("*.py"):
        if path == current_file:
            continue
        text = path.read_text(errors="ignore")
        if any(pattern.search(text) for pattern in _FORBIDDEN_IMPORT_PATTERNS):
            matches.append(path.relative_to(root).as_posix())
    return matches


def test_services_do_not_import_gui_root_shared_modules() -> None:
    """Service code should not depend on GUI-root shared infrastructure."""
    assert _find_gui_root_imports() == []


def test_application_utility_wrappers_follow_current_ownership() -> None:
    """Legacy GUI utility imports should reflect current ownership."""
    from airunner.components.application.exceptions import (
        InterruptedException as LegacyInterruptedException,
    )
    from airunner.components.application.exceptions import (
        PipeNotLoadedException as LegacyPipeNotLoadedException,
    )
    from airunner.utils.application.create_worker import (
        create_worker as legacy_create_worker,
    )
    from airunner.utils.application.get_torch_device import (
        get_torch_device as legacy_get_torch_device,
    )
    from airunner.utils.application.get_logger import (
        get_logger as legacy_get_logger,
    )
    from airunner.utils.application.log_hygiene import (
        summarize_text as legacy_summarize_text,
    )
    from airunner.utils.application.logging_utils import (
        configure_headless_logging as legacy_configure_headless_logging,
    )
    from airunner.utils.application.mediator_mixin import (
        MediatorMixin as LegacyMediatorMixin,
    )
    from airunner.utils.application.signal_mediator import (
        SignalMediator as LegacySignalMediator,
    )
    from airunner_services.utils.application.create_worker import create_worker
    from airunner_services.utils.application.get_logger import get_logger
    from airunner_services.utils.application.get_torch_device import (
        get_torch_device,
    )
    from airunner_services.utils.application.log_hygiene import summarize_text
    from airunner_services.utils.application.logging_utils import (
        configure_headless_logging,
    )
    from airunner_services.application_exceptions import (
        InterruptedException,
        PipeNotLoadedException,
    )
    from airunner_services.utils.application.mediator_mixin import (
        MediatorMixin,
    )
    from airunner_services.utils.application.signal_mediator import (
        SignalMediator,
    )

    assert LegacyInterruptedException is not InterruptedException
    assert LegacyInterruptedException.__module__ == (
        "airunner.components.application.exceptions"
    )
    assert LegacyPipeNotLoadedException is not PipeNotLoadedException
    assert LegacyPipeNotLoadedException.__module__ == (
        "airunner.components.application.exceptions"
    )
    assert legacy_configure_headless_logging is not configure_headless_logging
    assert legacy_create_worker is not create_worker
    assert legacy_get_logger is not get_logger
    assert legacy_get_torch_device is not get_torch_device
    assert legacy_summarize_text is not summarize_text
    assert LegacyMediatorMixin is not MediatorMixin
    assert LegacySignalMediator is not SignalMediator


def test_gui_db_wrapper_cluster_removed() -> None:
    """The legacy GUI db wrapper cluster should remain deleted."""
    repo_root = Path(__file__).resolve().parents[4]
    expected_absent = [
        repo_root / "gui" / "src" / "airunner" / "utils" / "db" / "__init__.py",
        repo_root / "gui" / "src" / "airunner" / "utils" / "db" / "bootstrap.py",
        repo_root / "gui" / "src" / "airunner" / "utils" / "db" / "column.py",
        repo_root / "gui" / "src" / "airunner" / "utils" / "db" / "foreign_key.py",
        repo_root / "gui" / "src" / "airunner" / "utils" / "db" / "table.py",
    ]

    for path in expected_absent:
        assert not path.exists(), path.as_posix()


def test_gui_location_map_wrapper_removed() -> None:
    """The dead GUI location-map wrapper should remain deleted."""
    repo_root = Path(__file__).resolve().parents[4]
    wrapper_path = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "location"
        / "map.py"
    )

    assert not wrapper_path.exists(), wrapper_path.as_posix()


def test_data_utility_wrappers_follow_current_ownership() -> None:
    """GUI data helpers should now resolve to GUI-owned code."""
    from airunner.utils.data.model_to_dataclass import (
        model_to_dataclass as legacy_model_to_dataclass,
    )
    from airunner_services.utils.data.model_to_dataclass import (
        model_to_dataclass,
    )

    assert legacy_model_to_dataclass is not model_to_dataclass
    assert legacy_model_to_dataclass.__module__ == (
        "airunner.utils.data.model_to_dataclass"
    )


def test_download_temp_cleanup_wrapper_is_gui_owned() -> None:
    """Legacy GUI cleanup helpers should now resolve to GUI ownership."""
    from airunner_services.download_temp_cleanup import (
        cleanup_stale_download_dir,
    )
    from airunner_services.download_temp_cleanup import (
        cleanup_stale_download_dirs,
    )
    from airunner.utils.download_temp_cleanup import (
        cleanup_stale_download_dir as legacy_cleanup_stale_download_dir,
    )
    from airunner.utils.download_temp_cleanup import (
        cleanup_stale_download_dirs as legacy_cleanup_stale_download_dirs,
    )

    assert legacy_cleanup_stale_download_dir is not cleanup_stale_download_dir
    assert legacy_cleanup_stale_download_dir.__module__ == (
        "airunner.utils.download_temp_cleanup"
    )
    assert legacy_cleanup_stale_download_dirs is not cleanup_stale_download_dirs
    assert legacy_cleanup_stale_download_dirs.__module__ == (
        "airunner.utils.download_temp_cleanup"
    )


def test_runtime_utility_wrappers_follow_current_ownership() -> None:
    """Legacy GUI runtime helpers should follow current ownership."""
    from airunner.components.llm.utils.language import (
        detect_language as legacy_detect_language,
    )
    from airunner.components.llm.utils.ministral3_config_patcher import (
        needs_patching as legacy_needs_patching,
    )
    from airunner.components.llm.utils.ministral3_config_patcher import (
        patch_ministral3_config as legacy_patch_ministral3_config,
    )
    from airunner.components.llm.utils.parse_template import (
        parse_template as legacy_component_parse_template,
    )
    from airunner.components.llm.utils.strip_names_from_message import (
        strip_names_from_message as legacy_component_strip_names,
    )
    from airunner.components.llm.utils.text_preprocessing import (
        prepare_text_for_tts as legacy_component_prepare_text_for_tts,
    )
    from airunner.utils import parse_template as legacy_parse_template
    from airunner.utils import (
        prepare_text_for_tts as legacy_prepare_text_for_tts,
    )
    from airunner.utils import (
        strip_names_from_message as legacy_strip_names_from_message,
    )
    from airunner.utils.job_tracker import JobTracker as LegacyJobTracker
    from airunner.utils.memory import (
        apply_cudnn_benchmark as legacy_apply_cudnn_benchmark,
    )
    from airunner.utils.memory import clear_memory as legacy_clear_memory
    from airunner.utils.memory.gpu_memory_stats import (
        gpu_memory_stats as legacy_gpu_memory_stats,
    )
    from airunner.utils.memory.runtime_flags import (
        apply_cudnn_benchmark as legacy_runtime_flags_apply,
    )
    from airunner.utils.path_policy import (
        normalize_local_path as legacy_normalize_local_path,
    )
    from airunner_services.utils.job_tracker import JobTracker
    from airunner_services.utils.memory import apply_cudnn_benchmark
    from airunner_services.utils.memory import clear_memory
    from airunner_services.utils.memory.gpu_memory_stats import (
        gpu_memory_stats,
    )
    from airunner_services.utils.path_policy import normalize_local_path
    from airunner_services.llm.utils.ministral3_config_patcher import (
        needs_patching,
    )
    from airunner_services.llm.utils.ministral3_config_patcher import (
        patch_ministral3_config,
    )
    from airunner_services.llm.utils.parse_template import parse_template
    from airunner_services.llm.utils.strip_names_from_message import (
        strip_names_from_message,
    )
    from airunner_services.utils.text import prepare_text_for_tts
    from airunner_services.utils.text.language_detection import (
        detect_language,
    )

    assert legacy_apply_cudnn_benchmark is not apply_cudnn_benchmark
    assert legacy_apply_cudnn_benchmark.__module__ == (
        "airunner.utils.memory.runtime_flags"
    )
    assert legacy_component_parse_template is not parse_template
    assert legacy_component_parse_template.__module__ == (
        "airunner.components.llm.utils.parse_template"
    )
    assert legacy_clear_memory is not clear_memory
    assert legacy_clear_memory.__module__ == (
        "airunner.utils.memory.clear_memory"
    )
    assert legacy_component_prepare_text_for_tts is not prepare_text_for_tts
    assert legacy_component_prepare_text_for_tts.__module__ == (
        "airunner.components.llm.utils.text_preprocessing"
    )
    assert legacy_component_strip_names is not strip_names_from_message
    assert legacy_component_strip_names.__module__ == (
        "airunner.components.llm.utils.strip_names_from_message"
    )
    assert legacy_detect_language is not detect_language
    assert legacy_detect_language.__module__ == (
        "airunner.components.llm.utils.language"
    )
    assert legacy_gpu_memory_stats is not gpu_memory_stats
    assert legacy_gpu_memory_stats.__module__ == (
        "airunner.utils.memory.gpu_memory_stats"
    )
    assert LegacyJobTracker is not JobTracker
    assert LegacyJobTracker.__module__ == "airunner.utils.job_tracker"
    assert legacy_needs_patching is not needs_patching
    assert legacy_needs_patching.__module__ == (
        "airunner.components.llm.utils.ministral3_config_patcher"
    )
    assert legacy_normalize_local_path is not normalize_local_path
    assert legacy_normalize_local_path.__module__ == (
        "airunner.utils.path_policy"
    )
    assert legacy_patch_ministral3_config is not patch_ministral3_config
    assert legacy_patch_ministral3_config.__module__ == (
        "airunner.components.llm.utils.ministral3_config_patcher"
    )
    assert legacy_parse_template is legacy_component_parse_template
    assert legacy_prepare_text_for_tts is legacy_component_prepare_text_for_tts
    assert legacy_strip_names_from_message is legacy_component_strip_names
    assert legacy_runtime_flags_apply is legacy_apply_cudnn_benchmark


def test_gui_utility_sources_avoid_service_imports() -> None:
    """Localized GUI utility helpers should not import service wrappers."""
    repo_root = Path(__file__).resolve().parents[4]
    path_policy_source = (
        repo_root / "gui" / "src" / "airunner" / "utils" / "path_policy.py"
    ).read_text(encoding="utf-8")
    exceptions_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "exceptions"
        / "__init__.py"
    ).read_text(encoding="utf-8")

    assert "airunner_services.utils.path_policy" not in path_policy_source
    assert "import_module" not in path_policy_source
    assert "sys.modules[__name__]" not in path_policy_source
    assert "airunner_services.application_exceptions" not in (
        exceptions_source
    )
    assert "import_module" not in exceptions_source
    assert "sys.modules[__name__]" not in exceptions_source


def test_art_rmbg_wrappers_share_identity() -> None:
    """Legacy GUI RMBG imports should resolve to service-owned modules."""
    from airunner_services.art.managers.rmbg.rmbg_model_manager import (
        RMBGModelManager as LegacyRMBGModelManager,
    )
    from airunner_services.art.managers.rmbg.rmbg_model_manager import (
        RMBGModelSpec as LegacyRMBGModelSpec,
    )
    from airunner.components.art.workers.background_removal_worker import (
        BackgroundRemovalWorker as LegacyBackgroundRemovalWorker,
    )
    from airunner_services.art.managers.rmbg.rmbg_model_manager import (
        RMBGModelManager,
        RMBGModelSpec,
    )
    from airunner_services.workers.background_removal_worker import (
        BackgroundRemovalWorker,
    )

    assert LegacyBackgroundRemovalWorker is BackgroundRemovalWorker
    assert LegacyRMBGModelManager is not RMBGModelManager
    assert LegacyRMBGModelSpec is not RMBGModelSpec


def test_art_rmbg_sources_avoid_service_imports() -> None:
    """Localized RMBG manager should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "art"
        / "managers"
        / "rmbg"
        / "rmbg_model_manager.py"
    ).read_text(encoding="utf-8")

    assert "airunner_services" not in source
    assert "import_module" not in source
    assert "sys.modules[__name__]" not in source


def test_pure_utility_wrappers_follow_current_ownership() -> None:
    """Legacy pure utility modules should follow current ownership."""
    from airunner.utils.application.get_version import (
        get_version as legacy_get_version,
    )
    from airunner.utils.application.platform_info import (
        get_platform_name as legacy_get_platform_name,
    )
    from airunner.utils.application.random_seed import (
        random_seed as legacy_random_seed,
    )
    from airunner.utils.audio.sound_device_manager import (
        SoundDeviceManager as LegacySoundDeviceManager,
    )
    from airunner.utils.crypto.data_encryption import (
        generate_fernet_key as legacy_generate_fernet_key,
    )
    from airunner.utils.gguf_ops import (
        dequantize_tensor as legacy_dequantize_tensor,
    )
    from airunner.utils.image.convert_binary_to_image import (
        convert_binary_to_image as legacy_convert_binary_to_image,
    )
    from airunner.utils.image.convert_image_to_binary import (
        convert_image_to_binary as legacy_convert_image_to_binary,
    )
    from airunner.utils.image.delete_image import (
        delete_image as legacy_delete_image,
    )
    from airunner.utils.image.export_image import (
        export_image as legacy_export_image,
    )
    from airunner.utils.image.load_metadata_from_image import (
        load_metadata_from_image as legacy_load_metadata_from_image,
    )
    from airunner.utils.location.get_lat_lon import get_lat_lon as legacy_get_lat_lon
    from airunner.utils.memory.is_ampere_or_newer import (
        is_ampere_or_newer as legacy_is_ampere_or_newer,
    )
    from airunner.utils.model_dtype_utils import (
        detect_model_dtype as legacy_detect_model_dtype,
    )
    from airunner.utils.model_optimizer import (
        ModelOptimizer as LegacyModelOptimizer,
    )
    from airunner.utils.model_optimizer import (
        get_model_optimizer as legacy_get_model_optimizer,
    )
    from airunner.utils.model_utils.model_utils import (
        get_stable_diffusion_model_storage_path as legacy_get_model_storage_path,
    )
    from airunner.utils.os.create_airunner_directory import (
        create_airunner_paths as legacy_create_airunner_paths,
    )
    from airunner.utils.text.formatter import Formatter as LegacyFormatter
    from airunner.utils.text.formatter_extended import (
        FormatterExtended as LegacyFormatterExtended,
    )
    from airunner.utils.vram_utils import (
        estimate_vram_from_path as legacy_estimate_vram_from_path,
    )
    from airunner.utils.zip_utils import safe_extract_zip as legacy_safe_extract_zip
    from airunner_services.utils.application.get_version import get_version
    from airunner_services.utils.application.platform_info import (
        get_platform_name,
    )
    from airunner_services.utils.application.random_seed import random_seed
    from airunner_services.utils.audio.sound_device_manager import (
        SoundDeviceManager,
    )
    from airunner_services.utils.crypto.data_encryption import (
        generate_fernet_key,
    )
    from airunner_services.utils.gguf_ops import dequantize_tensor
    from airunner_services.utils.image.convert_binary_to_image import (
        convert_binary_to_image,
    )
    from airunner_services.utils.image.convert_image_to_binary import (
        convert_image_to_binary,
    )
    from airunner_services.utils.image.delete_image import delete_image
    from airunner_services.utils.image.export_image import export_image
    from airunner_services.utils.image.load_metadata_from_image import (
        load_metadata_from_image,
    )
    from airunner_services.utils.location.get_lat_lon import get_lat_lon
    from airunner_services.utils.memory.is_ampere_or_newer import (
        is_ampere_or_newer,
    )
    from airunner_services.utils.model_dtype_utils import detect_model_dtype
    from airunner_services.utils.model_optimizer import ModelOptimizer
    from airunner_services.utils.model_optimizer import get_model_optimizer
    from airunner_services.utils.model_utils.model_utils import (
        get_stable_diffusion_model_storage_path,
    )
    from airunner_services.utils.os.create_airunner_directory import (
        create_airunner_paths,
    )
    from airunner_services.utils.text.formatter import Formatter
    from airunner_services.utils.text.formatter_extended import (
        FormatterExtended,
    )
    from airunner_services.utils.vram_utils import estimate_vram_from_path
    from airunner_services.utils.zip_utils import safe_extract_zip

    assert legacy_convert_binary_to_image is not convert_binary_to_image
    assert legacy_convert_binary_to_image.__module__ == (
        "airunner.utils.image.convert_binary_to_image"
    )
    assert legacy_convert_image_to_binary is not convert_image_to_binary
    assert legacy_convert_image_to_binary.__module__ == (
        "airunner.utils.image.convert_image_to_binary"
    )
    assert legacy_create_airunner_paths is not create_airunner_paths
    assert legacy_create_airunner_paths.__module__ == (
        "airunner.utils.os.create_airunner_directory"
    )
    assert legacy_delete_image is not delete_image
    assert legacy_delete_image.__module__ == (
        "airunner.utils.image.delete_image"
    )
    assert legacy_export_image is not export_image
    assert legacy_export_image.__module__ == (
        "airunner.utils.image.export_image"
    )
    assert LegacyFormatter is not Formatter
    assert LegacyFormatter.__module__ == "airunner.utils.text.formatter"
    assert LegacyFormatterExtended is not FormatterExtended
    assert LegacyFormatterExtended.__module__ == (
        "airunner.utils.text.formatter_extended"
    )
    assert legacy_detect_model_dtype is not detect_model_dtype
    assert legacy_detect_model_dtype.__module__ == (
        "airunner.utils.model_dtype_utils"
    )
    assert legacy_estimate_vram_from_path is not estimate_vram_from_path
    assert legacy_estimate_vram_from_path.__module__ == (
        "airunner.utils.vram_utils"
    )
    assert legacy_get_model_storage_path is not (
        get_stable_diffusion_model_storage_path
    )
    assert legacy_get_model_storage_path.__module__ == (
        "airunner.utils.model_utils.model_utils"
    )
    assert legacy_get_model_optimizer is not get_model_optimizer
    assert legacy_get_model_optimizer.__module__ == (
        "airunner.utils.model_optimizer"
    )
    assert legacy_load_metadata_from_image is not load_metadata_from_image
    assert legacy_load_metadata_from_image.__module__ == (
        "airunner.utils.image.load_metadata_from_image"
    )
    assert legacy_get_lat_lon is not get_lat_lon
    assert legacy_get_lat_lon.__module__ == "airunner.utils.location.get_lat_lon"
    assert legacy_generate_fernet_key is not generate_fernet_key
    assert legacy_generate_fernet_key.__module__ == (
        "airunner.utils.crypto.data_encryption"
    )
    assert legacy_dequantize_tensor is not dequantize_tensor
    assert legacy_dequantize_tensor.__module__ == "airunner.utils.gguf_ops"
    assert legacy_get_platform_name is not get_platform_name
    assert legacy_get_version is not get_version
    assert legacy_is_ampere_or_newer is not is_ampere_or_newer
    assert legacy_is_ampere_or_newer.__module__ == (
        "airunner.utils.memory.is_ampere_or_newer"
    )
    assert LegacyModelOptimizer is not ModelOptimizer
    assert LegacyModelOptimizer.__module__ == "airunner.utils.model_optimizer"
    assert legacy_random_seed is not random_seed
    assert legacy_safe_extract_zip is not safe_extract_zip
    assert legacy_safe_extract_zip.__module__ == "airunner.utils.zip_utils"
    assert LegacySoundDeviceManager is not SoundDeviceManager
    assert LegacySoundDeviceManager.__module__ == (
        "airunner.utils.audio.sound_device_manager"
    )


def test_gui_image_and_archive_utility_sources_avoid_service_imports() -> None:
    """Localized image/archive utility helpers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    utility_files = [
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "image"
        / "convert_binary_to_image.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "image"
        / "convert_image_to_binary.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "image"
        / "delete_image.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "image"
        / "export_image.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "image"
        / "load_metadata_from_image.py",
        repo_root / "gui" / "src" / "airunner" / "utils" / "zip_utils.py",
    ]

    for path in utility_files:
        source = path.read_text(encoding="utf-8")
        assert "airunner_services" not in source, path.as_posix()
        assert "import_module" not in source, path.as_posix()
        assert "sys.modules[__name__]" not in source, path.as_posix()


def test_gui_audio_and_location_utility_sources_avoid_service_imports() -> None:
    """Localized audio/location utility helpers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    utility_files = [
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "audio"
        / "sound_device_manager.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "location"
        / "get_lat_lon.py",
    ]

    for path in utility_files:
        source = path.read_text(encoding="utf-8")
        assert "airunner_services" not in source, path.as_posix()
        assert "import_module" not in source, path.as_posix()
        assert "sys.modules[__name__]" not in source, path.as_posix()


def test_gui_text_utility_sources_avoid_service_imports() -> None:
    """Localized text utility helpers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/utils/text/formatter.py"),
        Path("gui/src/airunner/utils/text/formatter_extended.py"),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_gui_model_utility_sources_avoid_service_imports() -> None:
    """Localized model utility helpers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/utils/gguf_ops.py"),
        Path("gui/src/airunner/utils/model_dtype_utils.py"),
        Path("gui/src/airunner/utils/model_optimizer.py"),
        Path("gui/src/airunner/utils/model_utils/model_utils.py"),
        Path("gui/src/airunner/utils/vram_utils.py"),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_gui_runtime_utility_sources_avoid_service_imports() -> None:
    """Localized runtime utility helpers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    llm_utils_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "utils"
        / "__init__.py"
    ).read_text(encoding="utf-8")
    job_tracker_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "job_tracker.py"
    ).read_text(encoding="utf-8")
    text_preprocessing_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "utils"
        / "text_preprocessing.py"
    ).read_text(encoding="utf-8")
    parse_template_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "utils"
        / "parse_template.py"
    ).read_text(encoding="utf-8")
    gpt_oss_parser_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "utils"
        / "gpt_oss_parser.py"
    ).read_text(encoding="utf-8")
    language_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "utils"
        / "language.py"
    ).read_text(encoding="utf-8")
    ministral3_config_patcher_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "utils"
        / "ministral3_config_patcher.py"
    ).read_text(encoding="utf-8")
    strip_names_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "utils"
        / "strip_names_from_message.py"
    ).read_text(encoding="utf-8")

    assert "airunner_services" not in llm_utils_source
    assert "import_module" not in llm_utils_source
    assert "sys.modules[__name__]" not in llm_utils_source
    assert "airunner_services" not in job_tracker_source
    assert "import_module" not in job_tracker_source
    assert "sys.modules[__name__]" not in job_tracker_source
    assert "airunner_services" not in parse_template_source
    assert "import_module" not in parse_template_source
    assert "sys.modules[__name__]" not in parse_template_source
    assert "airunner_services" not in gpt_oss_parser_source
    assert "import_module" not in gpt_oss_parser_source
    assert "sys.modules[__name__]" not in gpt_oss_parser_source
    assert "airunner_services" not in language_source
    assert "import_module" not in language_source
    assert "sys.modules[__name__]" not in language_source
    assert "airunner_services" not in ministral3_config_patcher_source
    assert "import_module" not in ministral3_config_patcher_source
    assert "sys.modules[__name__]" not in ministral3_config_patcher_source
    assert "airunner_services" not in strip_names_source
    assert "import_module" not in strip_names_source
    assert "sys.modules[__name__]" not in strip_names_source
    assert "airunner_services" not in text_preprocessing_source
    assert "import_module" not in text_preprocessing_source
    assert "sys.modules[__name__]" not in text_preprocessing_source


def test_gui_crypto_utility_sources_avoid_service_imports() -> None:
    """Localized crypto utility helpers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "crypto"
        / "data_encryption.py"
    ).read_text(encoding="utf-8")

    assert "airunner_services" not in source
    assert "import_module" not in source
    assert "sys.modules[__name__]" not in source


def test_gui_os_utility_sources_avoid_service_imports() -> None:
    """Localized OS utility helpers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "os"
        / "create_airunner_directory.py"
    ).read_text(encoding="utf-8")

    assert "airunner_services" not in source
    assert "import_module" not in source
    assert "sys.modules[__name__]" not in source


def test_bin_wrappers_share_identity() -> None:
    """Legacy bin modules should reflect current command ownership."""
    from pathlib import Path

    from scripts.code_quality_report import main as legacy_quality_main
    from scripts.coverage_report import main as legacy_coverage_main
    from scripts.mypy_shortcut import main as legacy_mypy_main
    from scripts.remove_unused_imports import (
        main as legacy_remove_unused_main,
    )
    from scripts.run_tests import main as legacy_run_tests_main

    assert legacy_quality_main.__module__ == "scripts.code_quality_report"
    assert legacy_coverage_main.__module__ == "scripts.coverage_report"
    assert legacy_mypy_main.__module__ == "scripts.mypy_shortcut"
    assert legacy_remove_unused_main.__module__ == (
        "scripts.remove_unused_imports"
    )
    assert legacy_run_tests_main.__module__ == "scripts.run_tests"

    # Verify that stale bin wrappers no longer exist
    for path in (
        Path("gui/src/airunner/bin/cleanup_llm_models.py"),
        Path("gui/src/airunner/bin/docker_wrapper.py"),
        Path("gui/src/airunner/bin/generate_cert.py"),
    ):
        assert not path.exists(), (
            f"Stale wrapper should not exist: {path.as_posix()}"
        )
        assert "sys.modules[__name__]" not in source, path.as_posix()

    for path in (
        Path("gui/src/airunner/bin/cleanup_llm_models.py"),
        Path("gui/src/airunner/bin/code_quality_report.py"),
        Path("gui/src/airunner/bin/coverage_report.py"),
        Path("gui/src/airunner/bin/docker_wrapper.py"),
        Path("gui/src/airunner/bin/generate_cert.py"),
        Path("gui/src/airunner/bin/kill_zombie_processes.py"),
        Path("gui/src/airunner/bin/mypy_shortcut.py"),
        Path("gui/src/airunner/bin/remove_unused_imports.py"),
        Path("gui/src/airunner/bin/run_tests.py"),
    ):
        source = path.read_text(encoding="utf-8")
        assert "airunner_shared.shared_tooling" not in source


def test_settings_utility_wrapper_is_gui_owned() -> None:
    """Legacy GUI settings helpers should resolve to the GUI helper."""
    from airunner.utils.settings import (
        get_qsettings as legacy_get_qsettings,
    )
    from airunner.utils.settings.get_qsettings import (
        get_qsettings as legacy_module_get_qsettings,
    )

    assert legacy_get_qsettings is legacy_module_get_qsettings
    assert legacy_get_qsettings.__module__ == (
        "airunner.utils.settings.get_qsettings"
    )


def test_dead_gui_bin_wrappers_removed() -> None:
    """Dead GUI bin compatibility wrappers should remain deleted."""
    repo_root = Path(__file__).resolve().parents[4]
    expected_absent = [
        repo_root / "gui" / "src" / "airunner" / "bin" / "airunner_service.py",
        repo_root / "gui" / "src" / "airunner" / "bin" / "airunner_hf_download.py",
        repo_root / "gui" / "src" / "airunner" / "bin" / "airunner_civitai_download.py",
        repo_root / "gui" / "src" / "airunner" / "bin" / "docker_build.py",
    ]

    for path in expected_absent:
        assert not path.exists(), path.as_posix()


def test_shared_helper_wrappers_follow_current_ownership() -> None:
    """Legacy helper paths should reflect current GUI and shared ownership."""
    from airunner.dev_build_token import current_dev_build_token as legacy_token
    from airunner.daemon_client import GuiDaemonClient as LegacyGuiDaemonClient
    from airunner.daemon_client.daemon_connection_state import (
        DaemonConnectionState as LegacyDaemonConnectionState,
    )
    from airunner_services.daemon_connection_state import (
        DaemonConnectionState,
    )
    from airunner_services.dev_build_token import current_dev_build_token
    assert LegacyGuiDaemonClient.__module__ == (
        "airunner.daemon_client.gui_daemon_client"
    )
    assert legacy_token is not current_dev_build_token
    assert legacy_token.__module__ == "airunner.dev_build_token"
    assert LegacyDaemonConnectionState is not DaemonConnectionState
    assert LegacyDaemonConnectionState.__module__ == (
        "airunner.daemon_client.daemon_connection_state"
    )

def test_api_client_wrappers_follow_current_ownership() -> None:
    """Daemon-client imports should reflect GUI vs API/service ownership."""
    from airunner.daemon_client import DaemonLauncher as LegacyDaemonLauncher
    from airunner.daemon_client import GuiDaemonClient as LegacyGuiDaemonClient
    from airunner_api.client import DaemonLauncher as APIDaemonLauncher
    from airunner_api.client import GuiDaemonClient as APIGuiDaemonClient
    from airunner_services.daemon_client import DaemonLauncher
    from airunner_services.daemon_client import GuiDaemonClient

    assert LegacyDaemonLauncher.__module__ == (
        "airunner.daemon_client.daemon_launcher"
    )
    assert LegacyGuiDaemonClient.__module__ == (
        "airunner.daemon_client.gui_daemon_client"
    )
    assert LegacyDaemonLauncher is not APIDaemonLauncher
    assert LegacyGuiDaemonClient is not APIGuiDaemonClient
    assert APIDaemonLauncher is DaemonLauncher
    assert APIGuiDaemonClient is GuiDaemonClient


def test_gui_runtime_contracts_are_local() -> None:
    """GUI runtime contracts should resolve through the local contract module."""
    from pathlib import Path

    from airunner.ipc.messages import RequestEnvelope
    from airunner.runtimes.contracts import RuntimeAction
    from airunner.runtimes.contracts import RuntimeKind

    assert RequestEnvelope.model_fields["runtime"].annotation is RuntimeKind
    assert RequestEnvelope.model_fields["action"].annotation is RuntimeAction

    for path in (
        Path("gui/src/airunner/runtimes/contracts.py"),
        Path("gui/src/airunner/ipc/messages.py"),
    ):
        source = path.read_text(encoding="utf-8")
        assert "airunner_model.contracts" not in source


def test_gui_runtime_bootstrap_uses_local_registry_helpers() -> None:
    """GUI runtime bootstrap should use GUI-local sidecar runtime helpers."""
    from pathlib import Path

    from airunner.runtime_bootstrap import build_runtime_registry
    from airunner.runtimes.registry import RuntimeRegistry

    registry = build_runtime_registry()

    assert isinstance(registry, RuntimeRegistry)

    source = Path("gui/src/airunner/runtime_bootstrap.py").read_text(
        encoding="utf-8"
    )
    assert "airunner_model.runtimes.registry" not in source
    assert "airunner_model.runtimes.sidecar_art_client" not in source
    assert "airunner_model.runtimes.sidecar_llm_client" not in source
    assert "airunner_model.runtimes.sidecar_stt_client" not in source
    assert "airunner_model.runtimes.sidecar_tts_client" not in source
    assert "airunner_services.runtimes.sidecar_art_client" not in source
    assert "airunner_services.runtimes.local_fallback" not in source
    assert "airunner_services.runtimes.sidecar_llm_client" not in source
    assert "airunner_services.runtimes.sidecar_stt_client" not in source
    assert "airunner_services.runtimes.sidecar_tts_client" not in source


def test_gui_runtime_fallback_and_signal_mediator_are_local() -> None:
    """GUI runtime fallback helpers should not import service utility code."""
    from pathlib import Path

    for path in (
        Path("gui/src/airunner/runtimes/local_fallback.py"),
        Path("gui/src/airunner/utils/application/signal_mediator.py"),
    ):
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.runtimes.local_fallback" not in source
        assert "airunner_services.utils.application.signal_mediator" not in source


def test_gui_api_service_base_uses_local_runtime_context_mixin() -> None:
    """GUI API base classes should not import the service runtime mixin."""
    from pathlib import Path

    for path in (
        Path("gui/src/airunner/components/application/api/api_service_base.py"),
        Path("gui/src/airunner/utils/application/runtime_context_mixin.py"),
        Path("gui/src/airunner/utils/application/api_reference.py"),
    ):
        source = path.read_text(encoding="utf-8")
        assert (
            "airunner_services.utils.application.runtime_context_mixin"
            not in source
        )
        assert "airunner_services.utils.application.api_reference" not in source


def test_ipc_envelope_wrappers_share_identity() -> None:
    """Legacy GUI IPC imports should now resolve to GUI-owned envelopes."""
    from airunner.ipc.messages import RequestEnvelope as LegacyRequestEnvelope
    from airunner_api.messages import RequestEnvelope as APIRequestEnvelope
    from airunner_services.ipc.messages import RequestEnvelope

    assert LegacyRequestEnvelope is not APIRequestEnvelope
    assert LegacyRequestEnvelope.__module__ == "airunner.ipc.messages"
    assert APIRequestEnvelope is RequestEnvelope


def test_api_service_wrappers_follow_current_ownership() -> None:
    """API package service imports should reflect current ownership."""
    from airunner.components.application.api.api_service_base import (
        APIServiceBase as LegacyAPIServiceBase,
    )
    from airunner.components.art.api.art_services import (
        ARTAPIService as LegacyARTAPIService,
    )
    from airunner.components.llm.api.llm_services import (
        LLMAPIService as LegacyLLMAPIService,
    )
    from airunner.components.stt.api.stt_services import (
        STTAPIService as LegacySTTAPIService,
    )
    from airunner.components.tts.api.tts_services import (
        TTSAPIService as LegacyTTSAPIService,
    )
    from airunner_api.api_service_base import APIServiceBase as APIAPIServiceBase
    from airunner_api.services.art_services import ARTAPIService as APIARTAPIService
    from airunner_api.services.llm_services import LLMAPIService as APILLMAPIService
    from airunner_api.services.stt_services import STTAPIService as APISTTAPIService
    from airunner_api.services.tts_services import TTSAPIService as APITTSAPIService
    from airunner_services.api.api_service_base import APIServiceBase
    from airunner_services.api.services.art_services import ARTAPIService
    from airunner_services.api.services.llm_services import LLMAPIService
    from airunner_services.api.services.stt_services import STTAPIService
    from airunner_services.api.services.tts_services import TTSAPIService

    assert LegacyAPIServiceBase is not APIAPIServiceBase
    assert LegacyAPIServiceBase.__module__ == (
        "airunner.components.application.api.api_service_base"
    )
    assert APIAPIServiceBase is APIServiceBase
    assert LegacyARTAPIService is not APIARTAPIService
    assert LegacyARTAPIService.__module__ == (
        "airunner.components.art.api.art_services"
    )
    assert APIARTAPIService is ARTAPIService
    assert LegacySTTAPIService is not APISTTAPIService
    assert LegacySTTAPIService.__module__ == (
        "airunner.components.stt.api.stt_services"
    )
    assert APISTTAPIService is STTAPIService
    assert LegacyTTSAPIService is not APITTSAPIService
    assert LegacyTTSAPIService.__module__ == (
        "airunner.components.tts.api.tts_services"
    )
    assert APITTSAPIService is TTSAPIService
    assert LegacyLLMAPIService is not APILLMAPIService
    assert LegacyLLMAPIService.__module__ == (
        "airunner.components.llm.api.llm_services"
    )
    assert APILLMAPIService.__module__ == (
        "airunner_services.llm.api.llm_services"
    )
    assert issubclass(APILLMAPIService, LLMAPIService)
    assert not issubclass(LegacyLLMAPIService, LLMAPIService)


def test_gui_imports_api_package_surface() -> None:
    """GUI boundary modules should reflect current split ownership."""
    repo_root = Path(__file__).resolve().parents[4]
    app_source = (repo_root / "gui" / "src" / "airunner" / "app.py").read_text(
        encoding="utf-8"
    )
    main_source = (
        repo_root / "gui" / "src" / "airunner" / "main.py"
    ).read_text(encoding="utf-8")
    headless_runtime_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "app_mixins"
        / "headless_runtime_mixin.py"
    ).read_text(encoding="utf-8")
    database_bootstrap_source = (
        repo_root / "gui" / "src" / "airunner" / "database_bootstrap.py"
    ).read_text(encoding="utf-8")
    ui_runtime_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "app_mixins"
        / "ui_runtime_mixin.py"
    ).read_text(encoding="utf-8")
    api_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "api"
        / "api.py"
    ).read_text(encoding="utf-8")
    api_service_base_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "api"
        / "api_service_base.py"
    ).read_text(encoding="utf-8")
    llm_service_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "api"
        / "llm_services.py"
    ).read_text(encoding="utf-8")
    runtime_bootstrap_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "runtime_bootstrap.py"
    ).read_text(encoding="utf-8")
    airunner_headless_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "bin"
        / "airunner_headless.py"
    ).read_text(encoding="utf-8")
    generate_migration_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "bin"
        / "generate_migration.py"
    ).read_text(encoding="utf-8")
    settings_mixin_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "gui"
        / "windows"
        / "main"
        / "settings_mixin.py"
    ).read_text(encoding="utf-8")
    worker_manager_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "gui"
        / "windows"
        / "main"
        / "worker_manager.py"
    ).read_text(encoding="utf-8")
    model_status_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "model_management"
        / "gui"
        / "model_status_widget.py"
    ).read_text(encoding="utf-8")
    tts_vocalizer_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "tts"
        / "workers"
        / "tts_vocalizer_worker.py"
    ).read_text(encoding="utf-8")

    assert "from airunner.daemon_client import GuiDaemonClient" in app_source
    assert "from airunner.runtime_bootstrap import build_runtime_registry" in app_source
    assert "from airunner_api.bootstrap import build_runtime_registry" not in app_source
    assert "airunner_services.daemon_client" not in app_source
    assert "airunner_services.runtimes.bootstrap" not in app_source
    assert "from airunner_api.privacy import activate" not in main_source
    assert "airunner_services.vendor.facehuggershield" not in main_source
    assert "airunner_api.headless_runtime_mixin" not in headless_runtime_source
    assert "import airunner.setup_database as setup_database_module" in (
        database_bootstrap_source
    )
    assert "from airunner_api.bootstrap import setup_database" not in (
        database_bootstrap_source
    )
    assert "from airunner.live_app import set_api" in ui_runtime_source
    assert "from airunner.live_app import get_api" in ui_runtime_source
    assert "airunner_services.api.legacy_server" not in ui_runtime_source
    assert "from airunner.live_app import get_api" in settings_mixin_source
    assert "components.server.api.server" not in settings_mixin_source
    assert "from airunner.live_app import get_api" in worker_manager_source
    assert "components.server.api.server" not in worker_manager_source
    assert "from airunner.live_app import get_api" in model_status_source
    assert "components.server.api.server" not in model_status_source
    assert "from airunner.live_app import get_api" in tts_vocalizer_source
    assert "components.server.api.server" not in tts_vocalizer_source
    assert "from airunner.components.art.api.art_services import" in api_source
    assert "from airunner_api.services.art_services import" not in api_source
    assert "from airunner.components.llm.api.llm_services import" in api_source
    assert "from airunner_api.services.llm_services import" not in api_source
    assert "from airunner.components.stt.api.stt_services import" in api_source
    assert "from airunner.components.tts.api.tts_services import" in api_source
    assert "from airunner_api.services.stt_services import" not in api_source
    assert "from airunner_api.services.tts_services import" not in api_source
    assert "airunner_api.requests.image_request" not in api_source
    assert "airunner_api.api_service_base" not in api_service_base_source
    assert "airunner_api.services.llm_services" not in llm_service_source
    assert "airunner_services.api.services" not in llm_service_source
    assert "airunner_services.utils.application.api_reference" not in (
        llm_service_source
    )
    assert "airunner_api.bootstrap" not in runtime_bootstrap_source
    assert "airunner_api.airunner_headless" not in airunner_headless_source
    assert "airunner_api.generate_migration" not in generate_migration_source
    assert "airunner_services.api.services" not in api_source


def test_gui_server_wrapper_cluster_removed() -> None:
    """GUI server wrapper files should be deleted after cutover."""
    repo_root = Path(__file__).resolve().parents[4]

    assert not (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "server"
        / "api"
        / "server.py"
    ).exists()
    assert not (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "server"
        / "api"
        / "api_server_thread.py"
    ).exists()


def test_gui_service_wrapper_cluster_removed() -> None:
    """GUI service wrapper files should be deleted once unused."""
    repo_root = Path(__file__).resolve().parents[4]
    services_root = (
        repo_root / "gui" / "src" / "airunner" / "services"
    )

    assert not (services_root / "daemon.py").exists()
    assert not (services_root / "daemon_config.py").exists()
    assert not (services_root / "lifecycle_service.py").exists()
    assert not (services_root / "service_manager.py").exists()
    assert not (services_root / "service_worker_manager.py").exists()


def test_gui_api_wrapper_cluster_removed() -> None:
    """GUI api wrapper files should be deleted after migration."""
    repo_root = Path(__file__).resolve().parents[4]
    api_root = repo_root / "gui" / "src" / "airunner" / "api"

    assert not (api_root / "__init__.py").exists()
    assert not (api_root / "server.py").exists()
    assert not (api_root / "routes" / "__init__.py").exists()
    assert not (api_root / "routes" / "art.py").exists()
    assert not (api_root / "routes" / "conversations.py").exists()
    assert not (api_root / "routes" / "daemon.py").exists()
    assert not (api_root / "routes" / "daemon_helpers.py").exists()
    assert not (api_root / "routes" / "downloads.py").exists()
    assert not (api_root / "routes" / "health.py").exists()
    assert not (api_root / "routes" / "legacy.py").exists()
    assert not (api_root / "routes" / "llm.py").exists()
    assert not (api_root / "routes" / "stt.py").exists()
    assert not (api_root / "routes" / "tts.py").exists()
    assert not (api_root / "models" / "__init__.py").exists()
    assert not (api_root / "models" / "daemon_runtime_status_response.py").exists()
    assert not (api_root / "models" / "runtime_route_request.py").exists()
    assert not (api_root / "models" / "runtime_summary_response.py").exists()


def test_gui_download_flow_uses_gui_owned_download_client() -> None:
    """GUI download flows should use the GUI-owned download client seam."""
    repo_root = Path(__file__).resolve().parents[4]
    download_client_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "utils"
        / "download_job_client.py"
    ).read_text(encoding="utf-8")
    download_runner_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "workers"
        / "download_job_runner.py"
    ).read_text(encoding="utf-8")
    qt_civitai_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "workers"
        / "qt_civitai_workers.py"
    ).read_text(encoding="utf-8")
    download_dialog_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "gui"
        / "windows"
        / "main"
        / "download_model_dialog.py"
    ).read_text(encoding="utf-8")
    download_models_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "gui"
        / "dialogs"
        / "download_models_dialog.py"
    ).read_text(encoding="utf-8")
    worker_manager_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "gui"
        / "windows"
        / "main"
        / "worker_manager.py"
    ).read_text(encoding="utf-8")
    service_download_worker_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "workers"
        / "service_download_worker.py"
    ).read_text(encoding="utf-8")

    assert "airunner_api.downloads" not in download_client_source
    assert "airunner_services.downloads" not in download_client_source
    assert "DownloadJobClient" in download_runner_source
    assert "import airunner_api.downloads as download_api" not in (
        download_runner_source
    )
    assert "airunner_services.downloads.job_service" not in (
        download_runner_source
    )
    assert "airunner_services.utils.job_tracker" not in download_runner_source
    assert "DownloadJobClient" in qt_civitai_source
    assert "import airunner_api.downloads as download_api" not in (
        qt_civitai_source
    )
    assert "airunner_services.downloads.service" not in qt_civitai_source
    assert "DownloadJobClient" in service_download_worker_source
    assert "airunner_api" not in service_download_worker_source
    assert "airunner_services.downloads" not in service_download_worker_source
    assert (
        "from airunner.components.application.utils.download_helpers import" in
        download_dialog_source
    )
    assert "import airunner_api.downloads as download_api" not in (
        download_dialog_source
    )
    assert "airunner_services.downloads.service" not in (
        download_dialog_source
    )
    assert (
        "from airunner.components.application.utils.download_helpers import" in
        download_models_source
    )
    assert "import airunner_api.downloads as download_api" not in (
        download_models_source
    )
    assert "airunner_services.downloads.service" not in (
        download_models_source
    )
    assert "ServiceDownloadWorker" in worker_manager_source
    assert "from airunner_api import downloads as download_api" not in (
        worker_manager_source
    )

    provider_policy_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "llm"
        / "config"
        / "provider_access_policy.py"
    ).read_text(encoding="utf-8")
    assert "airunner_services.downloads.policy" not in provider_policy_source
    assert "airunner_services.downloads.service_download_worker" not in (
        worker_manager_source
    )
    assert "airunner_services.downloads.service" not in worker_manager_source


def test_gui_application_data_imports_api_surface() -> None:
    """GUI application-data facades should reflect current ownership."""
    repo_root = Path(__file__).resolve().parents[4]
    application_data_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "data"
        / "__init__.py"
    ).read_text(encoding="utf-8")
    shortcut_keys_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "data"
        / "shortcut_keys.py"
    ).read_text(encoding="utf-8")

    assert "from airunner_api.application_data import ShortcutKeys" not in (
        application_data_source
    )
    assert "from airunner_api.application_data import table_to_class" not in (
        application_data_source
    )
    assert "airunner_services.application_data" not in application_data_source
    assert "airunner_model.models" not in application_data_source
    assert "from airunner.components.application.data.shortcut_keys" in (
        application_data_source
    )
    assert "from airunner.components.application.data import ShortcutKeys" not in (
        shortcut_keys_source
    )
    assert "from airunner.components.data.models.base import BaseModel" in (
        shortcut_keys_source
    )
    assert "airunner_model.models.shortcut_keys" not in (
        shortcut_keys_source
    )


def test_gui_api_wrappers_import_api_package_surface() -> None:
    """Legacy GUI API wrappers should target the API package, not services."""
    repo_root = Path(__file__).resolve().parents[4]
    api_wrapper_root = repo_root / "gui" / "src" / "airunner" / "api"
    server_wrapper_root = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "server"
        / "api"
    )
    application_api_root = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "application"
        / "api"
    )
    utility_wrapper_roots = [
        repo_root / "gui" / "src" / "airunner" / "utils" / "db",
        repo_root / "gui" / "src" / "airunner" / "utils" / "data",
        repo_root / "gui" / "src" / "airunner" / "utils" / "memory",
    ]
    infrastructure_wrapper_roots = [
        repo_root / "gui" / "src" / "airunner" / "services",
        repo_root / "gui" / "src" / "airunner" / "ipc",
    ]
    infrastructure_wrapper_files = [
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "app_mixins"
        / "__init__.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "app_mixins"
        / "headless_runtime_mixin.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "bin"
        / "airunner_headless.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "bin"
        / "generate_migration.py",
    ]
    gui_owned_utility_files = [
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "data"
        / "model_to_dataclass.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "memory"
        / "clear_memory.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "memory"
        / "gpu_memory_stats.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "memory"
        / "is_ampere_or_newer.py",
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "utils"
        / "memory"
        / "runtime_flags.py",
    ]

    for path in sorted(api_wrapper_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.api" not in source, path.as_posix()

    for path in sorted(server_wrapper_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.api" not in source, path.as_posix()

    for path in sorted(application_api_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.api" not in source, path.as_posix()

    for root in utility_wrapper_roots:
        for path in sorted(root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            assert "airunner_services.utils" not in source, path.as_posix()

    for root in infrastructure_wrapper_roots:
        for path in sorted(root.rglob("*.py")):
            if "tests" in path.parts:
                continue
            source = path.read_text(encoding="utf-8")
            assert "airunner_services" not in source, path.as_posix()

    for path in infrastructure_wrapper_files:
        source = path.read_text(encoding="utf-8")
        assert "airunner_services" not in source, path.as_posix()

    setup_database_source = (
        repo_root / "gui" / "src" / "airunner" / "setup_database.py"
    ).read_text(encoding="utf-8")
    assert "airunner_api" not in setup_database_source
    assert "airunner_services.database" not in setup_database_source
    assert "airunner.utils.db.engine" in setup_database_source

    for path in gui_owned_utility_files:
        source = path.read_text(encoding="utf-8")
        assert "airunner_api" not in source, path.as_posix()


def test_gui_model_management_wrappers_import_model_package_surface() -> None:
    """GUI model-management sources should avoid service imports."""
    repo_root = Path(__file__).resolve().parents[4]
    wrapper_root = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "model_management"
    )

    for path in sorted(wrapper_root.rglob("*.py")):
        if "tests" in path.parts or "gui" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.model_management" not in source, path.as_posix()


def test_gui_model_management_utility_modules_are_localized() -> None:
    """GUI model-management sources should avoid model imports."""
    repo_root = Path(__file__).resolve().parents[4]
    wrapper_root = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "model_management"
    )

    for path in sorted(wrapper_root.rglob("*.py")):
        if "tests" in path.parts or "gui" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        assert "airunner_model.model_management" not in source, path.as_posix()
        assert "airunner_services.model_management" not in source, path.as_posix()


def test_model_management_wrappers_share_identity() -> None:
    """Legacy GUI model-management imports should stay compatible."""
    from airunner.components.model_management import CanvasMemoryTracker as LegacyCanvasMemoryTracker
    from airunner.components.model_management import HardwareProfiler as LegacyHardwareProfiler
    from airunner.components.model_management import MemoryAllocator as LegacyMemoryAllocator
    from airunner.components.model_management import ModelRegistry as LegacyModelRegistry
    from airunner.components.model_management import ModelResourceManager as LegacyModelResourceManager
    from airunner.components.model_management import ModelState as LegacyModelState
    from airunner.components.model_management import QuantizationStrategy as LegacyQuantizationStrategy
    from airunner.components.model_management.mixins import MemoryTrackingMixin as LegacyMemoryTrackingMixin
    from airunner.components.model_management.mixins import ModelLoadingMixin as LegacyModelLoadingMixin
    from airunner.components.model_management.mixins import ModelSelectionMixin as LegacyModelSelectionMixin
    from airunner.components.model_management.mixins import ModelStateMixin as LegacyModelStateMixin
    from airunner_services.model_management import CanvasMemoryTracker
    from airunner_services.model_management import HardwareProfiler
    from airunner_services.model_management import MemoryAllocator
    from airunner_services.model_management import ModelRegistry
    from airunner_services.model_management import ModelResourceManager
    from airunner_services.model_management import ModelState
    from airunner_services.model_management import QuantizationStrategy
    from airunner_services.model_management.mixins import MemoryTrackingMixin
    from airunner_services.model_management.mixins import ModelLoadingMixin
    from airunner_services.model_management.mixins import ModelSelectionMixin
    from airunner_services.model_management.mixins import ModelStateMixin

    assert LegacyCanvasMemoryTracker.__name__ == CanvasMemoryTracker.__name__
    assert LegacyHardwareProfiler.__name__ == HardwareProfiler.__name__
    assert LegacyMemoryAllocator.__name__ == MemoryAllocator.__name__
    assert LegacyMemoryTrackingMixin.__name__ == MemoryTrackingMixin.__name__
    assert LegacyModelLoadingMixin.__name__ == ModelLoadingMixin.__name__
    assert LegacyModelRegistry.__name__ == ModelRegistry.__name__
    assert LegacyModelResourceManager.__name__ == ModelResourceManager.__name__
    assert LegacyModelSelectionMixin.__name__ == ModelSelectionMixin.__name__
    assert LegacyModelState.__name__ == ModelState.__name__
    assert LegacyModelStateMixin.__name__ == ModelStateMixin.__name__
    assert LegacyQuantizationStrategy.__name__ == QuantizationStrategy.__name__

    legacy_registry = LegacyModelRegistry()
    service_registry = ModelRegistry()
    legacy_canvas_tracker = LegacyCanvasMemoryTracker()
    service_canvas_tracker = CanvasMemoryTracker()

    for mixin, service_mixin, methods in (
        (
            LegacyMemoryTrackingMixin,
            MemoryTrackingMixin,
            (
                "update_canvas_history_allocation",
                "update_external_apps_allocation",
                "get_memory_allocation_breakdown",
            ),
        ),
        (
            LegacyModelLoadingMixin,
            ModelLoadingMixin,
            ("prepare_model_loading", "request_model_swap"),
        ),
        (
            LegacyModelSelectionMixin,
            ModelSelectionMixin,
            ("select_best_model",),
        ),
        (
            LegacyModelStateMixin,
            ModelStateMixin,
            ("get_model_state", "get_active_models", "cleanup_model"),
        ),
    ):
        for method in methods:
            assert callable(getattr(mixin, method))
            assert callable(getattr(service_mixin, method))

    class Scene:
        undo_history = [{"type": "create", "layers_after": [{}]}]
        redo_history = []

    assert [state.value for state in LegacyModelState] == [
        state.value for state in ModelState
    ]
    assert (
        legacy_registry.get_model("qwen3-8b").runtime_backend
        == service_registry.get_model("qwen3-8b").runtime_backend
    )
    assert (
        legacy_registry.get_model("ggml-large-v3.bin").model_type.value
        == service_registry.get_model("ggml-large-v3.bin").model_type.value
    )
    assert (
        legacy_canvas_tracker.get_history_summary(Scene())["total_entries"]
        == service_canvas_tracker.get_history_summary(Scene())["total_entries"]
    )
    assert (
        LegacyModelResourceManager._parse_nvidia_vram_usage("512\n")
        == ModelResourceManager._parse_nvidia_vram_usage("512\n")
    )
    assert (
        LegacyModelResourceManager._parse_rocm_vram_usage("gpu,used,256 MB\n")
        == ModelResourceManager._parse_rocm_vram_usage("gpu,used,256 MB\n")
    )


def test_gui_runtime_wrapper_sources_avoid_service_runtime_tunnels() -> None:
    """Legacy GUI runtime sources should not route through services."""
    repo_root = Path(__file__).resolve().parents[4]
    wrapper_root = repo_root / "gui" / "src" / "airunner" / "runtimes"

    for path in sorted(wrapper_root.rglob("*.py")):
        if "tests" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.runtimes" not in source, path.as_posix()


def test_gui_native_wrapper_sources_avoid_native_imports() -> None:
    """GUI native-facing sources should not import the native layer."""
    repo_root = Path(__file__).resolve().parents[4]
    gui_root = repo_root / "gui" / "src" / "airunner"

    checked_paths = [
        gui_root / "distribution" / "__init__.py",
        gui_root / "distribution" / "bundle_layout.py",
        gui_root / "distribution" / "python_runtime_pins.py",
        gui_root / "linux_bundle_layout.py",
        gui_root / "launcher.py",
        gui_root / "bin" / "build_end_user_bundle.py",
        gui_root / "bin" / "airunner_headless.py",
        gui_root / "daemon_client" / "daemon_launcher.py",
    ]

    for path in checked_paths:
        source = path.read_text(encoding="utf-8")
        assert "from airunner_native" not in source, path.as_posix()
        assert "import airunner_native" not in source, path.as_posix()


def test_gui_runtime_support_modules_are_localized() -> None:
    """Localized GUI runtime support modules should not import model paths."""
    repo_root = Path(__file__).resolve().parents[4]
    runtime_root = repo_root / "gui" / "src" / "airunner" / "runtimes"

    for relative_path in (
        "__init__.py",
        "art_daemon_runtime_settings.py",
        "base.py",
        "bundled_runtime_paths.py",
        "llama_cpp_runtime_settings.py",
        "message_envelopes.py",
        "runtime_bind_host.py",
        "runtime_layout.py",
        "sidecar_launcher.py",
        "sidecar_art_client.py",
        "sidecar_llm_client.py",
        "sidecar_stt_client.py",
        "sidecar_stt_launcher.py",
        "sidecar_tts_client.py",
        "tts_daemon_runtime_settings.py",
        "whisper_cpp_runtime_settings.py",
    ):
        source = (runtime_root / relative_path).read_text(encoding="utf-8")
        assert "airunner_model.runtimes" not in source, relative_path
        assert "airunner_services.settings" not in source, relative_path


def test_gui_daemon_config_sources_avoid_service_config_imports() -> None:
    """GUI daemon config sources should avoid service config helpers."""
    repo_root = Path(__file__).resolve().parents[4]
    gui_root = repo_root / "gui" / "src" / "airunner"

    checked_paths = [
        gui_root / "daemon_config.py",
        gui_root / "daemon_client" / "daemon_launcher.py",
        gui_root / "daemon_client" / "gui_daemon_client.py",
        gui_root / "bin" / "airunner_headless.py",
    ]

    for path in checked_paths:
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.daemon_config" not in source, path.as_posix()
        assert (
            "airunner_services.config.runtime_layout" not in source
        ), path.as_posix()


def test_gui_headless_launch_sources_avoid_service_launch_imports() -> None:
    """GUI headless launch helpers should avoid direct service launch imports."""
    repo_root = Path(__file__).resolve().parents[4]
    gui_root = repo_root / "gui" / "src" / "airunner"

    checked_paths = [
        gui_root / "launcher.py",
        gui_root / "bin" / "airunner_headless.py",
    ]

    forbidden_imports = (
        "airunner_services.bin.airunner_headless",
        "airunner_services.daemon_client.launcher",
        "airunner_services.daemon_client.gui_daemon_client",
        "airunner_services.api.server",
        "airunner_services.utils.application",
        "airunner_model.setup_database",
    )

    for path in checked_paths:
        source = path.read_text(encoding="utf-8")
        for forbidden in forbidden_imports:
            assert forbidden not in source, path.as_posix()


def test_gui_logging_helper_sources_avoid_service_utility_imports() -> None:
    """GUI logging helpers should not import service utility modules directly."""
    repo_root = Path(__file__).resolve().parents[4]
    gui_root = repo_root / "gui" / "src" / "airunner"

    checked_paths = [
        gui_root / "utils" / "application" / "get_logger.py",
        gui_root / "utils" / "application" / "logging_utils.py",
        gui_root / "utils" / "application" / "log_hygiene.py",
    ]

    for path in checked_paths:
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.utils.application" not in source, (
            path.as_posix()
        )


def test_gui_generate_migration_source_avoids_service_package_import() -> None:
    """GUI migration tooling should locate service assets without importing the service package."""
    repo_root = Path(__file__).resolve().parents[4]
    source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "bin"
        / "generate_migration.py"
    ).read_text(encoding="utf-8")

    assert "import airunner_services" not in source


def test_gui_setup_database_source_avoids_service_setup_import() -> None:
    """GUI database setup should use local helpers instead of service setup."""
    repo_root = Path(__file__).resolve().parents[4]
    source = (
        repo_root / "gui" / "src" / "airunner" / "setup_database.py"
    ).read_text(encoding="utf-8")

    assert "airunner_api" not in source
    assert "airunner_model.setup_database" not in source
    assert "airunner.utils.db.engine" in source


def test_runtime_wrappers_expose_compatible_runtime_types() -> None:
    """Legacy GUI runtime imports should expose compatible runtime types."""
    from airunner.runtimes.art_daemon_runtime_settings import (
        ArtDaemonRuntimeSettings as LegacyArtDaemonRuntimeSettings,
    )
    from airunner.runtimes.sidecar_art_client import SidecarArtClient as LegacySidecarArtClient
    from airunner.runtimes.base import RuntimeClient as LegacyRuntimeClient
    from airunner.runtimes.llama_cpp_runtime_settings import LlamaCppRuntimeSettings as LegacyLlamaCppRuntimeSettings
    from airunner.runtimes.registry import RuntimeRegistry as LegacyRuntimeRegistry
    from airunner.runtimes.registry import RuntimeRoute as LegacyRuntimeRoute
    from airunner.runtimes.sidecar_llm_client import SidecarLLMClient as LegacySidecarLLMClient
    from airunner.runtimes.sidecar_launcher import SidecarLauncher as LegacySidecarLauncher
    from airunner.runtimes.sidecar_stt_client import SidecarSTTClient as LegacySidecarSTTClient
    from airunner.runtimes.sidecar_stt_launcher import SidecarSTTLauncher as LegacySidecarSTTLauncher
    from airunner.runtimes.sidecar_tts_client import SidecarTTSClient as LegacySidecarTTSClient
    from airunner.runtimes.tts_daemon_runtime_settings import TTSDaemonRuntimeSettings as LegacyTTSDaemonRuntimeSettings
    from airunner.runtimes.whisper_cpp_runtime_settings import WhisperCppRuntimeSettings as LegacyWhisperCppRuntimeSettings
    from airunner_services.runtimes.art_daemon_runtime_settings import (
        ArtDaemonRuntimeSettings,
    )
    from airunner_services.runtimes.sidecar_art_client import SidecarArtClient
    from airunner_services.runtimes.base import RuntimeClient
    from airunner_services.runtimes.llama_cpp_runtime_settings import LlamaCppRuntimeSettings
    from airunner_services.runtimes.registry import RuntimeRegistry
    from airunner_services.runtimes.registry import RuntimeRoute
    from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient
    from airunner_services.runtimes.sidecar_launcher import SidecarLauncher
    from airunner_services.runtimes.sidecar_stt_client import SidecarSTTClient
    from airunner_services.runtimes.sidecar_stt_launcher import SidecarSTTLauncher
    from airunner_services.runtimes.sidecar_tts_client import SidecarTTSClient
    from airunner_services.runtimes.tts_daemon_runtime_settings import TTSDaemonRuntimeSettings
    from airunner_services.runtimes.whisper_cpp_runtime_settings import WhisperCppRuntimeSettings

    assert (
        LegacyArtDaemonRuntimeSettings.__dataclass_fields__.keys()
        == ArtDaemonRuntimeSettings.__dataclass_fields__.keys()
    )
    assert LegacyLlamaCppRuntimeSettings.__name__ == LlamaCppRuntimeSettings.__name__
    assert (
        LegacyLlamaCppRuntimeSettings.__dataclass_fields__.keys()
        == LlamaCppRuntimeSettings.__dataclass_fields__.keys()
    )
    assert (
        LegacyWhisperCppRuntimeSettings.__dataclass_fields__.keys()
        == WhisperCppRuntimeSettings.__dataclass_fields__.keys()
    )
    assert LegacyRuntimeClient.__name__ == RuntimeClient.__name__
    assert LegacyRuntimeRegistry.__name__ == RuntimeRegistry.__name__
    assert LegacyRuntimeRoute.__name__ == RuntimeRoute.__name__
    assert LegacySidecarArtClient.__name__ == SidecarArtClient.__name__
    assert LegacySidecarLLMClient.__name__ == SidecarLLMClient.__name__
    assert LegacySidecarLauncher.__name__ == SidecarLauncher.__name__
    assert LegacySidecarSTTClient.__name__ == SidecarSTTClient.__name__
    assert LegacySidecarSTTLauncher.__name__ == SidecarSTTLauncher.__name__
    assert LegacySidecarTTSClient.__name__ == SidecarTTSClient.__name__
    assert (
        LegacyTTSDaemonRuntimeSettings.__dataclass_fields__.keys()
        == TTSDaemonRuntimeSettings.__dataclass_fields__.keys()
    )


def test_gui_llm_api_service_sources_avoid_service_llm_imports() -> None:
    """The GUI LLM API stack should not import service LLM helpers."""
    from pathlib import Path

    for path in (
        Path("gui/src/airunner/components/llm/api/__init__.py"),
        Path("gui/src/airunner/components/llm/api/chatbot_services.py"),
        Path("gui/src/airunner/components/llm/api/llm_services.py"),
        Path("gui/src/airunner/components/llm/api/llm_request_dispatch_mixin.py"),
        Path("gui/src/airunner/components/llm/api/llm_conversation_service_mixin.py"),
        Path("gui/src/airunner/components/llm/api/llm_daemon_stream_mixin.py"),
        Path("gui/src/airunner/components/llm/api/llm_unload_routing_mixin.py"),
        Path("gui/src/airunner/components/llm/utils/stream_text.py"),
        Path("gui/src/airunner/components/llm/utils/thinking_parser.py"),
    ):
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.api.services.llm_" not in source
        assert "airunner_services.llm.api" not in source
        assert "airunner_services.utils.application.api_reference" not in source
        assert "airunner_services.llm.stream_text" not in source
        assert "airunner_services.llm.thinking_parser" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_gui_user_model_is_localized() -> None:
    """The GUI user model should no longer wrap the service model."""
    from pathlib import Path

    from airunner.components.data.models.base import BaseModel as LegacyBaseModel
    from airunner.components.user.data.user import User as LegacyUser
    from airunner_model.models.user import User

    source = Path("gui/src/airunner/components/user/data/user.py").read_text(
        encoding="utf-8"
    )

    assert LegacyUser is not User
    assert LegacyUser.__module__ == "airunner.components.user.data.user"
    assert issubclass(LegacyUser, LegacyBaseModel)
    assert not issubclass(LegacyUser, User)
    assert "airunner_model.models.user" not in source
    assert "import_module" not in source
    assert "sys.modules[__name__]" not in source


def test_gui_tts_stt_api_services_follow_current_ownership() -> None:
    """Legacy GUI TTS/STT API imports should now be GUI-owned."""
    from airunner.components.stt.api.stt_services import (
        STTAPIService as LegacySTTAPIService,
    )
    from airunner.components.tts.api.tts_services import (
        TTSAPIService as LegacyTTSAPIService,
    )
    from airunner_services.api.services.stt_services import STTAPIService
    from airunner_services.api.services.tts_services import TTSAPIService

    assert LegacySTTAPIService is not STTAPIService
    assert LegacySTTAPIService.__module__ == (
        "airunner.components.stt.api.stt_services"
    )
    assert LegacyTTSAPIService is not TTSAPIService
    assert LegacyTTSAPIService.__module__ == (
        "airunner.components.tts.api.tts_services"
    )


def test_service_api_is_service_owned() -> None:
    """Service API imports should resolve to the service-owned app shell."""
    from airunner.components.application.api.api import API as LegacyAPI
    from airunner_services.api.api import API as ServiceAPI
    from airunner_services.app.service_app import ServiceApp

    assert ServiceAPI is not LegacyAPI
    assert issubclass(ServiceAPI, ServiceApp)


def test_legacy_settings_facade_reexports_shared_runtime_values() -> None:
    """Legacy GUI settings should reflect GUI-owned runtime configuration."""
    import os
    from pathlib import Path

    import airunner.settings as legacy_settings

    assert legacy_settings.AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR == (
        os.environ.get("AIRUNNER_DEFAULT_BRUSH_PRIMARY_COLOR", "#99C1F1")
    )
    assert legacy_settings.AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR == (
        os.environ.get("AIRUNNER_DEFAULT_BRUSH_SECONDARY_COLOR", "#000000")
    )
    assert legacy_settings.get_log_level_from_env.__module__ == (
        "airunner.settings"
    )
    assert legacy_settings.AIRUNNER_BASE_PATH
    assert legacy_settings.AIRUNNER_DB_URL
    assert legacy_settings.AIRUNNER_LOG_FILE.startswith(
        legacy_settings.AIRUNNER_BASE_PATH
    )
    assert legacy_settings.AIRUNNER_HEADLESS_SERVER_HOST
    assert isinstance(legacy_settings.AIRUNNER_HEADLESS_SERVER_PORT, int)
    assert isinstance(legacy_settings.AIRUNNER_LLM_ON, bool)
    assert isinstance(legacy_settings.AIRUNNER_LOCAL_FILES_ONLY, bool)
    assert legacy_settings.DEFAULT_HF_ENDPOINT == "https://huggingface.co"

    for path in (
        Path("gui/src/airunner/settings.py"),
        Path("gui/src/airunner/main.py"),
        Path("gui/src/airunner/app_mixins/headless_runtime_mixin.py"),
        Path("gui/src/airunner/database_bootstrap.py"),
        Path("gui/src/airunner/app_installer.py"),
        Path("gui/src/airunner/utils/settings/get_qsettings.py"),
        Path("gui/src/airunner/bin/airunner_headless.py"),
        Path(
            "gui/src/airunner/components/downloader/gui/windows/"
            "download_wizard/download_thread.py"
        ),
        Path(
            "gui/src/airunner/components/application/utils/"
            "download_helpers.py"
        ),
    ):
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.settings" not in source

    settings_source = Path("gui/src/airunner/settings.py").read_text(
        encoding="utf-8"
    )
    assert "airunner_services.contract_enums" not in settings_source


def test_contract_enums_share_identity_with_legacy_gui_enums() -> None:
    """Legacy GUI enums should reuse the GUI-local enum contract."""
    from pathlib import Path

    from airunner.enums import AvailableLanguage as LegacyAvailableLanguage
    from airunner.enums import CanvasToolName as LegacyCanvasToolName
    from airunner.enums import DEFAULT_ART_VERSION as legacy_default_art_version
    from airunner.enums import (
        DEFAULT_IMAGE_GENERATOR as legacy_default_image_generator,
    )
    from airunner.enums import EngineResponseCode as LegacyEngineResponseCode
    from airunner.enums import Gender as LegacyGender
    from airunner.enums import GeneratorSection as LegacyGeneratorSection
    from airunner.enums import ImageGenerator as LegacyImageGenerator
    from airunner.enums import LLMActionType as LegacyLLMActionType
    from airunner.enums import Mode as LegacyMode
    from airunner.enums import ModelService as LegacyModelService
    from airunner.enums import ModelStatus as LegacyModelStatus
    from airunner.enums import ModelType as LegacyModelType
    from airunner.enums import Scheduler as LegacyScheduler
    from airunner.enums import (
        StableDiffusionVersion as LegacyStableDiffusionVersion,
    )
    from airunner.enums import TTSModel as LegacyTTSModel
    from airunner.enums import normalize_art_version as legacy_normalize_art_version
    from airunner.enums import (
        normalize_image_generator_name as legacy_normalize_image_generator_name,
    )
    from airunner.contract_enums import AvailableLanguage
    from airunner.contract_enums import CanvasToolName
    from airunner.contract_enums import DEFAULT_ART_VERSION
    from airunner.contract_enums import DEFAULT_IMAGE_GENERATOR
    from airunner.contract_enums import EngineResponseCode
    from airunner.contract_enums import Gender
    from airunner.contract_enums import GeneratorSection
    from airunner.contract_enums import ImageGenerator
    from airunner.contract_enums import LLMActionType
    from airunner.contract_enums import Mode
    from airunner.contract_enums import ModelService
    from airunner.contract_enums import ModelStatus
    from airunner.contract_enums import ModelType
    from airunner.contract_enums import Scheduler
    from airunner.contract_enums import StableDiffusionVersion
    from airunner.contract_enums import TTSModel
    from airunner.contract_enums import normalize_art_version
    from airunner.contract_enums import normalize_image_generator_name

    assert LegacyAvailableLanguage is AvailableLanguage
    assert LegacyCanvasToolName is CanvasToolName
    assert legacy_default_art_version is DEFAULT_ART_VERSION
    assert legacy_default_image_generator is DEFAULT_IMAGE_GENERATOR
    assert LegacyEngineResponseCode is EngineResponseCode
    assert LegacyGender is Gender
    assert LegacyGeneratorSection is GeneratorSection
    assert LegacyImageGenerator is ImageGenerator
    assert LegacyLLMActionType is LLMActionType
    assert LegacyMode is Mode
    assert LegacyModelService is ModelService
    assert LegacyModelStatus is ModelStatus
    assert LegacyModelType is ModelType
    assert LegacyScheduler is Scheduler
    assert LegacyStableDiffusionVersion is StableDiffusionVersion
    assert LegacyTTSModel is TTSModel
    assert legacy_normalize_art_version is normalize_art_version
    assert legacy_normalize_image_generator_name is (
        normalize_image_generator_name
    )

    for path in (
        Path("gui/src/airunner/enums.py"),
        Path("gui/src/airunner/components/stt/api/stt_services.py"),
        Path("gui/src/airunner/components/tts/api/tts_services.py"),
        Path("gui/src/airunner/components/stt/api/tests/test_stt_services.py"),
        Path("gui/src/airunner/components/tts/api/tests/test_tts_services.py"),
        Path("gui/src/airunner/utils/application/tests/test_signal_mediator.py"),
    ):
        source = path.read_text(encoding="utf-8")
        assert "airunner_services.contract_enums" not in source


def test_legacy_gui_signal_codes_share_contract_values() -> None:
    """Legacy GUI SignalCode should preserve the local contract values."""
    from airunner.enums import SignalCode as LegacySignalCode
    from airunner.contract_enums import SignalCode as ContractSignalCode

    for contract_signal_code in ContractSignalCode:
        assert hasattr(LegacySignalCode, contract_signal_code.name)
        assert (
            getattr(LegacySignalCode, contract_signal_code.name).value
            == contract_signal_code.value
        )


def test_seed_model_wrappers_share_identity() -> None:
    """Seed-model imports should reflect current split ownership."""
    from airunner.components.application.data.shortcut_keys import (
        ShortcutKeys as LegacyShortcutKeys,
    )
    from airunner.components.art.data.controlnet_model import (
        ControlnetModel as LegacyControlnetModel,
    )
    from airunner.components.art.data.schedulers import (
        Schedulers as LegacySchedulers,
    )
    from airunner.components.llm.data.prompt_template import (
        PromptTemplate as LegacyPromptTemplate,
    )
    from airunner.components.models.data.pipeline_model import (
        PipelineModel as LegacyPipelineModel,
    )
    from airunner.components.settings.data.font_setting import (
        FontSetting as LegacyFontSetting,
    )
    from airunner_model.models.controlnet_model import (
        ControlnetModel,
    )
    from airunner_model.models.font_setting import FontSetting
    from airunner_model.models.pipeline_model import PipelineModel
    from airunner_model.models.prompt_template import (
        PromptTemplate,
    )
    from airunner_model.models.schedulers import Schedulers
    from airunner_model.models.shortcut_keys import ShortcutKeys

    assert LegacyControlnetModel is ControlnetModel
    assert LegacyFontSetting is not FontSetting
    assert LegacyPipelineModel is PipelineModel
    assert LegacyPromptTemplate is PromptTemplate
    assert LegacySchedulers is Schedulers
    assert LegacyShortcutKeys is not ShortcutKeys


def test_settings_models_share_identity_across_split_paths() -> None:
    """GUI settings imports should reflect current split ownership."""
    from airunner.components.art.data.ai_models import AIModels as LegacyAIModels
    from airunner.components.llm.data.llm_generator_settings import (
        LLMGeneratorSettings as LegacyLLMGeneratorSettings,
    )
    from airunner.components.settings.data.application_settings import (
        ApplicationSettings as LegacyApplicationSettings,
    )
    from airunner.components.settings.data.path_settings import (
        PathSettings as LegacyPathSettings,
    )
    from airunner_model.models.ai_models import AIModels
    from airunner_model.models.application_settings import (
        ApplicationSettings,
    )
    from airunner_model.models.llm_generator_settings import (
        LLMGeneratorSettings,
    )
    from airunner_model.models.path_settings import PathSettings

    assert LegacyAIModels is AIModels
    assert LegacyApplicationSettings is not ApplicationSettings
    assert LegacyLLMGeneratorSettings is LLMGeneratorSettings
    assert LegacyPathSettings is not PathSettings


def test_gui_application_settings_is_gui_owned() -> None:
    """Legacy GUI ApplicationSettings should now be GUI-owned."""
    from airunner.components.settings.data.application_settings import (
        ApplicationSettings as LegacyApplicationSettings,
    )
    from airunner_model.models.application_settings import (
        ApplicationSettings,
    )

    assert LegacyApplicationSettings is not ApplicationSettings
    assert LegacyApplicationSettings.__module__ == (
        "airunner.components.settings.data.application_settings"
    )


def test_gui_application_settings_source_avoids_service_model_import() -> None:
    """GUI ApplicationSettings should not import the service model directly."""
    repo_root = Path(__file__).resolve().parents[4]
    application_settings_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "settings"
        / "data"
        / "application_settings.py"
    ).read_text(encoding="utf-8")
    headless_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "app_mixins"
        / "headless_runtime_mixin.py"
    ).read_text(encoding="utf-8")

    assert "airunner_model.models.application_settings" not in (
        application_settings_source
    )
    assert (
        "from airunner_model.models.application_settings import"
        not in headless_source
    )


def test_gui_path_settings_is_gui_owned() -> None:
    """Legacy GUI PathSettings should now be GUI-owned."""
    from airunner.components.settings.data.path_settings import (
        PathSettings as LegacyPathSettings,
    )
    from airunner_model.models.path_settings import PathSettings

    assert LegacyPathSettings is not PathSettings
    assert LegacyPathSettings.__module__ == (
        "airunner.components.settings.data.path_settings"
    )


def test_gui_path_settings_source_avoids_service_model_import() -> None:
    """GUI PathSettings should not import the service model directly."""
    repo_root = Path(__file__).resolve().parents[4]
    path_settings_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "settings"
        / "data"
        / "path_settings.py"
    ).read_text(encoding="utf-8")

    assert "airunner_model.models.path_settings" not in (
        path_settings_source
    )


def test_conversation_models_share_identity_across_split_paths() -> None:
    """Legacy conversation ORM imports should resolve to service models."""
    from airunner.components.llm.data.chatbot import Chatbot as LegacyChatbot
    from airunner.components.llm.data.conversation import (
        Conversation as LegacyConversation,
    )
    from airunner.components.llm.data.summary import Summary as LegacySummary
    from airunner.components.user.data.user import User as LegacyUser
    from airunner_model.models.chatbot import Chatbot
    from airunner_model.models.conversation import Conversation
    from airunner_model.models.summary import Summary
    from airunner_model.models.user import User

    assert LegacyChatbot is Chatbot
    assert LegacyConversation is Conversation
    assert LegacySummary is Summary
    assert LegacyUser is User


def test_conversation_history_manager_wrapper_shares_identity() -> None:
    """Legacy conversation-manager imports should resolve to services."""
    from airunner.components.conversations.conversation_history_manager import (
        ConversationHistoryManager as LegacyConversationHistoryManager,
    )
    from airunner_services.conversations.conversation_history_manager import (
        ConversationHistoryManager,
    )

    assert LegacyConversationHistoryManager is ConversationHistoryManager


def test_provider_and_bootstrap_wrappers_share_identity() -> None:
    """Legacy provider/bootstrap imports should resolve to services."""
    from airunner.components.art.data.bootstrap.controlnet_bootstrap_data import (
        controlnet_bootstrap_data as legacy_controlnet_bootstrap_data,
    )
    from airunner.components.art.data.bootstrap.imagefilter_bootstrap_data import (
        imagefilter_bootstrap_data as legacy_imagefilter_bootstrap_data,
    )
    from airunner.components.art.data.bootstrap.rmbg_bootstrap_data import (
        RMBG_FILES as legacy_rmbg_files,
    )
    from airunner.components.art.data.bootstrap.sd_file_bootstrap_data import (
        SD_FILE_BOOTSTRAP_DATA as legacy_sd_file_bootstrap_data,
    )
    from airunner.components.data.bootstrap.pipeline_bootstrap_data import (
        pipeline_bootstrap_data as legacy_pipeline_bootstrap_data,
    )
    from airunner.components.data.bootstrap.unified_model_files import (
        UNIFIED_MODEL_FILES as legacy_unified_model_files,
    )
    from airunner.components.data.bootstrap.unified_model_files import (
        get_required_files_for_model as legacy_get_required_files_for_model,
    )
    from airunner.components.data.bootstrap.model_bootstrap_data import (
        ai_art_models as legacy_ai_art_models,
    )
    from airunner.components.data.bootstrap.model_bootstrap_data import (
        llm_models as legacy_llm_models,
    )
    from airunner.components.llm.data.bootstrap.llm_file_bootstrap_data import (
        LLM_FILE_BOOTSTRAP_DATA as legacy_llm_file_bootstrap_data,
    )
    from airunner.components.llm.data.bootstrap.prompt_templates_bootstrap_data import (
        prompt_templates_bootstrap_data as legacy_prompt_templates_bootstrap_data,
    )
    from airunner.components.settings.data.bootstrap.font_settings_bootstrap_data import (
        font_settings_bootstrap_data as legacy_font_settings_bootstrap_data,
    )
    from airunner.components.stt.data.bootstrap.whisper import (
        WHISPER_FILES as legacy_whisper_files,
    )
    from airunner.components.tts.data.bootstrap.openvoice_bootstrap_data import (
        OPENVOICE_FILES as legacy_openvoice_files,
    )
    from airunner.components.tts.data.bootstrap.openvoice_languages import (
        OPENVOICE_CORE_MODELS as legacy_openvoice_core_models,
    )
    from airunner.components.tts.data.bootstrap.openvoice_languages import (
        OPENVOICE_LANGUAGE_MODELS as legacy_openvoice_language_models,
    )
    from airunner.components.tts.data.bootstrap.openvoice_languages import (
        get_models_for_languages as legacy_get_models_for_languages,
    )
    from airunner_services.bootstrap.controlnet_bootstrap_data import (
        controlnet_bootstrap_data,
    )
    from airunner_services.bootstrap.font_settings_bootstrap_data import (
        font_settings_bootstrap_data,
    )
    from airunner_services.bootstrap.imagefilter_bootstrap_data import (
        imagefilter_bootstrap_data,
    )
    from airunner_services.bootstrap.llm_file_bootstrap_data import (
        LLM_FILE_BOOTSTRAP_DATA,
    )
    from airunner_services.bootstrap.model_bootstrap_data import ai_art_models
    from airunner_services.bootstrap.model_bootstrap_data import llm_models
    from airunner_services.bootstrap.openvoice_bootstrap_data import (
        OPENVOICE_FILES,
    )
    from airunner_services.bootstrap.pipeline_bootstrap_data import (
        pipeline_bootstrap_data,
    )
    from airunner_services.bootstrap.prompt_templates_bootstrap_data import (
        prompt_templates_bootstrap_data,
    )
    from airunner_services.bootstrap.rmbg_bootstrap_data import RMBG_FILES
    from airunner_services.bootstrap.sd_file_bootstrap_data import (
        SD_FILE_BOOTSTRAP_DATA,
    )
    from airunner_services.bootstrap.unified_model_files import (
        UNIFIED_MODEL_FILES,
    )
    from airunner_services.bootstrap.unified_model_files import (
        get_required_files_for_model,
    )
    from airunner_services.bootstrap.whisper import WHISPER_FILES
    from airunner_services.bootstrap.openvoice_languages import (
        OPENVOICE_CORE_MODELS,
    )
    from airunner_services.bootstrap.openvoice_languages import (
        OPENVOICE_LANGUAGE_MODELS,
    )
    from airunner_services.bootstrap.openvoice_languages import (
        get_models_for_languages,
    )
    assert legacy_controlnet_bootstrap_data == controlnet_bootstrap_data
    assert legacy_controlnet_bootstrap_data is not controlnet_bootstrap_data
    assert legacy_font_settings_bootstrap_data == font_settings_bootstrap_data
    assert legacy_font_settings_bootstrap_data is not font_settings_bootstrap_data
    assert legacy_imagefilter_bootstrap_data == imagefilter_bootstrap_data
    assert legacy_imagefilter_bootstrap_data is not imagefilter_bootstrap_data
    assert legacy_ai_art_models == ai_art_models
    assert legacy_ai_art_models is not ai_art_models
    assert legacy_get_required_files_for_model is not get_required_files_for_model
    assert legacy_get_required_files_for_model(
        "stt",
        "ggerganov/whisper.cpp",
    ) == get_required_files_for_model(
        "stt",
        "ggerganov/whisper.cpp",
    )
    assert legacy_llm_file_bootstrap_data == LLM_FILE_BOOTSTRAP_DATA
    assert legacy_llm_file_bootstrap_data is not LLM_FILE_BOOTSTRAP_DATA
    assert legacy_llm_models == llm_models
    assert legacy_llm_models is not llm_models
    assert legacy_openvoice_files == OPENVOICE_FILES
    assert legacy_openvoice_files is not OPENVOICE_FILES
    assert legacy_openvoice_core_models == OPENVOICE_CORE_MODELS
    assert legacy_openvoice_core_models is not OPENVOICE_CORE_MODELS
    assert legacy_openvoice_language_models == OPENVOICE_LANGUAGE_MODELS
    assert legacy_openvoice_language_models is not OPENVOICE_LANGUAGE_MODELS
    assert legacy_get_models_for_languages is not get_models_for_languages
    assert legacy_get_models_for_languages(["French", "Korean"]) == (
        get_models_for_languages(["French", "Korean"])
    )
    assert legacy_pipeline_bootstrap_data == pipeline_bootstrap_data
    assert legacy_pipeline_bootstrap_data is not pipeline_bootstrap_data
    assert legacy_prompt_templates_bootstrap_data == (
        prompt_templates_bootstrap_data
    )
    assert legacy_prompt_templates_bootstrap_data is not (
        prompt_templates_bootstrap_data
    )
    assert legacy_rmbg_files == RMBG_FILES
    assert legacy_rmbg_files is not RMBG_FILES
    assert legacy_sd_file_bootstrap_data == SD_FILE_BOOTSTRAP_DATA
    assert legacy_sd_file_bootstrap_data is not SD_FILE_BOOTSTRAP_DATA
    assert legacy_unified_model_files == UNIFIED_MODEL_FILES
    assert legacy_unified_model_files is not UNIFIED_MODEL_FILES
    assert legacy_whisper_files == WHISPER_FILES
    assert legacy_whisper_files is not WHISPER_FILES


def test_gui_bootstrap_seed_sources_avoid_service_imports() -> None:
    """GUI bootstrap seed modules should not import service/shared owners."""
    repo_root = Path(__file__).resolve().parents[4]
    bootstrap_root = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
    )
    model_source = (
        bootstrap_root
        / "data"
        / "bootstrap"
        / "model_bootstrap_data.py"
    ).read_text(encoding="utf-8")
    pipeline_source = (
        bootstrap_root
        / "data"
        / "bootstrap"
        / "pipeline_bootstrap_data.py"
    ).read_text(encoding="utf-8")
    unified_source = (
        bootstrap_root
        / "data"
        / "bootstrap"
        / "unified_model_files.py"
    ).read_text(encoding="utf-8")
    llm_files_source = (
        bootstrap_root
        / "llm"
        / "data"
        / "bootstrap"
        / "llm_file_bootstrap_data.py"
    ).read_text(encoding="utf-8")
    prompt_templates_source = (
        bootstrap_root
        / "llm"
        / "data"
        / "bootstrap"
        / "prompt_templates_bootstrap_data.py"
    ).read_text(encoding="utf-8")
    llm_bootstrap_init_source = (
        bootstrap_root
        / "llm"
        / "data"
        / "bootstrap"
        / "__init__.py"
    ).read_text(encoding="utf-8")
    llm_package_source = (
        bootstrap_root / "llm" / "__init__.py"
    ).read_text(encoding="utf-8")
    llm_data_package_source = (
        bootstrap_root / "llm" / "data" / "__init__.py"
    ).read_text(encoding="utf-8")
    rmbg_source = (
        bootstrap_root
        / "art"
        / "data"
        / "bootstrap"
        / "rmbg_bootstrap_data.py"
    ).read_text(encoding="utf-8")
    controlnet_source = (
        bootstrap_root
        / "art"
        / "data"
        / "bootstrap"
        / "controlnet_bootstrap_data.py"
    ).read_text(encoding="utf-8")
    imagefilter_source = (
        bootstrap_root
        / "art"
        / "data"
        / "bootstrap"
        / "imagefilter_bootstrap_data.py"
    ).read_text(encoding="utf-8")
    sd_source = (
        bootstrap_root
        / "art"
        / "data"
        / "bootstrap"
        / "sd_file_bootstrap_data.py"
    ).read_text(encoding="utf-8")
    whisper_source = (
        bootstrap_root
        / "stt"
        / "data"
        / "bootstrap"
        / "whisper.py"
    ).read_text(encoding="utf-8")
    openvoice_bootstrap_source = (
        bootstrap_root
        / "tts"
        / "data"
        / "bootstrap"
        / "openvoice_bootstrap_data.py"
    ).read_text(encoding="utf-8")
    openvoice_languages_source = (
        bootstrap_root
        / "tts"
        / "data"
        / "bootstrap"
        / "openvoice_languages.py"
    ).read_text(encoding="utf-8")
    font_source = (
        bootstrap_root
        / "settings"
        / "data"
        / "bootstrap"
        / "font_settings_bootstrap_data.py"
    ).read_text(encoding="utf-8")

    assert "airunner_services.bootstrap.model_bootstrap_data" not in (
        model_source
    )
    assert "airunner_services.settings" not in model_source
    assert "airunner_services.bootstrap.pipeline_bootstrap_data" not in (
        pipeline_source
    )
    assert "airunner_services.settings" not in pipeline_source
    assert "airunner_services.bootstrap.unified_model_files" not in (
        unified_source
    )
    assert "airunner_services.bootstrap.llm_file_bootstrap_data" not in (
        llm_files_source
    )
    assert "airunner_services.bootstrap.prompt_templates_bootstrap_data" not in (
        prompt_templates_source
    )
    assert "airunner_model.models.bootstrap" not in (
        llm_bootstrap_init_source
    )
    assert "airunner_services.llm.__init__" not in llm_package_source
    assert "airunner_services.llm.data" not in llm_data_package_source
    assert "airunner_services.settings" not in prompt_templates_source
    assert "airunner_services.bootstrap.controlnet_bootstrap_data" not in (
        controlnet_source
    )
    assert "airunner_services.settings" not in controlnet_source
    assert "airunner_services.bootstrap.imagefilter_bootstrap_data" not in (
        imagefilter_source
    )
    assert "airunner_services.settings" not in imagefilter_source
    assert "airunner_services.bootstrap.rmbg_bootstrap_data" not in (
        rmbg_source
    )
    assert "airunner_services.bootstrap.sd_file_bootstrap_data" not in (
        sd_source
    )
    assert "airunner_services.settings" not in sd_source
    assert "airunner_services.bootstrap.whisper" not in whisper_source
    assert "airunner_services.settings" not in whisper_source
    assert "airunner_services.bootstrap.openvoice_bootstrap_data" not in (
        openvoice_bootstrap_source
    )
    assert "airunner_services.bootstrap.openvoice_languages" not in (
        openvoice_languages_source
    )
    assert "airunner_services.bootstrap.font_settings_bootstrap_data" not in (
        font_source
    )


def test_provider_config_surfaces_compatible_lookup_behavior() -> None:
    """GUI and services provider config surfaces should stay compatible."""
    from airunner.components.llm.config.provider_config import LLMProviderConfig
    from airunner_services.llm.provider_config import (
        LLMProviderConfig as ServicesLLMProviderConfig,
    )

    assert (
        LLMProviderConfig.resolve_model_id("local", "Qwen 3.5 9B")
        == ServicesLLMProviderConfig.resolve_model_id(
            "local",
            "Qwen 3.5 9B",
        )
    )
    assert LLMProviderConfig.get_model_info(
        "local",
        "gpt-oss-20b",
    ) == ServicesLLMProviderConfig.get_model_info(
        "local",
        "gpt-oss-20b",
    )
    assert LLMProviderConfig.get_expected_local_artifact_path(
        "/tmp/airunner-base",
        "local",
        model_id="qwen3-8b",
    ) == ServicesLLMProviderConfig.get_expected_local_artifact_path(
        "/tmp/airunner-base",
        "local",
        model_id="qwen3-8b",
    )


def test_generator_settings_and_tenant_wrappers_share_identity() -> None:
    """Legacy art settings and tenant helpers should resolve to services."""
    from airunner.components.art.data.generator_settings import (
        GeneratorSettings as LegacyGeneratorSettings,
    )
    from airunner.components.data import tenant as legacy_tenant
    from airunner_services.data import tenant
    from airunner_model.models.generator_settings import (
        GeneratorSettings,
    )

    assert LegacyGeneratorSettings is GeneratorSettings
    assert legacy_tenant.set_tenant_key is tenant.set_tenant_key
    assert legacy_tenant.reset_tenant_key is tenant.reset_tenant_key


def test_tts_request_wrappers_follow_current_ownership() -> None:
    """Localized TTS request dataclasses should stay GUI-owned."""
    from airunner.components.tts.managers.tts_request import (
        OpenVoiceTTSRequest as LegacyOpenVoiceTTSRequest,
    )
    from airunner_services.requests.tts_request import OpenVoiceTTSRequest

    assert LegacyOpenVoiceTTSRequest is not OpenVoiceTTSRequest
    assert LegacyOpenVoiceTTSRequest.__module__ == (
        "airunner.components.tts.managers.tts_request"
    )


def test_web_tools_wrapper_shares_identity() -> None:
    """Legacy LLM web-tool imports should resolve to services."""
    from airunner.components.llm.tools.web_tools import (
        scrape_website as legacy_scrape_website,
    )
    from airunner.components.llm.tools.web_tools import (
        search_news as legacy_search_news,
    )
    from airunner.components.llm.tools.web_tools import (
        search_web as legacy_search_web,
    )
    from airunner_services.tools.web_tools import scrape_website
    from airunner_services.tools.web_tools import search_news, search_web

    assert legacy_search_web is search_web
    assert search_web.__module__ == "airunner_services.tools.web_tools"
    assert legacy_search_news is search_news
    assert search_news.__module__ == "airunner_services.tools.web_tools"
    assert legacy_scrape_website is scrape_website
    assert scrape_website.__module__ == "airunner_services.tools.web_tools"


def test_download_routes_wrapper_shares_identity() -> None:
    """Legacy download route imports should resolve to services."""
    from airunner_api.routes import downloads as legacy_download_routes
    from airunner_services.api.routes import downloads as download_routes

    assert (
        legacy_download_routes.start_huggingface_download
        is download_routes.start_huggingface_download
    )


def test_tools_runtime_wrappers_follow_current_ownership() -> None:
    """Legacy pure tools imports should reflect current ownership."""
    from airunner.components.tools.base_tool import BaseTool as LegacyBaseTool
    from airunner.components.tools.scrapy import (
        LLMGuidedSpider as LegacyLLMGuidedSpider,
    )
    from airunner.components.tools.scrapy.llm_crawler_controller import (
        LLMCrawlerController as LegacyLLMCrawlerController,
    )
    from airunner.components.tools.search_providers import (
        DuckDuckGoProvider as LegacyDuckDuckGoProvider,
    )
    from airunner.components.tools.search_tool import (
        AggregatedSearchTool as LegacyAggregatedSearchTool,
    )
    from airunner.components.tools.url_safety import (
        validate_url_for_fetch as legacy_validate_url_for_fetch,
    )
    from airunner.components.tools.web_content_extractor import (
        WebContentExtractor as LegacyWebContentExtractor,
    )
    from airunner_services.tools.base_tool import BaseTool
    from airunner_services.tools.scrapy import LLMGuidedSpider
    from airunner_services.tools.scrapy.llm_crawler_controller import (
        LLMCrawlerController,
    )
    from airunner_services.tools.search_providers import DuckDuckGoProvider
    from airunner_services.tools.search_tool import AggregatedSearchTool
    from airunner_services.tools.url_safety import validate_url_for_fetch
    from airunner_services.tools.web_content_extractor import (
        WebContentExtractor,
    )

    assert LegacyBaseTool is BaseTool
    assert LegacyLLMGuidedSpider is LLMGuidedSpider
    assert LegacyLLMCrawlerController is LLMCrawlerController
    assert LegacyDuckDuckGoProvider is DuckDuckGoProvider
    assert LegacyAggregatedSearchTool is AggregatedSearchTool
    assert legacy_validate_url_for_fetch is not validate_url_for_fetch
    assert LegacyWebContentExtractor is WebContentExtractor


def test_scan_and_persistence_wrappers_follow_current_ownership() -> None:
    """Legacy GUI scan/persistence helpers should resolve per ownership."""
    from airunner.components.application.utils.model_persistence import (
        persist_trigger_words as legacy_persist_trigger_words,
    )
    from airunner.components.application.workers.model_scanner_worker import (
        ModelScannerWorker as LegacyModelScannerWorker,
    )
    from airunner.components.documents.data.scan_zimfiles import (
        scan_zimfiles as legacy_scan_zimfiles,
    )
    from airunner_services.documents.scan_zimfiles import scan_zimfiles
    from airunner_services.model_management.model_persistence import (
        persist_trigger_words,
    )
    from airunner_services.workers.model_scanner_worker import (
        ModelScannerWorker,
    )

    assert LegacyModelScannerWorker is ModelScannerWorker
    assert legacy_persist_trigger_words is persist_trigger_words
    assert legacy_scan_zimfiles is not scan_zimfiles


def test_stale_worker_wrappers_share_identity() -> None:
    """Legacy GUI worker residue should proxy service-owned modules."""
    from airunner.components.application.workers.base_download_worker import (
        BaseDownloadWorker as LegacyBaseDownloadWorker,
    )
    from airunner.components.application.workers.huggingface_download_worker import (
        HuggingFaceDownloadWorker as LegacyHuggingFaceDownloadWorker,
    )
    from airunner.components.art.workers.safety_checker_worker import (
        SafetyCheckerWorker as LegacySafetyCheckerWorker,
    )
    from airunner_services.downloads.base_download_worker import (
        BaseDownloadWorker,
    )
    from airunner_services.downloads.huggingface_download_worker import (
        HuggingFaceDownloadWorker,
    )
    from airunner_services.workers.safety_checker_worker import (
        SafetyCheckerWorker,
    )

    assert LegacyBaseDownloadWorker is BaseDownloadWorker
    assert LegacyHuggingFaceDownloadWorker is HuggingFaceDownloadWorker
    assert LegacySafetyCheckerWorker is SafetyCheckerWorker


def test_audio_processor_worker_wrapper_shares_identity() -> None:
    """Legacy STT worker imports should resolve to services."""
    from airunner.components.stt.workers.audio_processor_worker import (
        AudioProcessorWorker as LegacyAudioProcessorWorker,
    )
    from airunner_services.workers.audio_processor_worker import (
        AudioProcessorWorker,
    )

    assert LegacyAudioProcessorWorker is AudioProcessorWorker
    assert AudioProcessorWorker.__module__ == (
        "airunner_services.workers.audio_processor_worker"
    )


def test_image_export_worker_wrapper_shares_identity() -> None:
    """Legacy art export worker imports should resolve to services."""
    from airunner.components.art.workers.image_export_worker import (
        ImageExportWorker as LegacyImageExportWorker,
    )
    from airunner_services.workers.image_export_worker import ImageExportWorker

    assert LegacyImageExportWorker is ImageExportWorker
    assert ImageExportWorker.__module__ == (
        "airunner_services.workers.image_export_worker"
    )


def test_sd_worker_wrapper_shares_identity() -> None:
    """Legacy art worker imports should resolve to services."""
    from airunner.components.art.workers.sd_worker import (
        SDWorker as LegacySDWorker,
    )
    from airunner_services.workers.sd_worker import SDWorker

    assert LegacySDWorker is SDWorker
    assert SDWorker.__module__ == "airunner_services.workers.sd_worker"


def test_sd_worker_uses_service_worker_base() -> None:
    """Service SD worker should inherit the service worker base."""
    from airunner_services.workers.sd_worker import SDWorker
    from airunner_services.workers.worker import Worker

    assert issubclass(SDWorker, Worker)


def test_art_model_manager_wrappers_share_identity() -> None:
    """Legacy art model-manager imports should resolve to services."""
    from airunner_services.model_management.sdxl_model_manager import (
        SDXLModelManager as LegacySDXLModelManager
    )
    from airunner_services.model_management.x4_upscale_manager import (
        X4UpscaleManager as LegacyX4UpscaleManager,
    )
    from airunner_services.model_management.zimage_model_manager import (
        ZImageModelManager as LegacyZImageModelManager,
    )
    from airunner_services.model_management.sdxl_model_manager import (
        SDXLModelManager,
    )
    from airunner_services.model_management.x4_upscale_manager import (
        X4UpscaleManager,
    )
    from airunner_services.model_management.zimage_model_manager import (
        ZImageModelManager,
    )

    assert LegacySDXLModelManager is SDXLModelManager
    assert SDXLModelManager.__module__ == (
        "airunner_services.model_management.sdxl_model_manager"
    )
    assert LegacyX4UpscaleManager is X4UpscaleManager
    assert X4UpscaleManager.__module__ == (
        "airunner_services.model_management.x4_upscale_manager"
    )
    assert LegacyZImageModelManager is ZImageModelManager
    assert ZImageModelManager.__module__ == (
        "airunner_services.model_management.zimage_model_manager"
    )


def test_art_support_wrappers_share_identity() -> None:
    """Legacy art support-module imports should resolve to services."""
    from importlib import import_module

    module_pairs = (
        (
            "airunner.components.art.managers.stablediffusion."
            "base_diffusers_model_manager",
            "airunner_services.art.managers.stablediffusion."
            "base_diffusers_model_manager",
        ),
        (
            "airunner.components.art.managers.stablediffusion.prompt_utils",
            "airunner_services.art.managers.stablediffusion.prompt_utils",
        ),
    )

    for legacy_module_name, service_module_name in module_pairs:
        assert import_module(legacy_module_name) is import_module(
            service_module_name
        )


def test_art_scheduler_wrappers_follow_current_ownership() -> None:
    """Localized art scheduler modules should stay GUI-owned."""
    from airunner.components.art.schedulers.flow_match_scheduler_factory import (
        create_flow_match_scheduler as legacy_create_flow_match_scheduler,
    )
    from airunner_services.art.schedulers.flow_match_scheduler_factory import (
        create_flow_match_scheduler,
    )

    assert legacy_create_flow_match_scheduler is not create_flow_match_scheduler
    assert legacy_create_flow_match_scheduler.__module__ == (
        "airunner.components.art.schedulers.flow_match_scheduler_factory"
    )


def test_art_scheduler_sources_avoid_service_imports() -> None:
    """Localized art scheduler modules should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/components/art/schedulers/__init__.py"),
        Path(
            "gui/src/airunner/components/art/schedulers/"
            "flow_match_scheduler_factory.py"
        ),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_art_config_wrappers_follow_current_ownership() -> None:
    """Localized art config modules should stay GUI-owned."""
    from airunner.components.art.config.image_generator_capabilities import (
        get_generator_capabilities as legacy_get_generator_capabilities,
    )
    from airunner_services.art.config.image_generator_capabilities import (
        get_generator_capabilities,
    )

    assert legacy_get_generator_capabilities is not get_generator_capabilities
    assert legacy_get_generator_capabilities.__module__ == (
        "airunner.components.art.config.image_generator_capabilities"
    )


def test_art_config_sources_avoid_service_imports() -> None:
    """Localized art config modules should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/components/art/config/__init__.py"),
        Path(
            "gui/src/airunner/components/art/config/"
            "image_generator_capabilities.py"
        ),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_art_utility_wrappers_follow_current_ownership() -> None:
    """Localized art utility modules should stay GUI-owned."""
    from airunner.components.art.utils.model_file_checker import (
        ModelFileChecker as LegacyModelFileChecker,
    )
    from airunner.components.art.utils.nsfw_checker import (
        check_and_mark_nsfw_images as legacy_check_and_mark_nsfw_images,
    )
    from airunner_services.art.utils.model_file_checker import ModelFileChecker
    from airunner_services.art.utils.nsfw_checker import (
        check_and_mark_nsfw_images,
    )

    assert LegacyModelFileChecker is not ModelFileChecker
    assert LegacyModelFileChecker.__module__ == (
        "airunner.components.art.utils.model_file_checker"
    )
    assert legacy_check_and_mark_nsfw_images is not check_and_mark_nsfw_images
    assert legacy_check_and_mark_nsfw_images.__module__ == (
        "airunner.components.art.utils.nsfw_checker"
    )


def test_art_utility_sources_avoid_service_imports() -> None:
    """Localized art utility helpers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/components/art/utils/__init__.py"),
        Path("gui/src/airunner/components/art/utils/model_file_checker.py"),
        Path("gui/src/airunner/components/art/utils/nsfw_checker.py"),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_tts_generator_worker_wrapper_shares_identity() -> None:
    """Legacy TTS worker imports should resolve to services."""
    from airunner.components.tts.workers.tts_generator_worker import (
        TTSGeneratorWorker as LegacyTTSGeneratorWorker,
    )
    from airunner_services.workers.tts_generator_worker import (
        TTSGeneratorWorker,
    )

    assert LegacyTTSGeneratorWorker is TTSGeneratorWorker
    assert TTSGeneratorWorker.__module__ == (
        "airunner_services.workers.tts_generator_worker"
    )


def test_tts_support_wrappers_follow_current_ownership() -> None:
    """Localized TTS support modules should stay GUI-owned."""
    from airunner.components.tts.managers.exceptions import (
        FileMissing as LegacyFileMissing,
    )
    from airunner_services.runtimes.openvoice_exceptions import FileMissing

    assert LegacyFileMissing is not FileMissing
    assert LegacyFileMissing.__module__ == (
        "airunner.components.tts.managers.exceptions"
    )


def test_tts_support_sources_avoid_service_imports() -> None:
    """Localized TTS support modules should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "tts"
        / "managers"
        / "exceptions.py"
    ).read_text(encoding="utf-8")

    assert "airunner_services" not in source
    assert "import_module" not in source
    assert "sys.modules[__name__]" not in source


def test_stt_tts_runtime_wrappers_follow_current_ownership() -> None:
    """Legacy STT/TTS runtime managers should match current ownership."""
    from airunner.components.stt.executors.stt_executor import (
        STTExecutor as LegacySTTExecutor,
    )
    from airunner.components.tts.managers.espeak_model_manager import (
        EspeakModelManager as LegacyEspeakModelManager,
    )
    from airunner.components.tts.managers.openvoice_model_manager import (
        OpenVoiceModelManager as LegacyOpenVoiceModelManager,
    )
    from airunner.components.tts.managers.tts_model_manager import (
        TTSModelManager as LegacyTTSModelManager,
    )
    from airunner_services.runtimes.espeak_model_manager import (
        EspeakModelManager,
    )
    from airunner_services.runtimes.openvoice_model_manager import (
        OpenVoiceModelManager,
    )
    from airunner_services.runtimes.stt_executor import STTExecutor
    from airunner_services.runtimes.tts_model_manager import TTSModelManager

    assert LegacyEspeakModelManager is not EspeakModelManager
    assert LegacyOpenVoiceModelManager is OpenVoiceModelManager
    assert LegacySTTExecutor is STTExecutor
    assert LegacyTTSModelManager is not TTSModelManager


def test_tts_runtime_manager_sources_avoid_service_imports() -> None:
    """Localized TTS runtime managers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/components/tts/managers/tts_model_manager.py"),
        Path(
            "gui/src/airunner/components/tts/managers/"
            "espeak_model_manager.py"
        ),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_knowledge_base_is_gui_owned() -> None:
    """Legacy knowledge-base imports should now be GUI-owned."""
    from airunner.components.knowledge.knowledge_base import (
        KNOWLEDGE_DIR as legacy_knowledge_dir,
    )
    from airunner.components.knowledge.knowledge_base import (
        KnowledgeBase as LegacyKnowledgeBase,
    )
    from airunner.components.knowledge.knowledge_base import (
        get_knowledge_base as legacy_get_knowledge_base,
    )
    from airunner_services.knowledge import KNOWLEDGE_DIR
    from airunner_services.knowledge import KnowledgeBase, get_knowledge_base

    assert legacy_knowledge_dir == KNOWLEDGE_DIR
    assert LegacyKnowledgeBase is not KnowledgeBase
    assert legacy_get_knowledge_base is not get_knowledge_base
    assert LegacyKnowledgeBase.__module__ == (
        "airunner.components.knowledge.knowledge_base"
    )


def test_gui_knowledge_and_tenant_sources_avoid_service_imports() -> None:
    """GUI knowledge helpers should not import service modules directly."""
    repo_root = Path(__file__).resolve().parents[4]
    knowledge_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "knowledge"
        / "knowledge_base.py"
    ).read_text(encoding="utf-8")
    tenant_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "data"
        / "tenant.py"
    ).read_text(encoding="utf-8")
    headless_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "app_mixins"
        / "headless_runtime_mixin.py"
    ).read_text(encoding="utf-8")

    assert "airunner_services.knowledge" not in knowledge_source
    assert "airunner_services.data.tenant" not in tenant_source
    assert "from airunner_services.knowledge import" not in headless_source


def test_llm_model_manager_wrapper_shares_identity() -> None:
    """Legacy LLM model-manager imports should resolve to services."""
    from airunner.components.llm.managers.llm_model_manager import (
        LLMModelManager as LegacyLLMModelManager,
    )
    from airunner_services.model_management.llm_model_manager import (
        LLMModelManager,
    )

    assert LegacyLLMModelManager is LLMModelManager
    assert LLMModelManager.__module__ == (
        "airunner_services.model_management.llm_model_manager"
    )


def test_llm_manager_dependency_wrappers_share_identity() -> None:
    """Legacy LLM manager support modules should resolve to services."""
    from airunner.components.llm.managers.agent.rag_mixin import (
        RAGMixin as LegacyRAGMixin,
    )
    from airunner.components.llm.managers.llm_settings import (
        LLMSettings as LegacyLLMSettings,
    )
    from airunner.components.llm.managers.quantization_mixin import (
        QuantizationMixin as LegacyQuantizationMixin,
    )
    from airunner.components.llm.managers.tool_manager import (
        ToolManager as LegacyToolManager,
    )
    from airunner.components.llm.managers.workflow_manager import (
        WorkflowManager as LegacyWorkflowManager,
    )
    from airunner_services.llm.llm_settings import LLMSettings
    from airunner_services.llm.quantization_mixin import QuantizationMixin
    from airunner_services.llm.rag_mixin import RAGMixin
    from airunner_services.llm.tool_manager import ToolManager
    from airunner_services.llm.workflow_manager import WorkflowManager

    assert LegacyLLMSettings is LLMSettings
    assert LLMSettings.__module__ == "airunner_services.llm.llm_settings"
    assert LegacyRAGMixin is RAGMixin
    assert RAGMixin.__module__ == "airunner_services.llm.rag_mixin"
    assert LegacyQuantizationMixin is QuantizationMixin
    assert QuantizationMixin.__module__ == (
        "airunner_services.llm.quantization_mixin"
    )
    assert LegacyToolManager is ToolManager
    assert ToolManager.__module__ == "airunner_services.llm.tool_manager"
    assert LegacyWorkflowManager is WorkflowManager
    assert WorkflowManager.__module__ == (
        "airunner_services.llm.workflow_manager"
    )


def test_llm_generate_worker_wrapper_shares_identity() -> None:
    """Legacy LLM worker imports should resolve to services."""
    from airunner.components.llm.workers.llm_generate_worker import (
        LLMGenerateWorker as LegacyLLMGenerateWorker,
    )
    from airunner_services.workers.llm_generate_worker import (
        LLMGenerateWorker,
    )

    assert LegacyLLMGenerateWorker is LLMGenerateWorker
    assert LLMGenerateWorker.__module__ == (
        "airunner_services.workers.llm_generate_worker"
    )


def test_llm_worker_mixin_wrappers_share_identity() -> None:
    """Legacy LLM worker mixin imports should resolve to services."""
    from airunner.components.llm.workers.mixins.model_download_mixin import (
        ModelDownloadMixin as LegacyModelDownloadMixin,
    )
    from airunner.components.llm.workers.mixins.quantization_mixin import (
        QuantizationMixin as LegacyQuantizationMixin,
    )
    from airunner.components.llm.workers.mixins.rag_indexing_mixin import (
        RAGIndexingMixin as LegacyRAGIndexingMixin,
    )
    from airunner_services.llm.workers.mixins.model_download_mixin import (
        ModelDownloadMixin,
    )
    from airunner_services.llm.workers.mixins.quantization_mixin import (
        QuantizationMixin,
    )
    from airunner_services.llm.workers.mixins.rag_indexing_mixin import (
        RAGIndexingMixin,
    )

    assert LegacyModelDownloadMixin is ModelDownloadMixin
    assert ModelDownloadMixin.__module__ == (
        "airunner_services.llm.workers.mixins.model_download_mixin"
    )
    assert LegacyQuantizationMixin is QuantizationMixin
    assert QuantizationMixin.__module__ == (
        "airunner_services.llm.workers.mixins.quantization_mixin"
    )
    assert LegacyRAGIndexingMixin is RAGIndexingMixin
    assert RAGIndexingMixin.__module__ == (
        "airunner_services.llm.workers.mixins.rag_indexing_mixin"
    )


def test_target_model_wrappers_share_identity() -> None:
    """Legacy chatbot target-model imports should resolve to services."""
    from airunner.components.llm.data.target_directories import (
        TargetDirectories as LegacyTargetDirectories,
    )
    from airunner.components.llm.data.target_files import (
        TargetFiles as LegacyTargetFiles,
    )
    from airunner_model.models.target_directories import (
        TargetDirectories,
    )
    from airunner_model.models.target_files import TargetFiles

    assert LegacyTargetDirectories is TargetDirectories
    assert LegacyTargetFiles is TargetFiles


def test_database_model_wrappers_share_identity() -> None:
    """Legacy database-model imports should resolve to services."""
    from airunner.components.art.data.active_grid_settings import (
        ActiveGridSettings as LegacyActiveGridSettings,
    )
    from airunner.components.art.data.brush_settings import (
        BrushSettings as LegacyBrushSettings,
    )
    from airunner.components.art.data.grid_settings import (
        GridSettings as LegacyGridSettings,
    )
    from airunner.components.art.data.image_filter import (
        ImageFilter as LegacyImageFilter,
    )
    from airunner.components.art.data.image_filter_value import (
        ImageFilterValue as LegacyImageFilterValue,
    )
    from airunner.components.art.data.metadata_settings import (
        MetadataSettings as LegacyMetadataSettings,
    )
    from airunner.components.art.data.saved_prompt import (
        SavedPrompt as LegacySavedPrompt,
    )
    from airunner.components.llm.data.chatstore import (
        Chatstore as LegacyChatstore,
    )
    from airunner.components.stt.data.stt_settings import (
        STTSettings as LegacySTTSettings,
    )
    from airunner.components.stt.data.whisper_settings import (
        WhisperSettings as LegacyWhisperSettings,
    )
    from airunner.components.tts.data.models.espeak_settings import (
        EspeakSettings as LegacyEspeakSettings,
    )
    from airunner_model.models.active_grid_settings import (
        ActiveGridSettings,
    )
    from airunner_model.models.brush_settings import BrushSettings
    from airunner_model.models.chatstore import Chatstore
    from airunner_model.models.espeak_settings import (
        EspeakSettings,
    )
    from airunner_model.models.grid_settings import GridSettings
    from airunner_model.models.image_filter import ImageFilter
    from airunner_model.models.image_filter_value import (
        ImageFilterValue,
    )
    from airunner_model.models.metadata_settings import (
        MetadataSettings,
    )
    from airunner_model.models.saved_prompt import SavedPrompt
    from airunner_model.models.stt_settings import STTSettings
    from airunner_model.models.whisper_settings import (
        WhisperSettings,
    )

    assert LegacyActiveGridSettings is ActiveGridSettings
    assert LegacyBrushSettings is BrushSettings
    assert LegacyChatstore is Chatstore
    assert LegacyEspeakSettings is not EspeakSettings
    assert LegacyGridSettings is GridSettings
    assert LegacyImageFilter is ImageFilter
    assert LegacyImageFilterValue is ImageFilterValue
    assert LegacyMetadataSettings is MetadataSettings
    assert LegacySavedPrompt is SavedPrompt
    assert LegacySTTSettings is STTSettings
    assert LegacyWhisperSettings is WhisperSettings


def test_application_data_wrapper_shares_identity() -> None:
    """GUI application-data registry should match service tables."""
    from airunner.components.application.data import (
        class_names as legacy_class_names,
    )
    from airunner.components.application.data import classes as legacy_classes
    from airunner.components.application.data import (
        table_to_class as legacy_table_to_class,
    )
    from airunner_services.application_data import class_names
    from airunner_services.application_data import classes, table_to_class

    assert legacy_class_names is not class_names
    assert legacy_classes is not classes
    assert legacy_table_to_class is not table_to_class
    assert legacy_class_names == class_names
    assert [cls.__name__ for cls in legacy_classes] == [
        cls.__name__ for cls in classes
    ]
    assert set(legacy_table_to_class) == set(table_to_class)
    assert legacy_table_to_class["application_settings"].__module__ == (
        "airunner.components.settings.data.application_settings"
    )
    assert table_to_class["application_settings"].__module__ == (
        "airunner_model.models.application_settings"
    )
    assert table_to_class["brush_settings"].__module__ == (
        "airunner_model.models.brush_settings"
    )
    assert table_to_class["chatstore"].__module__ == (
        "airunner_model.models.chatstore"
    )
    assert table_to_class["image_filter_settings"].__module__ == (
        "airunner_model.models.image_filter"
    )
    assert table_to_class["image_filter_values"].__module__ == (
        "airunner_model.models.image_filter_value"
    )


def test_base_and_parser_wrappers_follow_current_ownership() -> None:
    """Legacy base and parser imports should reflect current ownership."""
    from airunner.components.data.models.base import BaseModel as LegacyBaseModel
    from airunner.components.data.models.base_manager import (
        BaseManager as LegacyBaseManager,
    )
    from airunner.components.llm.managers.llm_response import (
        LLMResponse as LegacyLLMResponse,
    )
    from airunner.components.llm.utils.gpt_oss_parser import (
        GPTOSSStreamParser as LegacyGPTOSSStreamParser,
    )
    from airunner.components.llm.utils.stream_text import (
        combine_stream_chunks as legacy_combine_stream_chunks,
    )
    from airunner.components.llm.utils.thinking_parser import (
        parse_thinking_response as legacy_parse_thinking_response,
    )
    from airunner_services.database.base import BaseModel
    from airunner_model.base_manager import BaseManager
    from airunner_services.llm.gpt_oss_parser import GPTOSSStreamParser
    from airunner_services.llm.llm_response import LLMResponse
    from airunner_services.llm.stream_text import combine_stream_chunks
    from airunner_services.llm.thinking_parser import parse_thinking_response

    assert LegacyBaseModel is not BaseModel
    assert LegacyBaseModel.__name__ == BaseModel.__name__
    assert LegacyBaseManager is not BaseManager
    assert LegacyBaseManager.__name__ == BaseManager.__name__
    assert LegacyLLMResponse is LLMResponse
    assert LegacyGPTOSSStreamParser is not GPTOSSStreamParser
    assert LegacyGPTOSSStreamParser.__module__ == (
        "airunner.components.llm.utils.gpt_oss_parser"
    )
    assert legacy_combine_stream_chunks is not combine_stream_chunks
    assert legacy_parse_thinking_response is not parse_thinking_response


def test_session_manager_wrapper_is_gui_owned() -> None:
    """Legacy session-manager imports should now resolve to GUI code."""
    from airunner.components.data.session_manager import (
        reset_engine as legacy_reset_engine,
    )
    from airunner.components.data.session_manager import (
        session_scope as legacy_session_scope,
    )
    from airunner_model.session import reset_engine, session_scope

    assert legacy_reset_engine is not reset_engine
    assert legacy_session_scope is not session_scope


def test_gui_data_base_sources_avoid_service_imports() -> None:
    """GUI data base/session modules should not import services directly."""
    repo_root = Path(__file__).resolve().parents[4]
    data_root = repo_root / "gui" / "src" / "airunner" / "components" / "data"
    base_source = (data_root / "models" / "base.py").read_text(
        encoding="utf-8"
    )
    base_manager_source = (
        data_root / "models" / "base_manager.py"
    ).read_text(encoding="utf-8")
    session_source = (data_root / "session_manager.py").read_text(
        encoding="utf-8"
    )

    assert "airunner_services.database.base" not in base_source
    assert "airunner_model.base_manager" not in (
        base_manager_source
    )
    assert "airunner_model.session" not in session_source
    assert "airunner_services.settings" not in base_source
    assert "airunner_services.settings" not in base_manager_source
    assert "airunner_services.settings" not in session_source


def test_service_api_and_request_wrappers_follow_current_ownership() -> None:
    """Service request wrappers should reflect current ownership."""
    from airunner.components.application.api.api import API as LegacyAPI
    from airunner.components.art.api.art_services import (
        ARTAPIService as LegacyARTAPIService,
    )
    from airunner_services.art.managers.stablediffusion.image_request import (
        ImageRequest as LegacyImageRequest,
    )
    from airunner_services.art.managers.stablediffusion.image_response import (
        ImageResponse as LegacyImageResponse,
    )
    from airunner_services.art.managers.stablediffusion.rect import (
        Rect as LegacyRect,
    )
    from airunner.components.llm.managers.llm_request import (
        LLMRequest as LegacyLLMRequest,
    )
    from airunner_services.api.api import API
    from airunner_services.api.services.art_services import ARTAPIService
    from airunner_services.app.service_app import ServiceApp
    from airunner_services.art.managers.stablediffusion.image_request import ImageRequest
    from airunner_services.art.managers.stablediffusion.image_response import ImageResponse
    from airunner_services.requests.llm_request import LLMRequest
    from airunner_services.art.managers.stablediffusion.rect import Rect

    assert API is not LegacyAPI
    assert issubclass(API, ServiceApp)
    assert LegacyARTAPIService is not ARTAPIService
    assert LegacyARTAPIService.__module__ == (
        "airunner.components.art.api.art_services"
    )
    assert ARTAPIService.__module__ == (
        "airunner_services.api.services.art_services"
    )
    assert LegacyImageRequest is ImageRequest
    assert ImageRequest.__module__ == "airunner_services.requests.image_request"
    assert LegacyImageResponse is ImageResponse
    assert ImageResponse.__module__ == (
        "airunner_services.requests.image_response"
    )
    assert LegacyRect is Rect
    assert Rect.__module__ == "airunner_services.requests.rect"
    assert LegacyLLMRequest is LLMRequest
    assert LLMRequest.__module__ == "airunner_services.llm.llm_request"


def test_additional_settings_models_share_identity() -> None:
    """Settings models should reflect current split ownership."""
    from airunner.components.llm.data.rag_settings import (
        RAGSettings as LegacyRAGSettings,
    )
    from airunner.components.settings.data.airunner_settings import (
        AIRunnerSettings as LegacyAIRunnerSettings,
    )
    from airunner.components.settings.data.language_settings import (
        LanguageSettings as LegacyLanguageSettings,
    )
    from airunner.components.settings.data.sound_settings import (
        SoundSettings as LegacySoundSettings,
    )
    from airunner.components.settings.data.voice_settings import (
        VoiceSettings as LegacyVoiceSettings,
    )
    from airunner.components.tts.data.models.openvoice_settings import (
        OpenVoiceSettings as LegacyOpenVoiceSettings,
    )
    from airunner_model.models.airunner_settings import (
        AIRunnerSettings,
    )
    from airunner_model.models.language_settings import (
        LanguageSettings,
    )
    from airunner_model.models.openvoice_settings import (
        OpenVoiceSettings,
    )
    from airunner_model.models.rag_settings import RAGSettings
    from airunner_model.models.sound_settings import SoundSettings
    from airunner_model.models.voice_settings import VoiceSettings

    assert LegacyAIRunnerSettings is not AIRunnerSettings
    assert LegacyLanguageSettings is not LanguageSettings
    assert LegacyOpenVoiceSettings is not OpenVoiceSettings
    assert LegacyRAGSettings is RAGSettings
    assert LegacySoundSettings is not SoundSettings
    assert LegacyVoiceSettings is not VoiceSettings


def test_tts_settings_models_follow_current_ownership() -> None:
    """Localized TTS settings models should stay GUI-owned."""
    from airunner.components.tts.data.models.espeak_settings import (
        EspeakSettings as LegacyEspeakSettings,
    )
    from airunner.components.tts.data.models.openvoice_settings import (
        OpenVoiceSettings as LegacyOpenVoiceSettings,
    )
    from airunner_model.models.espeak_settings import (
        EspeakSettings,
    )
    from airunner_model.models.openvoice_settings import (
        OpenVoiceSettings,
    )

    assert LegacyEspeakSettings.__module__ == (
        "airunner.components.tts.data.models.espeak_settings"
    )
    assert LegacyOpenVoiceSettings.__module__ == (
        "airunner.components.tts.data.models.openvoice_settings"
    )
    assert LegacyEspeakSettings is not EspeakSettings
    assert LegacyOpenVoiceSettings is not OpenVoiceSettings


def test_tts_request_and_settings_sources_avoid_service_imports() -> None:
    """Localized TTS request/settings modules should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/components/tts/managers/tts_request.py"),
        Path(
            "gui/src/airunner/components/tts/data/models/"
            "espeak_settings.py"
        ),
        Path(
            "gui/src/airunner/components/tts/data/models/"
            "openvoice_settings.py"
        ),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_gui_plain_settings_models_are_gui_owned() -> None:
    """Plain GUI settings models should no longer alias services."""
    from airunner.components.settings.data.airunner_settings import (
        AIRunnerSettings as LegacyAIRunnerSettings,
    )
    from airunner.components.settings.data.font_setting import (
        FontSetting as LegacyFontSetting,
    )
    from airunner.components.settings.data.voice_settings import (
        VoiceSettings as LegacyVoiceSettings,
    )
    from airunner_model.models.airunner_settings import (
        AIRunnerSettings,
    )
    from airunner_model.models.font_setting import FontSetting
    from airunner_model.models.voice_settings import VoiceSettings

    assert LegacyAIRunnerSettings is not AIRunnerSettings
    assert LegacyAIRunnerSettings.__module__ == (
        "airunner.components.settings.data.airunner_settings"
    )
    assert LegacyFontSetting is not FontSetting
    assert LegacyFontSetting.__module__ == (
        "airunner.components.settings.data.font_setting"
    )
    assert LegacyVoiceSettings is not VoiceSettings
    assert LegacyVoiceSettings.__module__ == (
        "airunner.components.settings.data.voice_settings"
    )


def test_gui_plain_settings_sources_avoid_service_models() -> None:
    """Plain GUI settings models should not import service model modules."""
    repo_root = Path(__file__).resolve().parents[4]
    airunner_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "settings"
        / "data"
        / "airunner_settings.py"
    ).read_text(encoding="utf-8")
    font_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "settings"
        / "data"
        / "font_setting.py"
    ).read_text(encoding="utf-8")
    voice_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "settings"
        / "data"
        / "voice_settings.py"
    ).read_text(encoding="utf-8")

    assert "airunner_model.models.airunner_settings" not in (
        airunner_source
    )
    assert "airunner_model.models.font_setting" not in (
        font_source
    )
    assert "airunner_model.models.voice_settings" not in (
        voice_source
    )


def test_gui_client_local_settings_models_are_gui_owned() -> None:
    """GUI-local client settings models should no longer alias services."""
    from airunner.components.settings.data.language_settings import (
        LanguageSettings as LegacyLanguageSettings,
    )
    from airunner.components.settings.data.sound_settings import (
        SoundSettings as LegacySoundSettings,
    )
    from airunner_model.models.language_settings import (
        LanguageSettings,
    )
    from airunner_model.models.sound_settings import SoundSettings

    assert LegacyLanguageSettings is not LanguageSettings
    assert LegacyLanguageSettings.__module__ == (
        "airunner.components.settings.data.language_settings"
    )
    assert LegacySoundSettings is not SoundSettings
    assert LegacySoundSettings.__module__ == (
        "airunner.components.settings.data.sound_settings"
    )


def test_gui_client_local_settings_sources_avoid_service_models() -> None:
    """GUI client-local settings models should not import service models."""
    repo_root = Path(__file__).resolve().parents[4]
    language_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "settings"
        / "data"
        / "language_settings.py"
    ).read_text(encoding="utf-8")
    sound_source = (
        repo_root
        / "gui"
        / "src"
        / "airunner"
        / "components"
        / "settings"
        / "data"
        / "sound_settings.py"
    ).read_text(encoding="utf-8")

    assert "airunner_model.models.language_settings" not in (
        language_source
    )
    assert "airunner_model.models.sound_settings" not in (
        sound_source
    )


def test_art_layer_models_share_identity() -> None:
    """Legacy art-layer settings models should resolve to services."""
    from airunner.components.art.data.canvas_layer import (
        CanvasLayer as LegacyCanvasLayer,
    )
    from airunner.components.art.data.controlnet_settings import (
        ControlnetSettings as LegacyControlnetSettings,
    )
    from airunner.components.art.data.drawingpad_settings import (
        DrawingPadSettings as LegacyDrawingPadSettings,
    )
    from airunner.components.art.data.image_to_image_settings import (
        ImageToImageSettings as LegacyImageToImageSettings,
    )
    from airunner.components.art.data.memory_settings import (
        MemorySettings as LegacyMemorySettings,
    )
    from airunner.components.art.data.outpaint_settings import (
        OutpaintSettings as LegacyOutpaintSettings,
    )
    from airunner_model.models.canvas_layer import CanvasLayer
    from airunner_model.models.controlnet_settings import (
        ControlnetSettings,
    )
    from airunner_model.models.drawingpad_settings import (
        DrawingPadSettings,
    )
    from airunner_model.models.image_to_image_settings import (
        ImageToImageSettings,
    )
    from airunner_model.models.memory_settings import (
        MemorySettings,
    )
    from airunner_model.models.outpaint_settings import (
        OutpaintSettings,
    )

    assert LegacyCanvasLayer is CanvasLayer
    assert LegacyControlnetSettings is ControlnetSettings
    assert LegacyDrawingPadSettings is DrawingPadSettings
    assert LegacyImageToImageSettings is ImageToImageSettings
    assert LegacyMemorySettings is MemorySettings
    assert LegacyOutpaintSettings is OutpaintSettings


def test_llm_and_agent_models_follow_current_ownership() -> None:
    """Legacy LLM and agent model imports should match current ownership."""
    from airunner.components.agents.data.agent_config import (
        AgentConfig as LegacyAgentConfig,
    )
    from airunner.components.llm.data.llm_tool import LLMTool as LegacyLLMTool
    from airunner_model.models.agent_config import AgentConfig
    from airunner_model.models.llm_tool import LLMTool

    assert LegacyAgentConfig is not AgentConfig
    assert LegacyLLMTool is LLMTool


def test_gui_copied_model_sources_avoid_shared_imports() -> None:
    """Localized GUI copied models should not import shared package helpers."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/components/llm/data/chatbot.py"),
        Path("gui/src/airunner/components/llm/data/llm_generator_settings.py"),
        Path("gui/src/airunner/components/llm/data/rag_settings.py"),
        Path("gui/src/airunner/components/art/data/brush_settings.py"),
        Path("gui/src/airunner/components/art/data/generator_settings.py"),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_shared" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_agent_data_sources_avoid_service_imports() -> None:
    """Localized agent data modules should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/components/agents/data/__init__.py"),
        Path("gui/src/airunner/components/agents/data/agent_config.py"),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_agent_runtime_wrappers_follow_current_ownership() -> None:
    """Legacy agent imports should reflect current ownership."""
    from airunner.components.agents import AgentCapability as LegacyCapability
    from airunner.components.agents import AgentRegistry as LegacyAgentRegistry
    from airunner.components.agents import AgentRouter as LegacyAgentRouter
    from airunner.components.agents import ExpertAgent as LegacyExpertAgent
    from airunner.components.agents.expert_agents import (
        CreativeExpertAgent as LegacyCreativeExpertAgent,
    )
    from airunner.components.agents.expert_agents import (
        ResearchExpertAgent as LegacyResearchExpertAgent,
    )
    from airunner.components.agents.runtime import (
        AgentRunRecord as LegacyAgentRunRecord,
    )
    from airunner.components.agents.runtime import (
        AgentTaskRecord as LegacyAgentTaskRecord,
    )
    from airunner.components.agents.templates import (
        get_template as legacy_get_template,
    )
    from airunner_services.agents import AgentCapability
    from airunner_services.agents import AgentRegistry
    from airunner_services.agents import AgentRouter
    from airunner_services.agents import ExpertAgent
    from airunner_services.agents.expert_agents import CreativeExpertAgent
    from airunner_services.agents.expert_agents import ResearchExpertAgent
    from airunner_services.agents.runtime import AgentRunRecord
    from airunner_services.agents.runtime import AgentTaskRecord
    from airunner_services.agents.templates import get_template

    assert LegacyCapability is not AgentCapability
    assert LegacyExpertAgent is not ExpertAgent
    assert LegacyAgentRegistry is not AgentRegistry
    assert LegacyAgentRouter is not AgentRouter
    assert LegacyResearchExpertAgent is not ResearchExpertAgent
    assert LegacyCreativeExpertAgent is not CreativeExpertAgent
    assert LegacyAgentRunRecord is not AgentRunRecord
    assert LegacyAgentTaskRecord is not AgentTaskRecord
    assert legacy_get_template is not get_template


def test_agent_runtime_sources_avoid_service_imports() -> None:
    """Localized agent runtime modules should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/components/agents/__init__.py"),
        Path("gui/src/airunner/components/agents/expert_agent.py"),
        Path("gui/src/airunner/components/agents/agent_registry.py"),
        Path("gui/src/airunner/components/agents/agent_router.py"),
        Path("gui/src/airunner/components/agents/templates.py"),
        Path("gui/src/airunner/components/agents/expert_agents/__init__.py"),
        Path(
            "gui/src/airunner/components/agents/expert_agents/"
            "creative_agent.py"
        ),
        Path(
            "gui/src/airunner/components/agents/expert_agents/"
            "research_agent.py"
        ),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source

    runtime_root = repo_root / "gui/src/airunner/components/agents/runtime"
    for runtime_path in runtime_root.rglob("*.py"):
        source = runtime_path.read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_llm_tool_package_sources_avoid_service_imports() -> None:
    """Localized LLM tool package modules should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    import_module_allowed = {
        Path("gui/src/airunner/components/llm/core/tool_registry.py"),
    }
    for relative_path in [
        Path("gui/src/airunner/components/llm/core/__init__.py"),
        Path("gui/src/airunner/components/llm/core/tool_registry.py"),
        Path("gui/src/airunner/components/llm/tools/__init__.py"),
        Path("gui/src/airunner/components/llm/tools/conversation_tools.py"),
        Path("gui/src/airunner/components/llm/tools/generation_tools.py"),
        Path("gui/src/airunner/components/llm/tools/system_tools.py"),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "sys.modules[__name__]" not in source
        if relative_path not in import_module_allowed:
            assert "import_module" not in source


def test_llm_request_sources_avoid_service_and_shared_imports() -> None:
    """Localized LLM request helpers should stay GUI-owned."""
    repo_root = Path(__file__).resolve().parents[4]
    for relative_path in [
        Path("gui/src/airunner/components/llm/core/request_processor.py"),
        Path("gui/src/airunner/components/llm/managers/llm_request.py"),
        Path("gui/src/airunner/components/llm/utils/get_chatbot.py"),
    ]:
        source = (repo_root / relative_path).read_text(encoding="utf-8")

        assert "airunner_services" not in source
        assert "airunner_shared" not in source
        assert "import_module" not in source
        assert "sys.modules[__name__]" not in source


def test_eval_wrappers_share_identity() -> None:
    """Legacy eval imports should resolve to service-owned code."""
    from airunner.components.eval import AIRunnerClient as LegacyAIRunnerClient
    from airunner.components.eval import (
        create_correctness_evaluator as legacy_create_correctness_evaluator,
    )
    from airunner.components.eval.math_tools import (
        SafePythonExecutor as LegacySafePythonExecutor,
    )
    from airunner_services.eval import AIRunnerClient
    from airunner_services.eval import create_correctness_evaluator
    from airunner_services.eval.math_tools import SafePythonExecutor

    assert LegacyAIRunnerClient is AIRunnerClient
    assert legacy_create_correctness_evaluator is (
        create_correctness_evaluator
    )
    assert LegacySafePythonExecutor is SafePythonExecutor


def test_long_running_project_models_share_identity() -> None:
    """Legacy long-running project models should resolve to services."""
    from airunner.components.llm.long_running.data.project_state import (
        DecisionMemory as LegacyDecisionMemory,
    )
    from airunner.components.llm.long_running.data.project_state import (
        DecisionOutcome as LegacyDecisionOutcome,
    )
    from airunner.components.llm.long_running.data.project_state import (
        FeatureCategory as LegacyFeatureCategory,
    )
    from airunner.components.llm.long_running.data.project_state import (
        FeatureStatus as LegacyFeatureStatus,
    )
    from airunner.components.llm.long_running.data.project_state import (
        ProgressEntry as LegacyProgressEntry,
    )
    from airunner.components.llm.long_running.data.project_state import (
        ProjectFeature as LegacyProjectFeature,
    )
    from airunner.components.llm.long_running.data.project_state import (
        ProjectState as LegacyProjectState,
    )
    from airunner.components.llm.long_running.data.project_state import (
        ProjectStatus as LegacyProjectStatus,
    )
    from airunner.components.llm.long_running.data.project_state import (
        SessionState as LegacySessionState,
    )
    from airunner_model.models.project_state import DecisionMemory
    from airunner_model.models.project_state import DecisionOutcome
    from airunner_model.models.project_state import FeatureCategory
    from airunner_model.models.project_state import FeatureStatus
    from airunner_model.models.project_state import ProgressEntry
    from airunner_model.models.project_state import ProjectFeature
    from airunner_model.models.project_state import ProjectState
    from airunner_model.models.project_state import ProjectStatus
    from airunner_model.models.project_state import SessionState

    assert LegacyDecisionMemory is DecisionMemory
    assert LegacyDecisionOutcome is DecisionOutcome
    assert LegacyFeatureCategory is FeatureCategory
    assert LegacyFeatureStatus is FeatureStatus
    assert LegacyProgressEntry is ProgressEntry
    assert LegacyProjectFeature is ProjectFeature
    assert LegacyProjectState is ProjectState
    assert LegacyProjectStatus is ProjectStatus
    assert LegacySessionState is SessionState


def test_gui_document_models_are_gui_owned() -> None:
    """GUI document models should mirror services without aliasing them."""
    from airunner.components.documents.data.models.document import (
        Document as LegacyDocument,
    )
    from airunner.components.documents.data.models.zimfile import (
        ZimFile as LegacyZimFile,
    )
    from airunner_model.models.document import Document
    from airunner_model.models.zimfile import ZimFile

    assert LegacyDocument is not Document
    assert LegacyDocument.__tablename__ == Document.__tablename__
    assert {
        column.name for column in LegacyDocument.__table__.columns
    } == {column.name for column in Document.__table__.columns}
    assert LegacyZimFile is not ZimFile
    assert LegacyZimFile.__tablename__ == ZimFile.__tablename__
    assert {
        column.name for column in LegacyZimFile.__table__.columns
    } == {column.name for column in ZimFile.__table__.columns}


def test_gui_document_sources_avoid_service_imports() -> None:
    """GUI document modules should not directly import service modules."""
    repo_root = Path(__file__).resolve().parents[4]
    gui_root = (
        repo_root / "gui" / "src" / "airunner" / "components" / "documents" / "data"
    )
    document_source = (gui_root / "models" / "document.py").read_text(
        encoding="utf-8"
    )
    zimfile_source = (gui_root / "models" / "zimfile.py").read_text(
        encoding="utf-8"
    )
    scan_source = (gui_root / "scan_zimfiles.py").read_text(
        encoding="utf-8"
    )

    assert "airunner_model.models.document" not in document_source
    assert "airunner_model.models.zimfile" not in zimfile_source
    assert "airunner_services.documents.scan_zimfiles" not in scan_source
    assert "airunner_model.models.zimfile" not in scan_source


def test_document_archive_utilities_follow_current_ownership() -> None:
    """Document archive utilities should reflect current ownership."""
    from airunner.components.documents.kiwix_api import KiwixAPI as LegacyKiwixAPI
    from airunner.components.zimreader.zimreader import ZIMReader as LegacyZIMReader
    from airunner_services.kiwix_api import KiwixAPI
    from airunner_services.zimreader import ZIMReader

    assert LegacyKiwixAPI is not KiwixAPI
    assert LegacyZIMReader is not ZIMReader


def test_gui_document_network_and_archive_sources_avoid_service_imports() -> None:
    """GUI network and archive helpers should not import services."""
    repo_root = Path(__file__).resolve().parents[4]
    gui_root = repo_root / "gui" / "src" / "airunner"
    url_safety_source = (
        gui_root / "components" / "tools" / "url_safety.py"
    ).read_text(encoding="utf-8")
    kiwix_source = (
        gui_root / "components" / "documents" / "kiwix_api.py"
    ).read_text(encoding="utf-8")
    zimreader_source = (
        gui_root / "components" / "zimreader" / "zimreader.py"
    ).read_text(encoding="utf-8")

    assert "airunner_services.tools.url_safety" not in url_safety_source
    assert "airunner_services.kiwix_api" not in kiwix_source
    assert "airunner_services.zimreader" not in zimreader_source
    assert "airunner_services.settings" not in kiwix_source
    assert "airunner_services.settings" not in zimreader_source
