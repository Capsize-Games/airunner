"""Regression guards for the split package setup metadata."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
from types import ModuleType


_AIRUNNER_COMPAT_IMPORT_PATTERN = re.compile(
    r"\b(?:from|import)\s+airunner(?:\.|\b)|"
    r"import_module\(\s*[\"']airunner(?:\.|[\"'])"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_module(module_name: str, relative_path: str) -> ModuleType:
    module_path = _repo_root() / relative_path
    spec = spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_service_compatibility_imports() -> list[str]:
    root = _repo_root() / "services" / "src" / "airunner_services"
    matches: list[str] = []
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if _AIRUNNER_COMPAT_IMPORT_PATTERN.search(text):
            matches.append(path.relative_to(root).as_posix())
    return matches


def test_services_package_avoids_airunner_compatibility_imports() -> None:
    assert _find_service_compatibility_imports() == []


def test_services_package_metadata_owns_runtime_dependencies() -> None:
    module = _load_module(
        "airunner_services_package_metadata",
        "services/package_metadata.py",
    )
    setup_kwargs = module.build_setup_kwargs(package_source_dir="src")
    install_requires = set(setup_kwargs["install_requires"])
    extras_require = setup_kwargs["extras_require"]

    assert install_requires == {
        f"airunner-model=={module.VERSION}",
        f"airunner-api=={module.VERSION}",
        *module.CORE_REQUIREMENTS,
    }
    assert "PySide6==6.9.0" not in install_requires
    assert "llama-cpp-python==0.3.21" in extras_require["llm-native"]
    assert "diffusers==0.38.0" in extras_require["art-python"]
    assert "pyautogui>=0.9.54" in extras_require["computer_use"]
    assert extras_require["development"] == module.DEVELOPMENT_REQUIREMENTS


def test_gui_package_metadata_owns_qt_not_service_profiles() -> None:
    module = _load_module(
        "airunner_gui_package_metadata",
        "gui/package_metadata.py",
    )
    setup_kwargs = module.build_setup_kwargs(package_source_dir="src")
    console_scripts = set(setup_kwargs["entry_points"]["console_scripts"])
    extras_require = setup_kwargs["extras_require"]

    assert f"airunner-model=={module.VERSION}" in setup_kwargs[
        "install_requires"
    ]
    assert f"airunner-api=={module.VERSION}" in setup_kwargs[
        "install_requires"
    ]
    assert f"airunner-services=={module.VERSION}" in setup_kwargs[
        "install_requires"
    ]
    assert "PySide6==6.9.0" in setup_kwargs["install_requires"]
    assert "PySide6_Addons==6.9.0" in setup_kwargs["install_requires"]
    assert "PySide6_Essentials==6.9.0" in setup_kwargs["install_requires"]
    assert f"airunner-native=={module.VERSION}" not in setup_kwargs[
        "install_requires"
    ]
    assert set(extras_require) == {"development", "dev"}
    assert extras_require["development"] == module.DEVELOPMENT_REQUIREMENTS
    assert "airunner-tests=scripts.run_tests:main" in console_scripts
    assert "airunner=airunner_native.launcher:main" not in console_scripts
    assert "airunner-headless=airunner.bin.airunner_headless:main" not in (
        console_scripts
    )
    assert "airunner-service=airunner.bin.airunner_service:main" not in (
        console_scripts
    )


def test_native_package_metadata_owns_launcher_entry_points() -> None:
    module = _load_module(
        "airunner_native_package_metadata",
        "native/package_metadata.py",
    )
    setup_kwargs = module.build_setup_kwargs(package_source_dir="src")
    console_scripts = set(setup_kwargs["entry_points"]["console_scripts"])
    install_requires = set(setup_kwargs["install_requires"])
    extras_require = setup_kwargs["extras_require"]

    assert install_requires == {
        f"airunner-model=={module.VERSION}",
        f"airunner-api=={module.VERSION}",
        f"airunner-services=={module.VERSION}",
    }
    assert extras_require == {
        "development": module.DEVELOPMENT_REQUIREMENTS,
        "dev": module.DEVELOPMENT_REQUIREMENTS,
        "gui": [f"airunner=={module.VERSION}"],
        "desktop": [f"airunner=={module.VERSION}"],
    }

    assert console_scripts == {
        "airunner=airunner_native.launcher:main",
        "airunner-build-end-user-bundle="
        "airunner_native.bin.build_end_user_bundle:main",
    }


def test_install_helper_keeps_native_available_without_gui() -> None:
    install_script = (_repo_root() / "install.sh").read_text(
        encoding="utf-8"
    )

    assert (
        '    pip install "$model_target"\n'
        '    pip install "$api_target"\n'
        '    pip install "$services_target"\n'
        'if gui_profile_enabled; then\n'
        '        pip install "$gui_target"\n'
        '    fi\n'
        '    pip install "$native_target"\n'
    ) in install_script


def test_dockerfile_keeps_native_available_without_gui() -> None:
    dockerfile = (_repo_root() / "Dockerfile").read_text(
        encoding="utf-8"
    )

    assert (
        '    python3.13 -m pip install -e ./model; \\\n'
        '    python3.13 -m pip install -e ./api; \\\n'
        '    python3.13 -m pip install -e "$service_spec"; \\\n'
        '    if [ "$install_gui" = "1" ]; then \\\n'
        '        python3.13 -m pip install -e ./gui; \\\n'
        '    fi; \\\n'
        '    python3.13 -m pip install -e ./native\n'
    ) in dockerfile


def test_api_package_metadata_owns_transport_neutral_contracts() -> None:
    module = _load_module(
        "airunner_api_package_metadata",
        "api/package_metadata.py",
    )
    setup_kwargs = module.build_setup_kwargs(package_source_dir="src")

    assert setup_kwargs["name"] == "airunner-api"
    assert set(setup_kwargs["install_requires"]) == {
        f"airunner-model=={module.VERSION}",
        "pydantic>=2.7,<3.0",
    }
    assert setup_kwargs["extras_require"]["development"] == (
        module.DEVELOPMENT_REQUIREMENTS
    )


def test_model_package_metadata_owns_runtime_contracts() -> None:
    module = _load_module(
        "airunner_model_package_metadata",
        "model/package_metadata.py",
    )
    setup_kwargs = module.build_setup_kwargs(package_source_dir="src")

    assert setup_kwargs["name"] == "airunner-model"
    assert set(setup_kwargs["install_requires"]) == {"pydantic>=2.7,<3.0"}
    assert setup_kwargs["extras_require"]["development"] == (
        module.DEVELOPMENT_REQUIREMENTS
    )


def test_shared_package_removed_from_repo() -> None:
    assert not (_repo_root() / "shared").exists()