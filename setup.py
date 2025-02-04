from setuptools import setup, find_packages

setup(
    name="airunner",
    version="3.1.9",
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
        "accelerate==1.3.0",
        "huggingface-hub==0.28.1",
        "PySide6==6.7.0",
        "PySide6_Addons==6.7.0",
        "PySide6_Essentials==6.7.0",
        "tokenizers==0.21.0",
        "torch==2.6.0",
        "torchaudio==2.6.0",
        "torchvision==0.21.0",
        "optimum==1.24.0",
        "numpy==2.0.2",
        "pillow==11.1.0",
        "tensorflow==2.18.0",
        "DeepCache==0.1.1",
        "alembic==1.14.1",

        # LLM Dependencies
        "transformers==4.48.1",
        "auto-gptq==0.7.1",
        "bitsandbytes==0.45.1",
        "datasets==3.2.0",
        "sentence_transformers==3.4.1",
        "sounddevice==0.5.1",  # Required for tts and stt
        "pyttsx3==2.91",  # Required for tts
        "cryptography==44.0.0",
        "setuptools==75.8.0",

        # # Stable Diffusion Dependencies
        "diffusers==0.32.2",
        "controlnet_aux==0.0.9",
        "safetensors==0.5.2",
        "compel==2.0.3",
        "tomesd==0.1.3",

        # # TTS Dependencies
        "inflect==7.5.0",
        "pycountry==24.6.1",

        # Llama index
        "llama-index==0.12.14",
        "llama-index-readers-file==0.4.4",
        "llama-index-readers-web==0.3.5",
        "llama-index-llms-huggingface==0.4.2",
        "llama-index-llms-groq==0.3.1",
        "llama-index-embeddings-mistralai==0.3.0",
        "EbookLib==0.18",
        "html2text==2024.2.26",
        "rake_nltk==1.0.6"
    ],
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
        'console_scripts': [
            'airunner=airunner.main:main',
        ],
    },
)
