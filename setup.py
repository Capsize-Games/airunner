from setuptools import setup, find_packages

setup(
    name="airunner",
    version="3.0.12",
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
        "accelerate==0.33.0",
        "huggingface-hub==0.23.5",
        "PySide6==6.7.0",
        "PySide6_Addons==6.7.0",
        "PySide6_Essentials==6.7.0",
        "tokenizers==0.19.1",
        "torch==2.4.1",
        "torchaudio==2.4.1",
        "torchvision==0.19.1",
        "optimum==1.21.4",
        "numpy==1.26.4",
        "pillow==10.4.0",
        "xformers==0.0.28.post1",
        "tensorflow==2.17.0",
        "DeepCache==0.1.1",
        "alembic==1.13.3",

        # LLM Dependencies
        "transformers==4.43.4",
        "auto-gptq==0.7.1",
        "bitsandbytes==0.43.3",
        "datasets==2.21.0",
        "sentence_transformers==3.0.1",
        "sounddevice==0.5.0",  # Required for tts and stt
        "pyttsx3==2.91",  # Required for tts
        "cryptography==43.0.1",
        "setuptools==75.1.0",

        # Stable Diffusion Dependencies
        "diffusers==0.30.1",
        "controlnet_aux==0.0.9",
        "safetensors==0.4.4",
        "compel==2.0.3",
        "tomesd==0.1.3",

        # TTS Dependencies
        "inflect==7.3.1",
        "pycountry==24.6.1",

        # Security
        "facehuggershield==0.1.11",

        # Llama index
        "llama-index==0.11.7",
        "llama-index-readers-file==0.2.0",
        "llama-index-readers-web==0.2.1",
        "llama-index-llms-huggingface==0.3.1",
        "llama-index-llms-groq==0.2.0",
        "llama-index-embeddings-mistralai==0.2.0",
        "EbookLib==0.18",
        "html2text==2024.2.26"
    ],
    dependency_links=[
    ],
    entry_points={
        'console_scripts': [
            'airunner=airunner.main:main',
        ],
    },
)
