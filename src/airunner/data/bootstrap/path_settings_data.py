import os


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
    "image_path": os.path.expanduser(
        os.path.join(
            "art",
            "other",
            "images"
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