from setuptools import setup, find_packages

setup(
    name='airunner',
    version="3.0.0.dev13",
    author="Capsize LLC",
    description="A Stable Diffusion GUI",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    keywords="ai, stable diffusion, art, ai art, stablediffusion",
    license="GPL-3.0",
    author_email="contact@capsizegames.com",
    url="https://github.com/Capsize-Games/airunner",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.10.0",
    install_requires=[
        # Core application dependencies
        "tqdm==4.66.4",
        "accelerate==0.31.0",
        "huggingface-hub==0.23.5",
        "numpy==1.26.4",
        "pip==24.0",
        "PySide6==6.7.0",
        "PySide6_Addons==6.7.0",
        "PySide6_Essentials==6.7.0",
        "requests==2.31.0",
        "requests-oauthlib==2.0.0",
        "scipy==1.13.0",
        "tokenizers==0.19.1",
        "charset-normalizer==3.3.2",
        "typing_extensions==4.11.0",
        "urllib3==2.2.1",
        "sympy==1.12.0",
        "regex==2024.4.28",
        "matplotlib==3.8.4",
        "torch==2.2.2",
        "torchvision==0.17.2",
        "torchaudio==2.2.2",
        "optimum==1.21.4",
        "inflect==7.2.0",
        "tiktoken==0.6.0",
        "mediapipe==0.10.11",
        "cryptography==42.0.5",
        "coverage==7.4.4",  # Required for testing
        # "watchdog==4.0.0",  # Required for file watching
        
        # LLM Dependencies
        "transformers==4.41.2",
        "auto-gptq==0.7.1",
        "bitsandbytes==0.43.1",
        "datasets==2.18.0",
        "sentence_transformers==2.6.1",
        "pycountry==23.12.11",
        "sounddevice==0.4.6",  # Required for tts and stt
        "pyttsx3==2.90",  # Required for tts

        # Pyinstaller Dependencies
        "ninja==1.11.1.1",
        "JIT==0.2.7",
        # "opencv-python-headless==4.9.0.80",
        "setuptools==69.5.1",

        # Stable Diffusion Dependencies
        "omegaconf==2.3.0",
        "diffusers==0.29.2",
        "controlnet_aux==0.0.8",
        "einops==0.7.0",  # Required for controlnet_aux
        "Pillow==10.3.0",
        "pyre-extensions==0.0.30",
        "safetensors==0.4.3",
        "compel==2.0.2",
        "tomesd==0.1.3",

        # Security
        "facehuggershield==0.1.10",
        
        # Llama index
        "llama-index==0.10.32",
        "llama-index-readers-file==0.1.19",
        "llama-index-readers-web==0.1.13",
        "llama-index-llms-huggingface==0.2.8"
    ],
    dependency_links=[],
)
