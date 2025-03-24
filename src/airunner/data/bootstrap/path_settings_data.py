import os
from airunner.settings import AIRUNNER_ART_ENABLED


PATH_SETTINGS_DATA = {
    "documents_path": os.path.expanduser(
        os.path.join(
            "text",
            "other",
            "documents"
        )
    ),
    "ebook_path": os.path.expanduser(
        os.path.join(
            "text",
            "other",
            "ebooks"
        )
    ),
    "llama_index_path": os.path.expanduser(
        os.path.join(
            "text",
            "rag",
            "db"
        )
    ),
    "webpages_path": os.path.expanduser(
        os.path.join(
            "text",
            "other",
            "webpages"
        )
    ),
    "stt_model_path": os.path.expanduser(
        os.path.join(
            "text",
            "models",
            "stt"
        )
    ),
    "tts_model_path": os.path.expanduser(
        os.path.join(
            "text",
            "models",
            "tts"
        )
    ),
}


if AIRUNNER_ART_ENABLED:
    PATH_SETTINGS_DATA["image_path"] = os.path.expanduser(
        os.path.join(
            "art",
            "other",
            "images"
        )
    )