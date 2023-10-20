seed_data = {
    "Flan": {
        "generator_settings": {
            "top_p": 90,
            "max_length": 50,
            "repetition_penalty": 100,
            "min_length": 10,
            "k": 0,
            "length_penalty": 100,
            "num_beams": 1,
            "ngram_size": 0,
            "temperature": 100,
            "sequences": 1,
            "top_k": 0,
            "seed": 0,
            "do_sample": False,
            "early_stopping": False,
            "random_seed": False,
            "model_version": "google/flan-t5-large"
        },
        "model_versions": [
            "google/flan-t5-xxl",
            "google/flan-t5-xl",
            "google/flan-t5-large",
            "google/flan-t5-small",
            "google/flan-t5-base"
        ]
    }
}