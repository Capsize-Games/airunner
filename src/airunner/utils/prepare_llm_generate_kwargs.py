def prepare_llm_generate_kwargs(settings):
    min_val = 0.0001
    length_penalty = settings.length_penalty / 1000.0
    repetition_penalty = settings.repetition_penalty / 100.0
    top_p = settings.top_p / 1000.0
    temperature = settings.temperature / 10000.0
    do_sample = settings.do_sample
    early_stopping = settings.early_stopping
    eta_cutoff = settings.eta_cutoff
    max_new_tokens = settings.max_new_tokens
    min_length = settings.min_length
    num_return_sequences = 1
    top_k = settings.top_k
    use_cache = settings.use_cache
    ngram_size = settings.ngram_size
    num_beams = settings.num_beams

    if length_penalty < min_val:
        length_penalty = min_val

    if repetition_penalty < min_val:
        repetition_penalty = min_val

    if top_p < min_val:
        top_p = min_val

    if temperature < min_val:
        temperature = min_val

    return {
        "length_penalty": length_penalty,
        "repetition_penalty": repetition_penalty,
        "do_sample": do_sample,
        "early_stopping": early_stopping,
        "eta_cutoff": eta_cutoff,
        "max_new_tokens": max_new_tokens,
        "min_length": min_length,
        "num_return_sequences": num_return_sequences,
        "temperature": temperature,
        "top_k": top_k,
        "top_p": top_p,
        "use_cache": use_cache,
        # "no_repeat_ngram_size": ngram_size,
        # "num_beams": num_beams,
    }
