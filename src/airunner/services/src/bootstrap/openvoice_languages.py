"""OpenVoice language configuration and model requirements.

This module defines the models required for each language supported by OpenVoice.
"""

# Core models required for all languages (English is the base)
OPENVOICE_CORE_MODELS = [
    "google-bert/bert-base-multilingual-uncased",
    "google-bert/bert-base-uncased",
    "myshell-ai/MeloTTS-English",
    "myshell-ai/MeloTTS-English-v3",
]

# Language-specific models
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


def get_models_for_languages(selected_languages: list) -> list:
    """Get all models required for the selected languages.
    
    Args:
        selected_languages: List of language keys (e.g., ["French", "Spanish"])
        
    Returns:
        List of model IDs to download
    """
    models = list(OPENVOICE_CORE_MODELS)  # Always include core models
    
    for lang in selected_languages:
        if lang in OPENVOICE_LANGUAGE_MODELS:
            models.extend(OPENVOICE_LANGUAGE_MODELS[lang]["models"])
    
    return models
