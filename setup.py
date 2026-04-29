from pathlib import Path

from setuptools import find_packages, setup

README = Path("README.md").read_text(encoding="utf-8")

CORE_REQUIREMENTS = [
    "numpy==2.2.5",
    "packaging>=24.0",
    "pillow==12.0.0",
    "alembic==1.13.2",
    "aiosqlite==0.21.0",
    "sqlalchemy==2.0.38",
    "psycopg[binary]>=3.2.0",
    "etils[epath]==1.12.2",
    "jinja2==3.1.6",
    "pyyaml==6.0.2",
    "fastapi==0.115.0",
    "python-multipart>=0.0.9",
    "uvicorn[standard]==0.34.0",
]

ML_RUNTIME_REQUIREMENTS = [
    "torch",
    "torchvision",
    "torchaudio",
    "accelerate==1.7.0",
    "huggingface-hub>=0.24.0,<1.0",
    "tokenizers==0.22.0",
    "optimum==1.25.1",
]

NVIDIA_REQUIREMENTS = ["nvidia-cuda-runtime"]

HUGGINGFACE_REQUIREMENTS = [
    "diffusers==0.35.1",
    "controlnet_aux==0.0.10",
    "safetensors==0.6.2",
    "kornia",
    "timm",
    "compel==2.1.1",
    "transformers==4.57.3",
    "datasets==4.0.0",
    "peft==0.17.1",
]

GUI_REQUIREMENTS = [
    "PySide6==6.9.0",
    "PySide6_Addons==6.9.0",
    "PySide6_Essentials==6.9.0",
]

DEVELOPMENT_REQUIREMENTS = [
    "pytest",
    "pytest-timeout",
    "responses>=0.25.0",
    "python-dotenv==1.0.1",
    "coverage==7.8.0",
    "black==25.1.0",
    "pyinstaller==6.12.0",
    "flake8==7.2.0",
    "mypy==1.16.0",
    "autoflake==2.3.1",
    "pandas>=2.0.0",
    "pyarrow>=14.0.0",
    "tqdm>=4.0.0",
]

ART_REQUIREMENTS = [
    "DeepCache==0.1.1",
    "tomesd==0.1.3",
    "gguf==0.17.1",
]

LLM_NATIVE_REQUIREMENTS = [
    "llama-cpp-python==0.3.16",
    "bitsandbytes==0.45.5",
    "sentence_transformers==3.4.1",
    "cryptography==44.0.3",
    "sumy==0.11.0",
    "sentencepiece==0.2.1",
    "lingua-language-detector==2.1.0",
    "markdown==3.8",
    "libzim==3.7.0",
    "mistral_common>=1.8.5",
    "rank-bm25>=0.2.2",
    "llama-index==0.12.36",
    "llama-index-readers-file==0.4.0",
    "llama-index-embeddings-huggingface==0.4.0",
    "llama-cloud==0.1.23",
    "llama-index-core==0.12.36",
    "llama-index-embeddings-openai==0.3.0",
    "llama-index-question-gen-openai==0.3.0",
    "llama-index-program-openai==0.3.0",
    "llama-index-multi-modal-llms-openai==0.4.0",
    "llama-index-cli==0.4.1",
    "llama-index-agent-openai==0.4.8",
    "llama-index-indices-managed-llama-cloud==0.7.1",
    "langchain==1.0.0",
    "langchain-core==1.0.0",
    "langchain-community>=0.4.0",
    "langchain-huggingface>=0.1.0",
    "langgraph==1.0.0",
    "langsmith>=0.1.0",
    "langchain-ollama==1.0.0",
    "EbookLib==0.19",
]

STT_NATIVE_REQUIREMENTS = [
    "faster-whisper>=1.0.0",
    "sounddevice==0.5.1",
]

LLM_WEATHER_REQUIREMENTS = [
    "requests-cache==1.2.1",
    "retry-requests==2.0.0",
    "openmeteo_requests==1.4.0",
]

TTS_REQUIREMENTS = [
    "inflect==7.5.0",
    "pycountry==24.6.1",
    "librosa==0.11.0",
    "torchcodec>=0.8.0",
]

OPENVOICE_REQUIREMENTS = [
    "librosa==0.11.0",
    "pydub==0.25.1",
    "wavmark==0.0.3",
    "eng_to_ipa==0.0.2",
    "inflect==7.5.0",
    "unidecode==1.4.0",
    "langid==1.1.6",
]

MELOTTS_REQUIREMENTS = [
    "txtsplit==1.0.0",
    "num2words==0.5.14",
    "g2p_en==2.1.0",
    "anyascii==0.3.2",
    "loguru==0.7.3",
]

OPENVOICE_CN_REQUIREMENTS = [
    "pypinyin==0.54.0",
    "jieba==0.42.1",
    "cn2an==0.5.23",
]

OPENVOICE_JP_REQUIREMENTS = [
    "unidic_lite==1.0.8",
    "unidic==1.1.0",
    "mecab-python3==1.0.10",
    "fugashi==1.4.0",
    "pykakasi==2.3.0",
]

OPENVOICE_KR_REQUIREMENTS = [
    "jamo==0.4.1",
    "python-mecab-ko==1.3.7",
    "python-mecab-ko-dic==2.1.1.post2",
]

OPENVOICE_TW_REQUIREMENTS = ["g2pkk>=0.1.2"]

GRUUT_SUPPORT_REQUIREMENTS = [
    "gruut[de,es,fr]==2.4.0",
    "networkx==3.4.2",
]

SEARCH_REQUIREMENTS = [
    "ddgs>=9.0.0",
    "aiohttp>=3.11.0",
    "google-api-python-client>=2.170.0",
    "wikipedia>=1.4.0",
    "scrapy==2.13.1",
    "trafilatura==2.0.0",
]

COMPUTER_USE_REQUIREMENTS = [
    "pyautogui>=0.9.54",
    "pyscreeze>=1.0.1",
    "python-xlib>=0.33;platform_system=='Linux'",
    "pygetwindow>=0.0.9",
]

SYSTEM_DEP_EXTRAS = {"openvoice_jp", "openvoice_kr"}


def unique_requirements(*groups):
    dependencies = []
    for group in groups:
        dependencies.extend(group)
    return list(dict.fromkeys(dependencies))


extras_require = {
    "core": [],
    "nvidia": NVIDIA_REQUIREMENTS,
    "huggingface": HUGGINGFACE_REQUIREMENTS,
    "gui": GUI_REQUIREMENTS,
    "linux": [],
    "development": DEVELOPMENT_REQUIREMENTS,
    "dev": DEVELOPMENT_REQUIREMENTS,
    "art": ART_REQUIREMENTS,
    "llm-native": unique_requirements(
        ML_RUNTIME_REQUIREMENTS,
        LLM_NATIVE_REQUIREMENTS,
    ),
    "stt-native": STT_NATIVE_REQUIREMENTS,
    "art-python": unique_requirements(
        ML_RUNTIME_REQUIREMENTS,
        HUGGINGFACE_REQUIREMENTS,
        ART_REQUIREMENTS,
    ),
    "llm": unique_requirements(
        ML_RUNTIME_REQUIREMENTS,
        LLM_NATIVE_REQUIREMENTS,
        STT_NATIVE_REQUIREMENTS,
        ["pyttsx3==2.91"],
    ),
    "llm_weather": LLM_WEATHER_REQUIREMENTS,
    "llm-weather": LLM_WEATHER_REQUIREMENTS,
    "tts": TTS_REQUIREMENTS,
    "tts-python": unique_requirements(
        ML_RUNTIME_REQUIREMENTS,
        TTS_REQUIREMENTS,
        ["pyttsx3==2.91"],
        OPENVOICE_REQUIREMENTS,
        MELOTTS_REQUIREMENTS,
        OPENVOICE_CN_REQUIREMENTS,
        OPENVOICE_TW_REQUIREMENTS,
        GRUUT_SUPPORT_REQUIREMENTS,
    ),
    "rabbitmq": ["pika"],
    "openvoice": OPENVOICE_REQUIREMENTS,
    "melotts": MELOTTS_REQUIREMENTS,
    "openvoice_cn": OPENVOICE_CN_REQUIREMENTS,
    "openvoice_jp": OPENVOICE_JP_REQUIREMENTS,
    "openvoice_kr": OPENVOICE_KR_REQUIREMENTS,
    "openvoice_tw": OPENVOICE_TW_REQUIREMENTS,
    "gruut_support": GRUUT_SUPPORT_REQUIREMENTS,
    "search": SEARCH_REQUIREMENTS,
    "computer_use": COMPUTER_USE_REQUIREMENTS,
    "computer-use": COMPUTER_USE_REQUIREMENTS,
}


def build_aggregate_extra(*extra_names):
    dependencies = []
    for extra_name in extra_names:
        dependencies.extend(extras_require[extra_name])
    return list(dict.fromkeys(dependencies))


extras_require["headless"] = build_aggregate_extra(
    "llm-native",
    "stt-native",
    "art-python",
    "tts-python",
)
extras_require["desktop"] = build_aggregate_extra("headless", "gui")
extras_require["all"] = build_aggregate_extra(
    "desktop",
    "llm_weather",
    "search",
    "computer_use",
    "nvidia",
    "rabbitmq",
    "linux",
)
extras_require["all_dev"] = build_aggregate_extra("all", "development")
extras_require["all_native"] = build_aggregate_extra(
    "all",
    *sorted(SYSTEM_DEP_EXTRAS),
)
extras_require["all_dev_native"] = build_aggregate_extra(
    "all_native",
    "development",
)
extras_require["windows"] = build_aggregate_extra(
    "desktop",
    "llm_weather",
    "search",
    "computer_use",
    "nvidia",
    "rabbitmq",
)


setup(
    name="airunner",
    version="5.6.1",
    author="Capsize LLC",
    description="Run local opensource AI models (Stable Diffusion, LLMs, TTS, STT, chatbots) in a lightweight Python GUI",
    long_description=README,
    long_description_content_type="text/markdown",
    keywords="llm, pyside6, gui, local llm, stable diffusion, generative ai, local chatgpt, text-to-speech, speech-to-text, open source chatbot, python ai runner",
    license="Apache-2.0",
    author_email="contact@capsizegames.com",
    url="https://github.com/Capsize-Games/airunner",
    package_dir={"": "src"},
    py_modules=["airunner_startup_env"],
    packages=find_packages("src"),
    python_requires=">=3.13.3",
    install_requires=CORE_REQUIREMENTS,
    extras_require=extras_require,
    package_data={
        "airunner": [
            # Alembic migrations
            "alembic/*.py",
            "alembic/*.mako",
            "alembic/versions/*.py",
            "*.ini",
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
            "airunner-headless=airunner.bin.airunner_headless:main",
            "airunner-build-ui=airunner.bin.build_ui:main",
            "airunner-compile-translations=airunner.bin.compile_translations:main",
            "airunner-tests=airunner.bin.run_tests:main",
            "airunner-test-coverage-report=airunner.bin.coverage_report:main",
            "airunner-docker=airunner.bin.docker_wrapper:main",
            "airunner-generate-migration=airunner.bin.generate_migration:main",
            "airunner-generate-cert=airunner.bin.generate_cert:main",
            "airunner-mypy=airunner.bin.mypy_shortcut:main",
            "airunner-create-theme=airunner.bin.airunner_create_theme:main",
            "airunner-create-component=airunner.bin.airunner_create_component:main",
            "airunner-train-diffusers=airunner.bin.train_diffusers:main",
            "airunner-daemon=airunner.services.daemon:main",
            "airunner-service=airunner.bin.airunner_service:main",
            "airunner-quality-report=airunner.bin.code_quality_report:main",
            "airunner-remove-unused-imports=airunner.bin.remove_unused_imports:main",
            "airunner-migrate-knowledge=airunner.bin.airunner_migrate_knowledge:main",
            "airunner-cleanup-llm-models=airunner.bin.cleanup_llm_models:main",
            "airunner-hf-download=airunner.bin.airunner_hf_download:main",
            "airunner-civitai-download=airunner.bin.airunner_civitai_download:main",
        ],
    },
)
