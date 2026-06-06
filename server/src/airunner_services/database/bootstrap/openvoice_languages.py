"""OpenVoice language configuration and model requirements."""

from __future__ import annotations

OPENVOICE_CORE_MODELS = [
    "google-bert/bert-base-multilingual-uncased",
    "google-bert/bert-base-uncased",
    "myshell-ai/MeloTTS-English",
    "myshell-ai/MeloTTS-English-v3",
]

OPENVOICE_LANGUAGE_MODELS = {
    "French": {
        "display_name": "French",
        "models": [
            "dbmdz/bert-base-french-europeana-cased",
            "myshell-ai/MeloTTS-French",
        ],
    },
    "Spanish": {
        "display_name": "Spanish",
        "models": [
            "dccuchile/bert-base-spanish-wwm-uncased",
            "myshell-ai/MeloTTS-Spanish",
        ],
    },
    "Japanese": {
        "display_name": "Japanese",
        "models": [
            "tohoku-nlp/bert-base-japanese-v3",
            "myshell-ai/MeloTTS-Japanese",
        ],
    },
    "Chinese": {
        "display_name": "Chinese",
        "models": [
            "hfl/chinese-roberta-wwm-ext-large",
            "myshell-ai/MeloTTS-Chinese",
        ],
    },
    "Korean": {
        "display_name": "Korean",
        "models": [
            "kykim/bert-kor-base",
            "myshell-ai/MeloTTS-Korean",
        ],
    },
}


def get_models_for_languages(selected_languages: list[str]) -> list[str]:
    """Return the model ids required for the selected languages."""
    models = list(OPENVOICE_CORE_MODELS)

    for language in selected_languages:
        if language in OPENVOICE_LANGUAGE_MODELS:
            models.extend(OPENVOICE_LANGUAGE_MODELS[language]["models"])

    return models


__all__ = [
    "OPENVOICE_CORE_MODELS",
    "OPENVOICE_LANGUAGE_MODELS",
    "get_models_for_languages",
]
