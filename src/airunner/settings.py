import os

BASE_PATH = os.path.join(os.path.expanduser("~"), ".airunner")
SQLITE_DB_NAME = "airunner.db"
SQLITE_DB_PATH = os.path.join(BASE_PATH, SQLITE_DB_NAME)
DEFAULT_PATHS = {
    "art": {
        "models": {
            "txt2img": os.path.join(BASE_PATH, "art", "models", "txt2img"),
            "depth2img": os.path.join(BASE_PATH, "art", "models", "depth2img"),
            "pix2pix": os.path.join(BASE_PATH, "art", "models", "pix2pix"),
            "inpaint": os.path.join(BASE_PATH, "art", "models", "inpaint"),
            "upscale": os.path.join(BASE_PATH, "art", "models", "upscale"),
            "txt2vid": os.path.join(BASE_PATH, "art", "models", "txt2vid"),
            "embeddings": os.path.join(BASE_PATH, "art", "models", "embeddings"),
            "lora": os.path.join(BASE_PATH, "art", "models", "lora"),
            "vae": os.path.join(BASE_PATH, "art", "models", "vae"),
        },
        "other": {
            "images": os.path.join(BASE_PATH, "art", "other", "images"),
            "videos": os.path.join(BASE_PATH, "art", "other", "videos"),
        },
    },
    "text": {
        "models": {
            "casuallm": os.path.join(BASE_PATH, "text", "models", "casuallm"),
            "seq2seq": os.path.join(BASE_PATH, "text", "models", "seq2seq"),
            "visualqa": os.path.join(BASE_PATH, "text", "models", "visualqa"),
        },
        "other": {
            "ebooks": os.path.join(BASE_PATH, "text", "other", "ebooks"),
            "documents": os.path.join(BASE_PATH, "text", "other", "documents"),
            "llama_index": os.path.join(BASE_PATH, "text", "other", "llama_index"),
        }
    }
}

DEFAULT_CHATBOT = dict(
    username="User",
    botname="AIRunner",
    use_personality=True,
    use_mood=True,
    use_guardrails=True,
    use_system_instructions=True,
    assign_names=True,
    bot_personality="happy. He loves {{ username }}",
    bot_mood="",
    prompt_template="Mistral 7B Instruct: Default Chatbot",
    guardrails_prompt=(
        "Always assist with care, respect, and truth. "
        "Respond with utmost utility yet securely. "
        "Avoid harmful, unethical, prejudiced, or negative content. "
        "Ensure replies promote fairness and positivity."
    ),
    system_instructions=(
        "You are a knowledgeable and helpful assistant. "
        "You will always do your best to answer the User "
        "with the most accurate and helpful information. "
        "You will always stay in character and respond as "
        "the assistant. ALWAYS respond in a conversational "
        "and expressive way. "
        "Use CAPITALIZATION for emphasis. "
        "NEVER generate text for the User ONLY for "
        "the assistant."
    ),
)

AVAILABLE_IMAGE_FILTERS = [
    "SaturationFilter",
    "ColorBalanceFilter",
    "RGBNoiseFilter",
    "PixelFilter",
    "HalftoneFilter",
    "RegistrationErrorFilter"
]

"""
Used in the TTS Bark Preferences widget to selected a voice
"""
VOICES = {
    "English": {
        "Male": [
            "v2/en_speaker_0",
            "v2/en_speaker_1",
            "v2/en_speaker_2",
            "v2/en_speaker_3",
            "v2/en_speaker_4",
            "v2/en_speaker_5",
            "v2/en_speaker_6",
            "v2/en_speaker_7",
            "v2/en_speaker_8",
        ],
        "Female": [
            "v2/en_speaker_9"
        ],
    },
    "Chinese (Simplified)": {
        "Male": [
            "v2/zh_speaker_0",
            "v2/zh_speaker_1",
            "v2/zh_speaker_2",
            "v2/zh_speaker_3",
            "v2/zh_speaker_5",
            "v2/zh_speaker_8",
        ],
        "Female": [
            "v2/zh_speaker_4",
            "v2/zh_speaker_6",
            "v2/zh_speaker_7",
            "v2/zh_speaker_9",
        ],
    },
    "French": {
        "Male": [
            "v2/fr_speaker_0",
            "v2/fr_speaker_3",
            "v2/fr_speaker_4",
            "v2/fr_speaker_6",
            "v2/fr_speaker_7",
            "v2/fr_speaker_8",
            "v2/fr_speaker_9",
        ],
        "Female": [
            "v2/fr_speaker_1",
            "v2/fr_speaker_2",
            "v2/fr_speaker_5",
        ],
    },
    "German": {
        "Male": [
            "v2/de_speaker_0",
            "v2/de_speaker_1",
            "v2/de_speaker_2",
            "v2/de_speaker_4",
            "v2/de_speaker_5",
            "v2/de_speaker_6",
            "v2/de_speaker_7",
            "v2/de_speaker_9",
        ],
        "Female": [
            "v2/de_speaker_3",
            "v2/de_speaker_8",
        ],
    },
    "Hindi": {
        "Male": [
            "v2/hi_speaker_2",
            "v2/hi_speaker_5",
            "v2/hi_speaker_6",
            "v2/hi_speaker_7",
            "v2/hi_speaker_8",
        ],
        "Female": [
            "v2/hi_speaker_0",
            "v2/hi_speaker_1",
            "v2/hi_speaker_3",
            "v2/hi_speaker_4",
            "v2/hi_speaker_9",
        ],
    },
    "Italian": {
        "Male": [
            "v2/it_speaker_0",
            "v2/it_speaker_1",
            "v2/it_speaker_3",
            "v2/it_speaker_4",
            "v2/it_speaker_5",
            "v2/it_speaker_6",
            "v2/it_speaker_8",
        ],
        "Female": [
            "v2/it_speaker_2",
            "v2/it_speaker_7",
            "v2/it_speaker_9",
        ],
    },
    "Japanese": {
        "Male": [
            "v2/ja_speaker_2",
            "v2/ja_speaker_6",
        ],
        "Female": [
            "v2/ja_speaker_0",
            "v2/ja_speaker_1",
            "v2/ja_speaker_3",
            "v2/ja_speaker_4",
            "v2/ja_speaker_5",
            "v2/ja_speaker_7",
            "v2/ja_speaker_8",
            "v2/ja_speaker_9",
        ],
    },
    "Korean": {
        "Male": [
            "v2/ko_speaker_1",
            "v2/ko_speaker_2",
            "v2/ko_speaker_3",
            "v2/ko_speaker_4",
            "v2/ko_speaker_5",
            "v2/ko_speaker_6",
            "v2/ko_speaker_7",
            "v2/ko_speaker_8",
            "v2/ko_speaker_9",
        ],
        "Female": [
            "v2/ko_speaker_0",
        ],
    },
    "Polish": {
        "Male": [
            "v2/pl_speaker_0",
            "v2/pl_speaker_1",
            "v2/pl_speaker_2",
            "v2/pl_speaker_3",
            "v2/pl_speaker_5",
            "v2/pl_speaker_7",
            "v2/pl_speaker_8",
        ],
        "Female": [
            "v2/pl_speaker_4",
            "v2/pl_speaker_6",
            "v2/pl_speaker_9",
        ],
    },
    "Portuguese": {
        "Male": [
            "v2/pt_speaker_0",
            "v2/pt_speaker_1",
            "v2/pt_speaker_2",
            "v2/pt_speaker_3",
            "v2/pt_speaker_4",
            "v2/pt_speaker_5",
            "v2/pt_speaker_6",
            "v2/pt_speaker_7",
            "v2/pt_speaker_8",
            "v2/pt_speaker_9",
        ],
        "Female": [],
    },
    "Russian": {
        "Male": [
            "v2/ru_speaker_0",
            "v2/ru_speaker_1",
            "v2/ru_speaker_2",
            "v2/ru_speaker_3",
            "v2/ru_speaker_4",
            "v2/ru_speaker_7",
            "v2/ru_speaker_8",
        ],
        "Female": [
            "v2/ru_speaker_5",
            "v2/ru_speaker_6",
            "v2/ru_speaker_9",
        ],
    },
    "Spanish": {
        "Male": [
            "v2/es_speaker_0",
            "v2/es_speaker_1",
            "v2/es_speaker_2",
            "v2/es_speaker_3",
            "v2/es_speaker_4",
            "v2/es_speaker_5",
            "v2/es_speaker_6",
            "v2/es_speaker_7",
        ],
        "Female": [
            "v2/es_speaker_8",
            "v2/es_speaker_9",
        ],
    },
    "Turkish": {
        "Male": [
            "v2/tr_speaker_0",
            "v2/tr_speaker_1",
            "v2/tr_speaker_2",
            "v2/tr_speaker_3",
            "v2/tr_speaker_6",
            "v2/tr_speaker_7",
            "v2/tr_speaker_8",
            "v2/tr_speaker_9",
        ],
        "Female": [
            "v2/tr_speaker_4",
            "v2/tr_speaker_5",
        ],
    },
}
TRANSLATION_LANGUAGES = [
    "English",
    "Spanish",
]
TRANSLATION_MODELS = {
    "English": None,
    "Spanish": None,
}
MALE = "Male"
FEMALE = "Female"
