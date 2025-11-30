"""
Launcher for AI Runner that ensures UI files are built before starting the main application.

This script is used as the entry point for the `airunner` command.
"""

import sys
import importlib.util
import os
import subprocess
import traceback
import shutil
from pathlib import Path

from airunner.components.settings.data.airunner_settings import (
    AIRunnerSettings,
)
from airunner.components.settings.data.path_settings import PathSettings
from airunner.settings import AIRUNNER_BASE_PATH, AIRUNNER_LOG_LEVEL, LOCAL_SERVER_HOST
from airunner.setup_database import setup_database
from airunner.components.data.session_manager import _get_session
from airunner.components.settings.data.path_settings import PathSettings
from airunner.components.settings.data.application_settings import (
    ApplicationSettings,
)
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner.utils.application import get_logger

COMPONENTS_PATH = os.path.join(os.path.dirname(__file__), "components")

logger = get_logger(__name__, level=AIRUNNER_LOG_LEVEL)


def deep_merge(defaults, current):
    """Recursively merge defaults into current, overwriting type mismatches and adding missing fields."""
    if not isinstance(defaults, dict) or not isinstance(current, dict):
        return defaults
    merged = dict(current)
    for k, v in defaults.items():
        if k not in merged:
            merged[k] = v
        else:
            if isinstance(v, dict) and isinstance(merged[k], dict):
                merged[k] = deep_merge(v, merged[k])
            elif type(merged[k]) != type(v):
                merged[k] = v
    # Optionally remove keys not in defaults (strict sync)
    # for k in list(merged.keys()):
    #     if k not in defaults:
    #         del merged[k]
    return merged


def build_ui_if_needed():
    """Build UI files only if necessary."""
    ui_build_marker = os.path.join(COMPONENTS_PATH, "ui_build_marker")
    if not os.path.exists(ui_build_marker):
        try:
            subprocess.run(
                [sys.executable, "-m", "airunner_build_ui"], check=True
            )
            with open(ui_build_marker, "w") as marker:
                marker.write("UI files built successfully.")
        except Exception as e:
            logger.warning(f"UI build step failed: {e}")


# Optimize component settings registration by caching results
cached_settings = {}


def register_component_settings():
    """Register settings for each component with a data/settings.py Pydantic dataclass."""
    created_count = 0
    found_count = 0

    for entry in os.scandir(COMPONENTS_PATH):
        if not entry.is_dir():
            continue
        settings_path = os.path.join(entry.path, "data", "settings.py")
        if not os.path.isfile(settings_path):
            continue
        if settings_path in cached_settings:
            continue
        spec = importlib.util.spec_from_file_location(
            f"airunner.components.{entry.name}.data.settings", settings_path
        )
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cached_settings[settings_path] = module
        for attr in dir(module):
            obj = getattr(module, attr)
            if (
                isinstance(obj, type)
                and hasattr(obj, "__fields__")
                and isinstance(
                    obj.__fields__, dict
                )  # Ensure __fields__ is a dictionary
                and "name" in obj.__fields__
            ):
                try:
                    instance = obj()
                    name = getattr(instance, "name", None)
                    if not name:
                        continue
                    found_count += 1
                    existing = AIRunnerSettings.objects.filter_by(name=name)
                    if not existing:
                        data = (
                            instance.dict()
                            if hasattr(instance, "dict")
                            else instance.model_dump()
                        )
                        AIRunnerSettings.objects.create(name=name, data=data)
                        created_count += 1
                    else:
                        defaults = (
                            instance.dict()
                            if hasattr(instance, "dict")
                            else instance.model_dump()
                        )
                        current = (
                            existing[0].data
                            if isinstance(existing, list) and existing
                            else existing.data
                        )
                        merged = deep_merge(defaults, current)
                        for key in ("name", "id"):
                            if key in current:
                                merged[key] = current[key]
                        if merged != current:
                            AIRunnerSettings.objects.update_by(
                                {"name": name}, data=merged
                            )
                except Exception as e:
                    logger.warning(
                        f"Failed to create/update default settings for {attr}: {e}\n{traceback.format_exc()}"
                    )
    logger.info(
        f"register_component_settings: found {found_count} settings classes, created {created_count} new entries."
    )


def generate_local_certs_if_needed(base_path):
    """
    Generate a trusted local certificate using mkcert if available, otherwise fall back to OpenSSL self-signed.
    Certs are always generated in base_path/certs.
    """
    cert_dir = os.path.join(base_path, "certs")
    cert_file = os.path.join(cert_dir, "cert.pem")
    key_file = os.path.join(cert_dir, "key.pem")
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir, exist_ok=True)
    if not (os.path.exists(cert_file) and os.path.exists(key_file)):
        mkcert_path = shutil.which("mkcert")
        if mkcert_path:
            print(
                "Using mkcert to generate a trusted certificate for localhost..."
            )
            try:
                subprocess.run([mkcert_path, "-install"], check=True)
                subprocess.run(
                    [
                        mkcert_path,
                        "-cert-file",
                        cert_file,
                        "-key-file",
                        key_file,
                        "localhost",
                        LOCAL_SERVER_HOST,
                        "::1",
                    ],
                    check=True,
                )
                print(
                    f"Trusted certificate generated with mkcert: {cert_file}, {key_file}"
                )
            except Exception as e:
                print(
                    f"mkcert failed: {e}. Falling back to OpenSSL self-signed certificate."
                )
                subprocess.run(
                    [
                        "openssl",
                        "req",
                        "-x509",
                        "-newkey",
                        "rsa:4096",
                        "-keyout",
                        key_file,
                        "-out",
                        cert_file,
                        "-days",
                        "365",
                        "-nodes",
                        "-subj",
                        "/CN=localhost",
                    ],
                    check=True,
                )
                print(
                    f"Self-signed certificate generated: {cert_file}, {key_file}"
                )
        else:
            print(
                "mkcert not found, falling back to OpenSSL self-signed certificate."
            )
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:4096",
                    "-keyout",
                    key_file,
                    "-out",
                    cert_file,
                    "-days",
                    "365",
                    "-nodes",
                    "-subj",
                    "/CN=localhost",
                ],
                check=True,
            )
            print(
                f"Self-signed certificate generated: {cert_file}, {key_file}"
            )
    return cert_file, key_file


def _configure_test_mode():
    """Configure database settings for test mode.

    When running tests, this function:
    1. Creates default settings if they don't exist
    2. Sets model path from AIRUNNER_TEST_MODEL_PATH env var if provided
    """
    Session = _get_session()
    with Session() as session:
        # Create default path settings if not exists
        if not session.query(PathSettings).first():
            path_settings = PathSettings()
            session.add(path_settings)

        # Create default application settings if not exists
        if not session.query(ApplicationSettings).first():
            app_settings = ApplicationSettings()
            session.add(app_settings)

        # Create or update LLM settings with test model path
        llm_settings = session.query(LLMGeneratorSettings).first()
        if not llm_settings:
            llm_settings = LLMGeneratorSettings()
            session.add(llm_settings)

        # Set model path from environment variable if provided
        test_model_path = os.environ.get("AIRUNNER_TEST_MODEL_PATH")
        if test_model_path:
            llm_settings.model_path = test_model_path
            logger.info(f"Test mode: Using model path: {test_model_path}")
        else:
            logger.warning(
                "Test mode: AIRUNNER_TEST_MODEL_PATH not set. "
                "Tests requiring LLM will fail. "
                "Use pytest --model=/path/to/model or set environment variable."
            )

        session.commit()


def _check_first_run_agreement():
    """Check if user has accepted all legal agreements, show dialogs if not.
    
    Shows Age Agreement, Privacy Policy, and Terms of Service dialogs
    in sequence on first run. All must be accepted to proceed.
    
    Returns:
        tuple: (QApplication, bool) - app instance and whether to proceed
    """
    from PySide6.QtWidgets import QApplication
    from airunner.utils.settings.get_qsettings import get_qsettings
    from airunner.components.application.gui.dialogs.first_run_agreement_dialog import (
        check_all_agreements,
    )
    
    # Create QApplication if not exists (needed for dialog)
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    qsettings = get_qsettings()
    
    # Check and show all agreement dialogs if needed
    if not check_all_agreements(qsettings):
        # User declined one of the agreements - exit
        return app, False
    
    return app, True


def _show_early_splash(existing_app=None):
    """Show splash screen as early as possible, before heavy initialization."""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QGuiApplication
    from airunner.components.splash_screen.splash_screen import SplashScreen
    
    # Use existing app or create new
    if existing_app is not None:
        app = existing_app
    else:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
    
    # Get the target screen
    screens = QGuiApplication.screens()
    target_screen = QGuiApplication.primaryScreen()
    
    # Try to use saved screen preference
    try:
        from airunner.utils.settings.get_qsettings import get_qsettings
        qsettings = get_qsettings()
        qsettings.beginGroup("window_settings")
        saved_screen_name = qsettings.value("screen_name", None, type=str)
        qsettings.endGroup()
        
        if saved_screen_name:
            for s in screens:
                if s.name() == saved_screen_name:
                    target_screen = s
                    break
    except Exception:
        pass
    
    # Final fallback
    if not target_screen and screens:
        target_screen = screens[0]
    
    # Create and show splash
    base_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    image_path = base_dir / "gui" / "images" / "splashscreen.png"
    splash = SplashScreen(target_screen, image_path)
    splash.show_message("Starting AI Runner...")
    splash.show()
    app.processEvents()
    
    return app, splash


def _update_splash(splash, message):
    """Update splash screen message and process events."""
    from PySide6.QtWidgets import QApplication
    if splash:
        splash.show_message(message)
        app = QApplication.instance()
        if app:
            app.processEvents()


def main():
    # Check first-run agreement BEFORE splash screen
    app, proceed = _check_first_run_agreement()
    if not proceed:
        # User declined terms - exit
        sys.exit(0)
    
    # Show splash screen IMMEDIATELY before any heavy operations
    app, splash = _show_early_splash(existing_app=app)
    
    # Build UI files first
    _update_splash(splash, "Building UI files...")
    build_ui_if_needed()

    # --- Ensure database and tables are created before any DB access ---
    _update_splash(splash, "Setting up database...")
    setup_database()

    # --- Configure test mode if running tests ---
    if os.environ.get("AIRUNNER_ENVIRONMENT") == "test":
        _configure_test_mode()

    # Register component settings after UI build but before main app starts
    _update_splash(splash, "Registering component settings...")
    try:
        register_component_settings()
    except Exception as e:
        logger.error(f"Failed to register component settings: {e}")
        traceback.print_exc()

    # --- SSL certificate auto-generation ---
    _update_splash(splash, "Generating SSL certificates...")
    path_settings = PathSettings.objects.first()
    if not path_settings:
        base_path = AIRUNNER_BASE_PATH
    else:
        base_path = path_settings.base_path
    cert_file, key_file = generate_local_certs_if_needed(base_path)
    os.environ["AIRUNNER_SSL_CERT"] = cert_file
    os.environ["AIRUNNER_SSL_KEY"] = key_file

    # Store splash in environment for main.py to use
    _update_splash(splash, "Loading AI Runner...")
    
    # Pass splash to the main app via environment variable workaround
    # The App class will take over the splash
    import airunner.main as main_module
    main_module._launcher_splash = splash
    main_module._launcher_app = app
    
    # Run the main app (it will use our existing splash and app)
    from airunner.main import main as real_main
    sys.exit(real_main())
