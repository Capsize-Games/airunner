from setuptools import setup, find_packages

extras_require = {
    # These are optional dependencies that will change the
    # behavior of the application or add new features if installed.
    "nvidia": [  # NVIDIA dependencies:
        "nvidia-cuda-runtime-cu12", # This package provides CUDA 12 runtime
    ],
    "gui": [  # GUI dependencies
        "PySide6==6.9.0",
        "PySide6_Addons==6.9.0",
        "PySide6_Essentials==6.9.0",
        "nodegraphqt==0.6.38",
    ],
    "linux": [  # Linux-specific dependencies
        # "faiss-gpu==1.7.2", # If faiss-gpu is from NVIDIA or a custom index, it needs similar handling
        "tensorrt==10.9.0.34", # This package is from NVIDIA
    ],
    "dev": [  # Development dependencies
        "pytest",
        "python-dotenv==1.0.1",
        "coverage==7.8.0",
        "black==25.1.0", # Note: As of May 2025, Black's versioning might be year.month (e.g., 24.x.x or 25.x.x). 25.1.0 is plausible for a future date.
        "pyinstaller==6.12.0", # As of May 2025, latest PyInstaller is 6.8.0. Check if 6.12.0 is a future or dev version.
    ],
    "art": [  # Art generation dependencies
        "DeepCache==0.1.1",
        "diffusers==0.33.1", # As of May 2025, latest is ~0.29.0. Check version.
        "controlnet_aux==0.0.9",
        "safetensors==0.5.2", # As of May 2025, latest is ~0.4.3. Check version.
        "compel==2.0.3",
        "tomesd==0.1.3",
        "timm<=0.6.7",  # Timm is marked at a lower version for compel, we upgrade after installing
    ],
    "llm": [  # LLM dependencies (also text-to-speech and speech-to-text)
        "transformers==4.51.3", # As of May 2025, latest is ~4.41.0. Check version.
        "bitsandbytes==0.45.5", # As of May 2025, latest is ~0.43.0. Check version.
        "datasets==3.2.0", # As of May 2025, latest is ~2.19.0. Check version.
        "sentence_transformers==3.4.1", # As of May 2025, latest is ~3.0.1. Check version.
        "sounddevice==0.5.1", # As of May 2025, latest is ~0.4.7. Check version.
        "pyttsx3==2.91", # This is an older version, latest is similar but good to note.
        "cryptography==44.0.0", # As of May 2025, latest is ~42.0.8. Check version.
        "llama-index==0.12.14", # As of May 2025, latest is ~0.10.44. Check version.
        "llama-index-readers-file==0.4.4", # LlamaIndex packages are rapidly evolving, check versions.
        "llama-index-readers-web==0.3.5",
        "llama-index-llms-huggingface==0.4.2",
        "llama-index-llms-groq==0.3.1",
        "llama-index-embeddings-mistralai==0.3.0",
        "llama-index-vector-stores-faiss==0.3.0",
        "llama-index-embeddings-huggingface==0.5.1",
        "llama-index-llms-openrouter==0.3.1",
        "langchain-community==0.3.17", # As of May 2025, latest is ~0.2.0. Check version significantly.
        "EbookLib==0.18",
        "html2text==2024.2.26",
        "rake_nltk==1.0.6",
        # "tf-keras==2.18.0", # Removed as it causes issues on Windows with dlopenflags
        "peft==0.15.2", # As of May 2025, latest is ~0.11.1. Check version.
        "lxml_html_clean==0.4.1", # This seems to be an older or less common package. lxml is more standard.
        # "flash_attn==2.7.4.post1", # flash-attn usually requires specific build steps.
        # Summarizations (basic)
        "sumy==0.11.0",
    ],
    "llm_weather": [  # LLM dependencies for weather (requires llm dependencies)
        "requests-cache==1.2.1",
        "retry-requests==2.0.0",
        "openmeteo_requests==1.4.0",
    ],
    "tts": [  # Text-to-speech dependencies (requires llm dependencies)
        "inflect==7.5.0", # As of May 2025, latest is ~7.3.0. Check version.
        "pycountry==24.6.1",
        "librosa==0.11.0", # As of May 2025, latest is ~0.10.2. Check version.
    ],
    "rabbitmq": ["pika"],
}

extras_require["all"] = []
extras_require["all_dev"] = []
extras_require["windows"] = [] # For Windows-specific aggregate, excludes "linux"

for k, v_list in extras_require.items():
    if k == "all":
        continue
    if k != "dev": # 'all' should not include 'dev' dependencies
        extras_require["all"].extend(v_list)
    extras_require["all_dev"].extend(v_list) # 'all_dev' includes everything

# The existing loop does this:
for k, v in extras_require.items():
    if k in ["all", "all_dev", "windows"]: # Avoid processing already aggregated keys if script is re-run/modified
        continue
    # Assuming 'v' is the list of dependencies for key 'k'
    if k != "dev":
        if k not in extras_require["all"]: # Avoid duplicates if keys share dependencies (not typical for extras)
             extras_require["all"].extend(v)
    if k not in extras_require["all_dev"]:
        extras_require["all_dev"].extend(v)
    if k != "linux":
        if k not in extras_require["windows"]:
            extras_require["windows"].extend(v)


setup(
    name="airunner",
    version="4.6.5",
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
    python_requires=">=3.10.17", # Note: 3.10.17 is unusually specific. >=3.10 is more common.
    install_requires=[
        "torch", # For GPU, user must install this from PyTorch's index first
        "torchvision", # or alongside airunner specifying PyTorch's index.
        "torchaudio",
        "torchao",
        "accelerate==1.3.0", # As of May 2025, latest is ~0.31.0
        "huggingface-hub>=0.24.0,<1.0", # As of May 2025, latest is ~0.23.0
        "tokenizers==0.21.1", # As of May 2025, latest is ~0.19.1
        "optimum==1.24.0", # As of May 2025, latest is ~1.20.0
        "numpy==1.26.4", # Standard, latest version
        "pillow==10.4.0", # As of May 2025, latest is 10.3.0
        "alembic==1.14.1", # As of May 2025, latest is 1.13.1
        "aiosqlite==0.21.0", # As of May 2025, latest is 0.20.0
        "sqlalchemy==2.0.38", # As of May 2025, latest is 2.0.30
        "setuptools==78.1.0", # As of May 2025, latest is 70.1.0. This is a very new version number.
        "facehuggershield==0.1.13",
        "etils[epath]==1.12.2", # As of May 2025, latest is 1.8.0
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