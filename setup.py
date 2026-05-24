from pathlib import Path

from setuptools import find_packages, setup

README = Path("README.md").read_text(encoding="utf-8")

VERSION = "6.0.0"

GUI_REQUIREMENTS = [
    "PySide6==6.9.0",
    "PySide6_Addons==6.9.0",
    "PySide6_Essentials==6.9.0",
]


def unique_requirements(*groups):
    dependencies = []
    for group in groups:
        dependencies.extend(group)
    return list(dict.fromkeys(dependencies))


setup(
    name="airunner",
    version=VERSION,
    author="Capsize LLC",
    description="Run local opensource AI models (Stable Diffusion, LLMs, TTS, STT, chatbots) in a lightweight Python GUI",
    long_description=README,
    long_description_content_type="text/markdown",
    keywords="llm, pyside6, gui, local llm, stable diffusion, generative ai, local chatgpt, text-to-speech, speech-to-text, open source chatbot, python ai runner",
    license="Apache-2.0",
    author_email="contact@capsizegames.com",
    url="https://github.com/Capsize-Games/airunner",
    package_dir={"": "src", "scripts": "."},
    py_modules=["airunner_startup_env"],
    packages=find_packages("src") + ["scripts"],
    python_requires=">=3.13.3",
    install_requires=GUI_REQUIREMENTS,
    extras_require={},
    package_data={
        "airunner": [
            # GUI resources
            "gui/cursors/*",
            "gui/images/*",
            "gui/resources/**/*",
            "gui/styles/**/*",
            # Component resources
            "components/icons/*",
            "components/art/filters/*",
            # UI templates (all .ui files in templates directories)
            "components/**/templates/*.ui",
            # Legal documents (user agreement, privacy policy)
            "components/**/user_agreement/*.md",
            # Static files (HTML, CSS, JS templates for web views)
            "components/**/static/**/*",
            "static/**/*",
        ],
    },
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "airunner=airunner.launcher:main",
            "airunner-build-ui=scripts.build_ui:main",
            "airunner-compile-translations=scripts.compile_translations:main",
            "airunner-tests=scripts.run_tests:main",
            "airunner-test-coverage-report=scripts.coverage_report:main",
            "airunner-mypy=scripts.mypy_shortcut:main",
            "airunner-quality-report=scripts.code_quality_report:main",
            "airunner-remove-unused-imports=scripts.remove_unused_imports:main",
        ],
    },
)
