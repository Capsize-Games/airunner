from setuptools import setup, find_packages

extras_require = {
    # These are optional dependencies that will change the
    # behavior of the application or add new features if installed.
    "nvidia": [  # NVIDIA dependencies: skip if installing NVIDIA manually
        "nvidia-pyindex==1.0.9",
        "nvidia-cuda-runtime-cu12",
    ],
    "gui": [  # GUI dependencies
        "PySide6==6.7.0",
        "PySide6_Addons==6.7.0",
        "PySide6_Essentials==6.7.0",
        "nodegraphqt==0.6.38",
    ],
    "linux": [  # Linux-specific dependencies
        # "faiss-gpu==1.7.2",
        "tensorrt==10.9.0.34",
    ],
    "dev": [  # Development dependencies
        "pytest",
        "python-dotenv==1.0.1",
        "coverage==7.8.0",
        "black==25.1.0",
        "pyinstaller==6.12.0",
    ],
    "art": [  # Art generation dependencies
        "DeepCache==0.1.1",
        "diffusers==0.33.1",
        "controlnet_aux==0.0.9",
        "safetensors==0.5.2",
        "compel==2.0.3",
        "tomesd==0.1.3",
        "timm<=0.6.7",  # Timm is marked at a lower version for compel, we upgrade after installing
    ],
    "llm": [  # LLM dependencies (also text-to-speech and speech-to-text)
        "transformers==4.51.3",
        "auto-gptq==0.7.1",
        "bitsandbytes==0.45.5",
        "datasets==3.2.0",
        "sentence_transformers==3.4.1",
        "sounddevice==0.5.1",
        "pyttsx3==2.91",
        "cryptography==44.0.0",
        "llama-index==0.12.14",
        "llama-index-readers-file==0.4.4",
        "llama-index-readers-web==0.3.5",
        "llama-index-llms-huggingface==0.4.2",
        "llama-index-llms-groq==0.3.1",
        "llama-index-embeddings-mistralai==0.3.0",
        "llama-index-vector-stores-faiss==0.3.0",
        "llama-index-embeddings-huggingface==0.5.1",
        "llama-index-llms-openrouter==0.3.1",
        "langchain-community==0.3.17",
        "EbookLib==0.18",
        "html2text==2024.2.26",
        "rake_nltk==1.0.6",
        # "tf-keras==2.18.0", # Removed as it causes issues on Windows with dlopenflags
        "peft==0.15.2",
        "lxml_html_clean==0.4.1",
        # "flash_attn==2.7.4.post1",
        # Summarizations (basic)
        "sumy==0.11.0",
    ],
    "llm_weather": [  # LLM dependencies for weather (requires llm dependencies)
        "requests-cache==1.2.1",
        "retry-requests==2.0.0",
        "openmeteo_requests==1.4.0",
    ],
    "tts": [  # Text-to-speech dependencies (requires llm dependencies)
        "inflect==7.5.0",
        "pycountry==24.6.1",
        "librosa==0.11.0",
    ],
    "rabbitmq": ["pika"],
}

extras_require["all"] = []
extras_require["all_dev"] = []
extras_require["windows"] = []

for k, v in extras_require.items():
    if k == "all":
        continue
    if k != "dev":
        extras_require["all"].extend(v)
    extras_require["all_dev"].extend(v)
    extras_require["windows"].extend(v if k != "linux" else [])

setup(
    name="airunner",
    version="4.6.3",
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
    python_requires=">=3.10.11,<3.11.0",
    install_requires=[
        "torch",
        "torchvision",
        "torchaudio",
        "torchao",
        "accelerate==1.3.0",
        "huggingface-hub>=0.24.0,<1.0",
        "tokenizers==0.21.1",
        "optimum==1.24.0",
        "numpy==1.26.4",
        "pillow==10.4.0",
        "alembic==1.14.1",
        "aiosqlite==0.21.0",
        "sqlalchemy==2.0.38",
        "setuptools==78.1.0",
        "facehuggershield==0.1.13",
        "etils[epath]==1.12.2",
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
            "airunner=airunner.main:main",
            "airunner-setup=airunner.installer:main",
            "airunner-build-ui=airunner.bin.build_ui:main",
            "airunner-tests=airunner.bin.run_tests:main",
            "airunner-test-coverage-report=airunner.bin.coverage_report:main",
            "airunner-docker=airunner.bin.docker_wrapper:main",
        ],
    },
)
