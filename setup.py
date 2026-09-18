"""Setup for the AIRunner GUI package.

The build metadata below is vendored statically, the same pattern already
established for services/setup.py and native/setup.py (issue #2038):
airunner_common now lives in its own repository
(https://github.com/Capsize-Games/airunner-common, issue #2197), so a
``sys.path`` insert at the repo root -- this file's previous approach,
issue #2044 -- stopped working once it became a separate checkout. Its
own VERSION/FACEHUGGERSHIELD_REQUIREMENT/LICENSE_CLASSIFIERS are the
values worth keeping in sync here when they change.
"""

import sys
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py as _build_py

_REPO_ROOT = Path(__file__).resolve().parent

VERSION = "6.1.3"

# The project is GPL-3.0-only (issue #2058): the repo-root LICENSE file,
# every ``license=`` metadata field and these PyPI classifiers must agree.
# Mirrored from airunner_common/package_metadata.py in
# Capsize-Games/airunner-common.
LICENSE_CLASSIFIERS = [
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
]

# Supply-chain hardening (issue #2036); see airunner_common/package_metadata.py
# in Capsize-Games/airunner-common for the full rationale.
FACEHUGGERSHIELD_REQUIREMENT = "facehuggershield==1.0.0"

# Test/lint/dev tooling (issue #2054). Mirrors
# airunner_common/package_metadata.py's DEVELOPMENT_REQUIREMENTS in
# Capsize-Games/airunner-common.
DEVELOPMENT_REQUIREMENTS = [
    "pytest",
    "pytest-timeout",
    "responses>=0.25.0",
    "httpx>=0.27",
    "coverage==7.8.0",
    "black==26.3.1",
    "pyinstaller==6.12.0",
    "flake8==7.2.0",
    "mypy==1.16.0",
    "autoflake==2.3.1",
    "pandas>=2.0.0",
    "pyarrow>=14.0.0",
    "tqdm>=4.0.0",
]

README = Path("README.md").read_text(encoding="utf-8")

GUI_REQUIREMENTS = [
    "PySide6==6.9.0",
    "PySide6_Addons==6.9.0",
    "PySide6_Essentials==6.9.0",
    # airunner-common is independently versioned in its own repository
    # now (issue #2197, https://github.com/Capsize-Games/airunner-common),
    # so a compatible-release pin per the versioning policy (#2191)
    # instead of an exact lockstep VERSION pin. Floor is 6.1.5, the
    # release that added llm_response (issue #2188) -- this package
    # imports airunner_common.llm_response directly and cannot start
    # on an older release.
    "airunner-common~=6.1.5",
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
    *.tests) but cannot remove bare ``conftest`` modules, which setuptools
    otherwise ships as part of the ``airunner`` package. pytest's conftest
    files are only used from a checkout and must not ship. The filter must
    cover every subpackage (``airunner.*``): ``find_package_modules`` is
    called once per package, so checking only ``package == "airunner"`` lets
    nested conftests such as ``airunner/components/application/conftest.py``
    leak into the wheel.
    """

    def find_package_modules(self, package: str, package_dir: str) -> list:
        modules = super().find_package_modules(package, package_dir)
        if package == "airunner" or package.startswith("airunner."):
            modules = [
                (pkg, mod, path)
                for pkg, mod, path in modules
                if mod != "conftest"
            ]
        return modules

    def run(self):
        self._verify_generated_ui_resources()
        super().run()

    @staticmethod
    def _verify_generated_ui_resources() -> None:
        """Fail the build if compiled Qt UI/resource files are missing.

        Compilation itself happens via ``scripts/build_ui.py`` (a
        developer/CI step, run before ``python -m build``/``bdist_wheel``,
        never at application startup — see ``airunner.launcher``). This
        only verifies the checkout already has up-to-date generated
        files before they get swept into the package (release issue P01).
        """
        scripts_dir = _REPO_ROOT / "scripts"
        sys.path.insert(0, str(scripts_dir))
        try:
            from build_ui import verify_generated_resources
        finally:
            sys.path.remove(str(scripts_dir))

        problems = verify_generated_resources(_REPO_ROOT / "src" / "airunner")
        if problems:
            raise RuntimeError(
                "Cannot package airunner: generated Qt UI/resource files "
                "are missing or stale. Run `python scripts/build_ui.py` "
                "from a source checkout first. Problems:\n"
                + "\n".join(f"  - {problem}" for problem in problems)
            )


setup(
    name="airunner",
    version=VERSION,
    author="Capsize LLC",
    description="Run local opensource AI models (Stable Diffusion, LLMs, TTS, STT, chatbots) in a lightweight Python GUI",
    long_description=README,
    long_description_content_type="text/markdown",
    keywords="llm, pyside6, gui, local llm, stable diffusion, generative ai, local chatgpt, text-to-speech, speech-to-text, open source chatbot, python ai runner",
    license="GPL-3.0-only",
    classifiers=LICENSE_CLASSIFIERS,
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
