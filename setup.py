from pathlib import Path

from setuptools import find_packages, setup

README = Path("README.md").read_text(encoding="utf-8")

VERSION = "6.0.0"

ANALYSIS_REQUIREMENTS = [
    "radon>=6.0.1,<7",
    "xenon>=0.9.3,<1",
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
    description="Run local opensource AI models (Stable Diffusion, LLMs, TTS, STT, chatbots) with a web GUI and headless API",
    long_description=README,
    long_description_content_type="text/markdown",
    keywords="llm, web gui, local llm, stable diffusion, generative ai, local chatgpt, text-to-speech, speech-to-text, open source chatbot, python ai runner",
    license="Apache-2.0",
    author_email="contact@capsizegames.com",
    url="https://github.com/Capsize-Games/airunner",
    package_dir={"": "services/src", "scripts": "."},
    py_modules=["airunner_startup_env"],
    packages=find_packages("services/src") + ["scripts"],
    python_requires=">=3.13.3",
    install_requires=[],
    extras_require={"analysis": ANALYSIS_REQUIREMENTS},
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "airunner-headless=airunner_services.bin.airunner_headless:main",
            "airunner-hf-download=airunner_services.bin.airunner_hf_download:main",
            "airunner-civitai-download=airunner_services.bin.airunner_civitai_download:main",
            "airunner-tests=scripts.run_tests:main",
            "airunner-test-coverage-report=scripts.coverage_report:main",
            "airunner-mypy=scripts.mypy_shortcut:main",
            "airunner-quality-report=scripts.code_quality_report:main",
            "airunner-services-complexity-report=scripts.services_complexity_report:main",
            "airunner-remove-unused-imports=scripts.remove_unused_imports:main",
            "airunner-generate-cert=airunner_services.bin.generate_cert:main",
        ],
    },
)
