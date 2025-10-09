from setuptools import setup, find_packages

extras_require = {
    # These are optional dependencies that will change the
    # behavior of the application or add new features if installed.
    "nvidia": [  # NVIDIA dependencies:
        "nvidia-cuda-runtime-cu12",  # This package provides CUDA 12 runtime
    ],
    "huggingface": [
        "diffusers==0.35.1",
        "controlnet_aux==0.0.10",
        "safetensors==0.6.2",
        "compel==2.1.1",
        "transformers==4.56.1",
        "datasets==4.0.0",
        "peft==0.17.1",
    ],
    "gui": [  # GUI dependencies
        "PySide6==6.9.0",
        "PySide6_Addons==6.9.0",
        "PySide6_Essentials==6.9.0",
    ],
    "linux": [  # Linux-specific dependencies
        # "faiss-gpu==1.7.2", # If faiss-gpu is from NVIDIA or a custom index, it needs similar handling
        "tensorrt==10.13.3.9",
    ],
    "dev": [  # Development dependencies
        "pytest",
        "python-dotenv==1.0.1",
        "coverage==7.8.0",
        "black==25.1.0",
        "pyinstaller==6.12.0",
        "flake8==7.2.0",
        "mypy==1.16.0",
    ],
    "art": [  # Art generation dependencies
        "DeepCache==0.1.1",
        "tomesd==0.1.3",
    ],
    "llm": [  # LLM dependencies (also text-to-speech and speech-to-text)
        "bitsandbytes==0.45.5",
        "sentence_transformers==3.4.1",
        "sounddevice==0.5.1",
        "pyttsx3==2.91",
        "cryptography==44.0.3",
        # "flash_attn==2.7.4.post1", # flash-attn usually requires specific build steps.
        # Summarizations (basic)
        "sumy==0.11.0",
        "sentencepiece==0.2.0",
        "lingua-language-detector==2.1.0",
        "markdown==3.8",
        "libzim==3.7.0",
    ],
    "agents": [
        "llama-index==0.13.6",
        "llama-index-readers-file==0.5.3",
        "llama-index-readers-web==0.5.1",
        "llama-index-llms-huggingface==0.6.0",
        "llama-index-llms-groq==0.4.0",
        "llama-index-embeddings-mistralai==0.4.0",
        "llama-index-vector-stores-faiss==0.5.0",
        "llama-index-embeddings-huggingface==0.6.0",
        "llama-index-llms-openrouter==0.4.0",
        "langchain-community==0.3.29",
        "EbookLib==0.19",
        "html2text==2025.4.15",
        "rake_nltk==1.0.6",
    ],
    "ollama": [
        "llama-index-llms-ollama==0.7.1",
    ],
    "llm_weather": [  # LLM dependencies for weather (requires llm dependencies)
        "requests-cache==1.2.1",
        "retry-requests==2.0.0",
        "openmeteo_requests==1.4.0",
        "uszipcode==1.0.1",
    ],
    "tts": [  # Text-to-speech dependencies (requires llm dependencies)
        "inflect==7.5.0",
        "pycountry==24.6.1",
        "librosa==0.11.0",
    ],
    "rabbitmq": ["pika"],
    "openvoice": [
        "librosa==0.11.0",
        "pydub==0.25.1",
        "wavmark==0.0.3",
        "eng_to_ipa==0.0.2",
        "inflect==7.5.0",
        "unidecode==1.4.0",
        "langid==1.1.6",
    ],
    "melotts": [
        "txtsplit==1.0.0",
        "cached_path==1.7.3",
        "num2words==0.5.14",
        "g2p_en==2.1.0",
        "anyascii==0.3.2",
        "loguru==0.7.3",
    ],
    "openvoice_cn": [
        "pypinyin==0.54.0",
        "jieba==0.42.1",
        "cn2an==0.5.23",
    ],
    "openvoice_jp": [
        "unidic_lite==1.0.8",
        "unidic==1.1.0",
        "mecab-python3==1.0.10",
        # Note: fugashi requires MeCab to be installed on the system
        # Install with: apt-get install mecab libmecab-dev mecab-ipadic-utf8
        "fugashi==1.4.0",
        "pykakasi==2.3.0",
    ],
    "openvoice_kr": [
        "jamo==0.4.1",
        "python-mecab-ko==1.3.7",
        "python-mecab-ko-dic==2.1.1.post2",
    ],
    "openvoice_tw": [
        "g2pkk>=0.1.2",
    ],
    "gruut_support": [
        "gruut[de,es,fr]==2.4.0",
        "networkx==3.4.2",
    ],
    "search": [
        "duckduckgo-search>=8.0.2 ",
        "aiohttp>=3.11.0",
        "google-api-python-client>=2.170.0",
        "wikipedia>=1.4.0",
        "scrapy==2.13.1",
        "trafilatura==2.0.0",
    ],
}

extras_require["all"] = []
extras_require["all_dev"] = []
extras_require["windows"] = []

for k, v_list in extras_require.items():
    if k == "all":
        continue
    if k != "dev":
        extras_require["all"].extend(v_list)
    extras_require["all_dev"].extend(v_list)

for k, v in extras_require.items():
    if k in ["all", "all_dev", "windows"]:
        continue
    if k != "dev":
        if k not in extras_require["all"]:
            extras_require["all"].extend(v)
    if k not in extras_require["all_dev"]:
        extras_require["all_dev"].extend(v)
    if k != "linux":
        if k not in extras_require["windows"]:
            extras_require["windows"].extend(v)


setup(
    name="airunner",
    version="5.0.0",
    author="Capsize LLC",
    description="Run local opensource AI models (Stable Diffusion, LLMs, TTS, STT, chatbots) in a lightweight Python GUI",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    keywords="llm, pyside6, gui, local llm, stable diffusion, generative ai, local chatgpt, text-to-speech, speech-to-text, open source chatbot, python ai runner",
    license="Apache-2.0",
    author_email="contact@capsizegames.com",
    url="https://github.com/Capsize-Games/airunner",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.13.3",
    install_requires=[
        "pip==25.2",
        "torch",
        "torchvision",
        "torchaudio",
        "torchao",
        "accelerate==1.7.0",
        "huggingface-hub>=0.24.0,<1.0",
        "tokenizers==0.22.0",
        "optimum==1.25.1",
        "numpy==2.2.5",
        "pillow==10.4.0",
        "alembic==1.15.2",
        "aiosqlite==0.21.0",
        "sqlalchemy==2.0.38",
        "setuptools==78.1.1",
        "etils[epath]==1.12.2",
        "jinja2==3.1.6",
    ],
    extras_require=extras_require,
    package_data={
        "airunner": [
            "alembic/*",
            "cursors/*",
            "filters/*",
            "icons/*",
            "images/*",
            "styles/*",
            "widgets/**/*.ui",
            "windows/**/*.ui",
            "*.qrc",
            "*.ini",
        ],
    },
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "airunner=airunner.launcher:main",
            "airunner-setup=airunner.installer:main",
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
        ],
    },
)
