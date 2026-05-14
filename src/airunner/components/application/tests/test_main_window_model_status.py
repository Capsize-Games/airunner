"""Tests for main-window model status synchronization."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from airunner.components.application.gui.windows.main import (
    main_window as main_window_module,
)
from airunner.components.application.gui.windows.main.main_window import (
    MainWindow,
)
from airunner.components.model_management.types import ModelState
from airunner.enums import ModelStatus, ModelType
from airunner.settings import AIRUNNER_DEFAULT_STT_HF_PATH


@pytest.fixture(autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def resource_manager_stub(monkeypatch):
    manager = SimpleNamespace(
        get_active_models=lambda: [],
        cleanup_model=Mock(),
        model_loaded=Mock(),
        set_model_state=Mock(),
        get_model_state=Mock(return_value=ModelState.UNLOADED),
    )
    monkeypatch.setattr(
        main_window_module,
        "ModelResourceManager",
        lambda: manager,
    )
    return manager


def _make_action() -> Mock:
    action = Mock()
    action.blockSignals = Mock()
    action.setChecked = Mock()
    action.setDisabled = Mock()
    return action


def _make_window_stub():
    window = SimpleNamespace(
        _model_status={
            model_type: ModelStatus.UNLOADED for model_type in ModelType
        },
        _post_startup_status_refresh_requested=False,
        _restore_sidebar_page_after_startup=None,
        _runtime_preference_retry_after={},
        _documents_sidebar_index=0,
        _stats_sidebar_index=1,
        ui=SimpleNamespace(
            text_to_speech_button=_make_action(),
            speech_to_text_button=_make_action(),
            sidebar_tab=SimpleNamespace(
                currentIndex=Mock(return_value=0),
                setCurrentIndex=Mock(),
            ),
            main_window_splitter=SimpleNamespace(sizes=lambda: [0, 0, 0]),
            knowledgebase_button=_make_action(),
            stats_button=_make_action(),
        ),
        application_settings=SimpleNamespace(
            llm_enabled=False,
            tts_enabled=False,
            stt_enabled=False,
            sd_enabled=False,
            nsfw_filter=False,
        ),
        llm_generator_settings=SimpleNamespace(
            model_path="",
            model_id="",
            model_version="",
        ),
        path_settings=SimpleNamespace(
            tts_model_path="",
            stt_model_path="",
        ),
        chatbot_voice_settings=SimpleNamespace(model_type=""),
        update_application_settings=Mock(),
        emit_signal=Mock(),
        initialize_widget_elements=Mock(),
        logger=Mock(),
        refresh_api_reference=Mock(return_value=None),
        _ensure_canvas_loaded=Mock(),
        _ensure_sidebar_page_loaded=Mock(),
        _sync_sidebar_button_states=Mock(),
        _set_action_checked_state=MainWindow._set_action_checked_state,
        _allows_loading_toggle=MainWindow._allows_loading_toggle,
        _optional_runtime_preference_specs=(
            MainWindow._optional_runtime_preference_specs
        ),
        _reconcile_optional_runtime_preference=(
            MainWindow._reconcile_optional_runtime_preference
        ),
        _runtime_preference_retry_seconds=(
            MainWindow._runtime_preference_retry_seconds
        ),
    )
    window._normalize_direct_llm_status = lambda status: (
        MainWindow._normalize_direct_llm_status(window, status)
    )
    return window


def test_tts_runtime_status_does_not_persist_user_preference():
    window = _make_window_stub()

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.TTS, "status": ModelStatus.LOADED},
    )

    window.update_application_settings.assert_not_called()
    window.initialize_widget_elements.assert_not_called()
    window.ui.text_to_speech_button.setDisabled.assert_called_once_with(
        False
    )


def test_stt_runtime_status_does_not_persist_user_preference():
    window = _make_window_stub()
    window._model_status[ModelType.STT] = ModelStatus.LOADED

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.STT, "status": ModelStatus.UNLOADED},
    )

    window.update_application_settings.assert_not_called()
    window.initialize_widget_elements.assert_not_called()
    window.ui.speech_to_text_button.setDisabled.assert_called_once_with(
        False
    )


def test_failed_tts_status_keeps_action_checked_state_for_retry():
    window = _make_window_stub()

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.TTS, "status": ModelStatus.FAILED},
    )

    window.update_application_settings.assert_not_called()
    window.ui.text_to_speech_button.setChecked.assert_not_called()


def test_failed_stt_status_keeps_action_checked_state_for_retry():
    window = _make_window_stub()

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.STT, "status": ModelStatus.FAILED},
    )

    window.update_application_settings.assert_not_called()
    window.ui.speech_to_text_button.setChecked.assert_not_called()


def test_loading_stt_status_keeps_action_enabled_for_cancel():
    window = _make_window_stub()

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.STT, "status": ModelStatus.LOADING},
    )

    window.ui.speech_to_text_button.setDisabled.assert_called_once_with(
        False
    )


def test_reconcile_optional_runtime_preferences_unloads_disabled_runtime():
    window = _make_window_stub()

    MainWindow._reconcile_optional_runtime_preferences(window, {"STT"})

    window.emit_signal.assert_called_once_with(
        MainWindow._optional_runtime_preference_specs()[1][4],
        {"source": "runtime_preference_sync"},
    )


def test_reconcile_optional_runtime_preferences_loads_enabled_runtime():
    window = _make_window_stub()
    window.application_settings.tts_enabled = True

    MainWindow._reconcile_optional_runtime_preferences(window, set())

    window.emit_signal.assert_called_once_with(
        MainWindow._optional_runtime_preference_specs()[0][3],
        {"source": "runtime_preference_sync"},
    )


def test_reconcile_optional_runtime_preferences_respects_retry_window():
    window = _make_window_stub()

    MainWindow._reconcile_optional_runtime_preferences(window, {"STT"})
    MainWindow._reconcile_optional_runtime_preferences(window, {"STT"})

    window.emit_signal.assert_called_once_with(
        MainWindow._optional_runtime_preference_specs()[1][4],
        {"source": "runtime_preference_sync"},
    )


def test_reconcile_optional_runtime_preferences_unloads_while_loading():
    window = _make_window_stub()
    window._model_status[ModelType.STT] = ModelStatus.LOADING

    MainWindow._reconcile_optional_runtime_preferences(window, {"STT"})

    window.emit_signal.assert_called_once_with(
        MainWindow._optional_runtime_preference_specs()[1][4],
        {"source": "runtime_preference_sync"},
    )


def test_runtime_starting_summary_maps_to_loading():
    status = MainWindow._model_status_from_runtime_summary(
        {"status": "starting", "loaded": True}
    )

    assert status is ModelStatus.LOADING


def test_optional_toggle_updates_preference_while_loading():
    window = _make_window_stub()
    window._model_status[ModelType.STT] = ModelStatus.LOADING

    MainWindow._update_action_button(
        window,
        ModelType.STT,
        window.ui.speech_to_text_button,
        False,
        object(),
        object(),
        "stt_enabled",
    )

    window.update_application_settings.assert_called_once_with(
        stt_enabled=False
    )
    window.emit_signal.assert_not_called()
    window.ui.speech_to_text_button.setChecked.assert_called_once_with(
        False
    )


def test_sync_only_llm_toggle_skips_runtime_reload():
    window = _make_window_stub()

    MainWindow.on_toggle_llm(
        window,
        {"enabled": True, "sync_only": True},
    )

    window.update_application_settings.assert_called_once_with(
        llm_enabled=True
    )
    window.emit_signal.assert_not_called()


def test_initialize_widget_elements_marks_window_initialized():
    window = _make_window_stub()
    window.application_settings = SimpleNamespace(
        llm_enabled=False,
        tts_enabled=False,
        stt_enabled=False,
        sd_enabled=False,
        nsfw_filter=False,
    )
    window.initialized = False

    MainWindow.initialize_widget_elements(window)

    assert window.initialized is True


def test_emit_main_window_loaded_signal_refreshes_api_reference():
    window = _make_window_stub()
    api = SimpleNamespace(main_window_loaded=Mock())
    window.api = None
    window.refresh_api_reference = Mock(return_value=api)

    MainWindow._emit_main_window_loaded_signal_if_ready(window)

    window.refresh_api_reference.assert_called_once_with()
    api.main_window_loaded.assert_called_once_with(window)
    assert window._main_window_loaded_signal_emitted is True


def test_on_main_window_loaded_signal_refreshes_daemon_status_once():
    window = _make_window_stub()
    window._refresh_model_status_from_daemon = Mock()

    MainWindow.on_main_window_loaded_signal(window)
    MainWindow.on_main_window_loaded_signal(window)

    window._ensure_canvas_loaded.assert_called()
    window._refresh_model_status_from_daemon.assert_called_once_with()


def test_on_main_window_loaded_signal_restores_saved_sidebar_page():
    window = _make_window_stub()
    window._restore_sidebar_page_after_startup = 1
    window._refresh_model_status_from_daemon = Mock()

    MainWindow.on_main_window_loaded_signal(window)

    window._ensure_sidebar_page_loaded.assert_called_once_with(1)
    window.ui.sidebar_tab.setCurrentIndex.assert_called_once_with(1)
    window._sync_sidebar_button_states.assert_called_once_with()
    assert window._restore_sidebar_page_after_startup is None


def test_sidebar_buttons_reflect_active_sidebar_page():
    window = _make_window_stub()
    window.ui.main_window_splitter = SimpleNamespace(sizes=lambda: [50, 500, 240])
    window._sidebar_is_visible = lambda: True
    window.ui.sidebar_tab.currentIndex = Mock(return_value=1)

    MainWindow.set_knowledgebase_button_checked(window)
    MainWindow.set_stats_button_checked(window)

    window.ui.knowledgebase_button.setChecked.assert_called_once_with(False)
    window.ui.stats_button.setChecked.assert_called_once_with(True)


def test_daemon_status_prefers_loaded_local_llm_worker():
    window = _make_window_stub()
    window._daemon_status_refresh_inflight = True
    window.worker_manager = SimpleNamespace(
        _llm_generate_worker=SimpleNamespace(
            current_model_status=lambda: ModelStatus.LOADED
        )
    )
    window._sync_model_status_value = (
        lambda model_type, status:
        MainWindow._sync_model_status_value(window, model_type, status)
    )
    window._runtime_statuses_from_daemon_status = (
        MainWindow._runtime_statuses_from_daemon_status
    )
    window._loaded_model_names_from_runtime_status = (
        MainWindow._loaded_model_names_from_runtime_status
    )
    window._effective_llm_status = (
        lambda status: MainWindow._effective_llm_status(window, status)
    )
    window._reconcile_optional_runtime_preferences = Mock()

    MainWindow._on_daemon_runtime_status_ready(
        window,
        {
            "runtimes": [
                {"runtime": "llm", "status": "stopped", "loaded": False}
            ]
        },
    )

    window.emit_signal.assert_called_once_with(
        main_window_module.SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
        {"model": ModelType.LLM, "status": ModelStatus.LOADED},
    )


def test_daemon_failed_status_does_not_override_local_llm_state():
    window = _make_window_stub()
    window._daemon_status_refresh_inflight = True
    window.worker_manager = SimpleNamespace(
        _llm_generate_worker=SimpleNamespace(
            current_model_status=lambda: ModelStatus.UNLOADED
        )
    )
    window._sync_model_status_value = (
        lambda model_type, status:
        MainWindow._sync_model_status_value(window, model_type, status)
    )
    window._runtime_statuses_from_daemon_status = (
        MainWindow._runtime_statuses_from_daemon_status
    )
    window._loaded_model_names_from_runtime_status = (
        MainWindow._loaded_model_names_from_runtime_status
    )
    window._effective_llm_status = (
        lambda status: MainWindow._effective_llm_status(window, status)
    )
    window._reconcile_optional_runtime_preferences = Mock()

    MainWindow._on_daemon_runtime_status_ready(
        window,
        {
            "runtimes": [
                {"runtime": "llm", "status": "failed", "loaded": False}
            ]
        },
    )

    assert window._model_status[ModelType.LLM] == ModelStatus.UNLOADED


def test_sync_model_resource_manager_from_daemon_tracks_art_model(
    monkeypatch,
):
    window = _make_window_stub()
    manager = SimpleNamespace(
        get_active_models=lambda: [],
        cleanup_model=Mock(),
        model_loaded=Mock(),
        set_model_state=Mock(),
    )
    monkeypatch.setattr(
        main_window_module,
        "ModelResourceManager",
        lambda: manager,
    )

    MainWindow._sync_model_resource_manager_from_daemon(
        window,
        {
            "runtimes": [
                {
                    "runtime": "art",
                    "status": "ready",
                    "loaded": True,
                    "metadata": {
                        "model_path": "/models/zimage.safetensors",
                    },
                }
            ]
        },
    )

    manager.model_loaded.assert_called_once_with(
        "/models/zimage.safetensors",
        "text_to_image",
    )


def test_sync_model_resource_manager_from_daemon_cleans_unloaded_art(
    monkeypatch,
):
    window = _make_window_stub()
    manager = SimpleNamespace(
        get_active_models=lambda: [
            SimpleNamespace(
                model_id="/models/zimage.safetensors",
                model_type="text_to_image",
                state=ModelState.LOADED,
            )
        ],
        cleanup_model=Mock(),
        model_loaded=Mock(),
        set_model_state=Mock(),
    )
    monkeypatch.setattr(
        main_window_module,
        "ModelResourceManager",
        lambda: manager,
    )

    MainWindow._sync_model_resource_manager_from_daemon(
        window,
        {
            "runtimes": [
                {
                    "runtime": "art",
                    "status": "stopped",
                    "loaded": False,
                    "metadata": {},
                }
            ]
        },
    )

    manager.cleanup_model.assert_called_once_with(
        "/models/zimage.safetensors",
        "text_to_image",
    )


def test_direct_loaded_llm_status_syncs_resource_manager(
    resource_manager_stub,
):
    window = _make_window_stub()
    window._model_status[ModelType.LLM] = ModelStatus.LOADED
    window.llm_generator_settings = SimpleNamespace(
        model_path="/models/qwen3.gguf",
        model_id="qwen3",
        model_version="Qwen3",
    )

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.LLM, "status": ModelStatus.LOADED},
    )

    resource_manager_stub.model_loaded.assert_called_once_with(
        "/models/qwen3.gguf",
        "llm",
    )


def test_direct_loaded_tts_status_uses_voice_model_name(
    resource_manager_stub,
):
    window = _make_window_stub()
    window.chatbot_voice_settings = SimpleNamespace(model_type="OpenVoice")

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.TTS, "status": ModelStatus.LOADED},
    )

    resource_manager_stub.model_loaded.assert_called_once_with(
        "OpenVoice",
        "tts",
    )


def test_direct_loaded_stt_status_uses_configured_model_path(
    resource_manager_stub,
):
    window = _make_window_stub()
    window.path_settings = SimpleNamespace(
        tts_model_path="",
        stt_model_path="/models/stt",
    )

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.STT, "status": ModelStatus.LOADED},
    )

    resource_manager_stub.model_loaded.assert_called_once_with(
        f"/models/stt/{AIRUNNER_DEFAULT_STT_HF_PATH}",
        "stt",
    )


def test_safety_checker_status_syncs_resource_manager(
    resource_manager_stub,
):
    window = _make_window_stub()

    MainWindow.on_model_status_changed_signal(
        window,
        {
            "model": ModelType.SAFETY_CHECKER,
            "status": ModelStatus.LOADED,
        },
    )

    resource_manager_stub.model_loaded.assert_called_once_with(
        "Safety Checker",
        "safety_checker",
    )


def test_direct_failed_status_does_not_override_local_llm_loading():
    window = _make_window_stub()
    window.worker_manager = SimpleNamespace(
        _llm_generate_worker=SimpleNamespace(
            current_model_status=lambda: ModelStatus.LOADING
        )
    )

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.LLM, "status": ModelStatus.FAILED},
    )

    assert window._model_status[ModelType.LLM] is ModelStatus.LOADING
    window.logger.warning.assert_not_called()
    window.emit_signal.assert_not_called()


def test_direct_failed_status_keeps_loaded_llm_when_status_unknown():
    window = _make_window_stub()
    window._model_status[ModelType.LLM] = ModelStatus.LOADED
    window.worker_manager = SimpleNamespace(
        _llm_generate_worker=SimpleNamespace(
            current_model_status=lambda: None
        )
    )

    MainWindow.on_model_status_changed_signal(
        window,
        {"model": ModelType.LLM, "status": ModelStatus.FAILED},
    )

    assert window._model_status[ModelType.LLM] is ModelStatus.LOADED
    window.logger.warning.assert_not_called()


def test_handoff_launcher_splash_defers_dismissal(monkeypatch):
    window = _make_window_stub()
    window.api = SimpleNamespace(splash=object())
    window._launcher_splash_dismissed = False
    window._complete_launcher_splash_handoff = (
        lambda: MainWindow._complete_launcher_splash_handoff(window)
    )
    window.raise_ = Mock()
    window.activateWindow = Mock()
    callbacks: list[object] = []
    app = QApplication.instance()
    dismiss_splash = Mock()

    monkeypatch.setattr(
        main_window_module.QApplication,
        "instance",
        lambda: app,
    )
    monkeypatch.setattr(
        main_window_module.QTimer,
        "singleShot",
        lambda _delay, callback: callbacks.append(callback),
    )
    monkeypatch.setattr(
        "airunner.app_mixins.ui_runtime_mixin."
        "UIRuntimeMixin._dismiss_splash_screen",
        dismiss_splash,
    )

    MainWindow._handoff_launcher_splash(window)

    dismiss_splash.assert_not_called()
    assert window._launcher_splash_dismissed is True
    assert len(callbacks) == 1

    callbacks[0]()

    dismiss_splash.assert_called_once_with(window.api, window, app)
    window.raise_.assert_called_once_with()
    window.activateWindow.assert_called_once_with()