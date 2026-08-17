"""Setup for the AIRunner GUI package.

VERSION and the facehuggershield requirement are single-sourced from
``shared/airunner_common/package_metadata.py`` (issue #2044) so the GUI,
services, native and shared surfaces cannot drift.
"""

import sys
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as _build_py

# Make the shared package importable when building from the repo root
# without requiring it to be installed first (issue #2044).
_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT / "shared"))

from airunner_common.package_metadata import (  # noqa: E402
    DEVELOPMENT_REQUIREMENTS,
    FACEHUGGERSHIELD_REQUIREMENT,
    VERSION,
)

README = Path("README.md").read_text(encoding="utf-8")

GUI_REQUIREMENTS = [
    "PySide6==6.9.0",
    "PySide6_Addons==6.9.0",
    "PySide6_Essentials==6.9.0",
    f"airunner-common=={VERSION}",
    # The GUI hard-imports airunner_services (daemon_client, api) but never
    # declared it (issue #2037). Mirror the native pattern and pin it to the
    # same VERSION as the rest of the surface.
    f"airunner-services=={VERSION}",
    # Undeclared third-party runtime imports (issue #2040).
    # requests: url_safety, components/documents/kiwix_api,
    #           components/llm/utils/model_downloader,
    #           components/application/workers/download_worker
    # numpy:    utils/audio/sound_device_manager,
    #           components/art/filters/{dither,rgb_noise,film}
    # Pillow:   utils/image/convert_image_to_binary
    # markdown: utils/text/formatter
    # jinja2:   components/server/local_http_server
    # psutil:   components/application/gui/widgets/stats/stats_widget
    "requests>=2.31.0",
    "numpy>=1.26.0",
    "Pillow>=10.0.0",
    "markdown>=3.5.0",
    "jinja2>=3.1.0",
    "psutil>=5.9.0",
    FACEHUGGERSHIELD_REQUIREMENT,
]

# PyTorch is a hard GUI import (utils/memory/gpu_memory_stats, main.py) but
# is intentionally kept in a documented optional "ml" group below so the base
# GUI package can install without a CUDA wheel. See ML_REQUIREMENTS.

# Documented optional/ML group (issues #2040/#2041). torch/torchvision/
# torchaudio are pinned to the stable cu129 line matching the Docker base
# image (nvidia/cuda:12.9.1-devel-ubuntu24.04). Install with:
#     pip install "airunner[ml]" --index-url https://download.pytorch.org/whl/cu129
# CPU fallback: --index-url https://download.pytorch.org/whl/cpu
ML_REQUIREMENTS = [
    "torch==2.13.0+cu129",
    "torchvision==0.28.0+cu129",
    "torchaudio==2.11.0+cu129",
]

ANALYSIS_REQUIREMENTS = [
    "radon>=6.0.1,<7",
    "xenon>=0.9.3,<1",
]


class _FilteredBuildPy(_build_py):
    """build_py that drops the in-package pytest harness (issue #2046).

    ``find_packages(exclude=...)`` removes whole packages (test_support,
    *.tests) but cannot remove a bare module such as ``airunner/conftest.py``,
    which setuptools otherwise ships as part of the ``airunner`` package. The
    conftest is only used by pytest from a checkout and must not ship.
    """

    def find_package_modules(self, package: str, package_dir: str) -> list:
        modules = super().find_package_modules(package, package_dir)
        if package == "airunner":
            modules = [
                (pkg, mod, path)
                for pkg, mod, path in modules
                if mod != "conftest"
            ]
        return modules


setup(
    name="airunner",
    version=VERSION,
    author="Capsize LLC",
    description="Run local opensource AI models (Stable Diffusion, LLMs, TTS, STT, chatbots) in a lightweight Python GUI",
    long_description=README,
    long_description_content_type="text/markdown",
    keywords="llm, pyside6, gui, local llm, stable diffusion, generative ai, local chatgpt, text-to-speech, speech-to-text, open source chatbot, python ai runner",
    license="GPL-3.0-only",
    author_email="contact@capsizegames.com",
    url="https://github.com/Capsize-Games/airunner",
    # The top-level scripts/ directory is developer tooling only and must not
    # be shipped in the wheel (issue #2044). Likewise the in-package test
    # harness (conftest.py, test_support/, *.tests/) is dev tooling and must
    # not ship in the wheel (issue #2046).
    package_dir={"": "src"},
    packages=find_packages(
        "src",
        exclude=[
            "airunner.conftest",
            "airunner.test_support",
            "*.tests",
            "*.tests.*",
        ],
    ),
    python_requires=">=3.13.3",
    install_requires=GUI_REQUIREMENTS,
    extras_require={
        "analysis": ANALYSIS_REQUIREMENTS,
        "ml": ML_REQUIREMENTS,
        # Test/lint/dev tooling (issue #2054). Mirrors the shared
        # DEVELOPMENT_REQUIREMENTS so ``pip install -e ".[development]"``
        # installs pytest + pytest-timeout and the CI eval-tests workflow can
        # run from a fresh clone.
        "development": DEVELOPMENT_REQUIREMENTS,
    },
    package_data={
        "airunner": [
            # GUI resources
            "gui/cursors/*",
            "gui/images/*",
            "gui/resources/**/*",
            "gui/styles/**/*",
            # UI templates (all .ui files in templates directories)
            "components/**/templates/*.ui",
            # Legal documents (user agreement, privacy policy) - loaded at
            # runtime by first_run_agreement_dialog / legal_document_dialog
            "components/**/user_agreement/*.md",
            # Static files (HTML, CSS, JS templates for web views)
            "components/**/static/**/*",
            "static/**/*",
            # Compiled Qt translations and their sources (issue #2043)
            "translations/*.qm",
            "translations/*.ts",
        ],
    },
    exclude_package_data={
        # Test harness must not ship in the wheel (issue #2046). find_packages
        # excludes the test_support/ package and *.tests/* packages above;
        # this removes the bare conftest.py module from the airunner package.
        "airunner": [
            "conftest.py",
            "test_support/*",
            "test_support/**/*",
        ],
    },
    include_package_data=True,
    cmdclass={"build_py": _FilteredBuildPy},
    entry_points={
        # Only the runtime GUI launcher is installed. Developer commands
        # (build-ui, compile-translations, probes, test runners, quality and
        # complexity reports) live in the scripts/ package and are run from a
        # checkout with `python scripts/<tool>.py`; they are intentionally
        # not shipped as installed console scripts (issue #2044).
        "console_scripts": [
            "airunner=airunner.launcher:main",
        ],
    },
)
